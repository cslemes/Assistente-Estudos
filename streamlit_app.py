import json

import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(
    page_title="Assistente de Estudos — PUC-Rio",
    page_icon="🎓",
    layout="wide",
)


def render_sources(sources: list) -> None:
    if not sources:
        return
    with st.expander(f"📚 {len(sources)} fontes", expanded=False):
        n_cols = min(len(sources), 3)
        cols = st.columns(n_cols)
        for i, doc in enumerate(sources):
            m = doc.get("metadata", {})
            label = " — ".join(p for p in [m.get("course"), m.get("topic")] if p) or "Aula"
            aula = m.get("aula_number")
            url = m.get("video_url")
            excerpt = (doc.get("page_content") or "")[:150]
            with cols[i % n_cols]:
                st.markdown(f"**{label}**")
                if aula:
                    st.caption(f"Aula {aula}")
                st.caption(excerpt + ("…" if len(doc.get("page_content", "")) > 150 else ""))
                if url:
                    st.link_button("▶ Assistir", url)


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🎓 Assistente PUC-Rio")
    st.divider()

    provider = st.radio("Provedor LLM", ["Groq (rápido)", "OpenAI"], index=0)

    st.subheader("Filtros")

    @st.cache_data(show_spinner=False)
    def get_classes() -> list:
        try:
            r = requests.get(f"{API}/classes", timeout=5)
            r.raise_for_status()
            return r.json().get("classes", [])
        except Exception:
            return []

    classes = get_classes()
    courses = sorted({c["course"] for c in classes if c.get("course")})

    course = st.selectbox("Curso", ["Todos"] + courses)

    available_topics = sorted(
        {
            c["topic"]
            for c in classes
            if c.get("topic") and (course == "Todos" or c.get("course") == course)
        }
    )
    topic = st.selectbox("Tópico", ["Todos"] + available_topics)

    st.divider()
    st.caption(f"{len(classes)} aulas indexadas")

    if st.button("🗑️ Limpar conversa"):
        st.session_state.messages = []
        st.rerun()


# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_chat, tab_flashcards = st.tabs(["💬 Chat", "🃏 Flashcards"])


# ── Chat tab ──────────────────────────────────────────────────────────────────

with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("Assistente de Estudos")
    st.caption("Faça perguntas sobre as aulas da pós-graduação em IA.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                render_sources(msg["sources"])

    if prompt := st.chat_input("Pergunte sobre as aulas…"):
        st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
        with st.chat_message("user"):
            st.markdown(prompt)

        endpoint = "/ask/groq/stream" if "Groq" in provider else "/ask/stream"
        payload = {
            "query": prompt,
            "limit": 10,
            "course": None if course == "Todos" else course,
            "topic": None if topic == "Todos" else topic,
        }

        state = {"sources": [], "full_text": ""}

        with st.chat_message("assistant"):
            try:
                with requests.post(
                    f"{API}{endpoint}", json=payload, stream=True, timeout=120
                ) as resp:
                    resp.raise_for_status()

                    def delta_gen():
                        for raw_line in resp.iter_lines():
                            if not raw_line:
                                continue
                            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                            if not line.startswith("data: "):
                                continue
                            try:
                                event = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue
                            etype = event.get("type")
                            if etype == "source_documents":
                                state["sources"] = event.get("documents", [])
                            elif etype == "text_delta":
                                chunk = event.get("delta", "")
                                state["full_text"] += chunk
                                yield chunk
                            elif etype == "stream_completed":
                                break
                            elif etype == "error":
                                st.error(event.get("message", "Erro desconhecido"))
                                break

                    st.write_stream(delta_gen())

            except requests.exceptions.ConnectionError:
                st.error("Não foi possível conectar à API. Verifique se o servidor está rodando em localhost:8000.")
            except Exception as e:
                st.error(f"Erro: {e}")

            if state["sources"]:
                render_sources(state["sources"])

        st.session_state.messages.append(
            {"role": "assistant", "content": state["full_text"], "sources": state["sources"]}
        )


# ── Flashcards tab ────────────────────────────────────────────────────────────

with tab_flashcards:
    st.title("Gerar Flashcards para Anki")
    st.caption(
        "Selecione o conteúdo desejado, gere os flashcards com IA e importe o arquivo "
        ".apkg diretamente no Anki."
    )

    col1, col2 = st.columns(2)

    with col1:
        fc_course = st.selectbox("Curso", ["Todos"] + courses, key="fc_course")
        fc_available_topics = sorted(
            {
                c["topic"]
                for c in classes
                if c.get("topic")
                and (fc_course == "Todos" or c.get("course") == fc_course)
            }
        )
        fc_topic = st.selectbox("Tópico", ["Todos"] + fc_available_topics, key="fc_topic")

    with col2:
        fc_available_aulas = sorted(
            {
                c["aula_number"]
                for c in classes
                if c.get("aula_number") is not None
                and (fc_course == "Todos" or c.get("course") == fc_course)
                and (fc_topic == "Todos" or c.get("topic") == fc_topic)
            }
        )
        aula_options = ["Todas"] + [str(int(n)) for n in fc_available_aulas]
        fc_aula = st.selectbox("Aula", aula_options, key="fc_aula")
        fc_num_cards = st.slider(
            "Quantidade de cards", min_value=5, max_value=50, value=20, step=5
        )

    fc_deck_name = st.text_input(
        "Nome do deck (opcional)",
        placeholder="ex: Redes Neurais — PUC-Rio",
        key="fc_deck_name",
    )

    if st.button("Gerar Flashcards", type="primary", key="fc_generate"):
        payload = {
            "course": None if fc_course == "Todos" else fc_course,
            "topic": None if fc_topic == "Todos" else fc_topic,
            "aula_number": None if fc_aula == "Todas" else int(fc_aula),
            "num_cards": fc_num_cards,
            "deck_name": fc_deck_name or None,
        }

        with st.spinner("Gerando flashcards com IA…"):
            try:
                resp = requests.post(
                    f"{API}/flashcards",
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 404:
                    st.warning(resp.json().get("detail", "Nenhum conteúdo encontrado."))
                elif resp.status_code == 502:
                    st.error(resp.json().get("detail", "O modelo não retornou flashcards."))
                elif not resp.ok:
                    st.error(f"Erro {resp.status_code}: {resp.text[:200]}")
                else:
                    parts = [p for p in [fc_course, fc_topic] if p and p != "Todos"]
                    fname = "_".join(parts) if parts else "pucrio_ia"
                    st.success(f"Flashcards gerados com sucesso!")
                    st.download_button(
                        label="⬇️ Baixar .apkg para Anki",
                        data=resp.content,
                        file_name=f"flashcards_{fname}.apkg".replace(" ", "_"),
                        mime="application/octet-stream",
                        key="fc_download",
                    )
            except requests.exceptions.ConnectionError:
                st.error(
                    "Não foi possível conectar à API. "
                    "Verifique se o servidor está rodando em localhost:8000."
                )
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
