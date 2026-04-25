import json

import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(
    page_title="Assistente de Estudos — PUC-Rio",
    page_icon="🎓",
    layout="wide",
)


@st.cache_data(show_spinner=False, ttl=300)
def get_classes() -> list:
    try:
        r = requests.get(f"{API}/classes", timeout=30)
        r.raise_for_status()
        return r.json().get("classes", [])
    except Exception:
        return []


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

    if st.button("🔄 Atualizar filtros", use_container_width=True):
        get_classes.clear()
        st.rerun()

    st.divider()
    st.caption(f"{len(classes)} aulas indexadas")

    if st.button("🗑️ Limpar conversa"):
        st.session_state.messages = []
        st.rerun()


# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_chat, tab_resumos, tab_flashcards = st.tabs(["💬 Chat", "📝 Resumos", "🃏 Flashcards"])


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
                                chunk = event.get("text", "")
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


# ── Resumos tab ───────────────────────────────────────────────────────────────

with tab_resumos:
    st.title("Resumos das Aulas")
    st.caption("Gere e consulte resumos das transcrições via Map-Reduce.")

    def load_transcriptions():
        try:
            r = requests.get(f"{API}/summarize", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            st.error(f"Erro ao carregar transcrições: {e}")
            return []

    if "resumos_data" not in st.session_state:
        st.session_state.resumos_data = []

    col_refresh, col_all = st.columns([1, 1])
    with col_refresh:
        if st.button("🔄 Atualizar lista"):
            st.session_state.resumos_data = load_transcriptions()
    with col_all:
        if st.button("⚡ Resumir todos pendentes", type="primary"):
            with st.spinner("Resumindo todas as aulas sem resumo… (pode demorar)"):
                try:
                    r = requests.post(f"{API}/summarize/all", timeout=600)
                    r.raise_for_status()
                    st.success(f"{len(r.json())} resumo(s) gerado(s).")
                    st.session_state.resumos_data = load_transcriptions()
                except Exception as e:
                    st.error(f"Erro: {e}")

    if not st.session_state.resumos_data:
        st.session_state.resumos_data = load_transcriptions()

    transcriptions = st.session_state.resumos_data

    if not transcriptions:
        st.info("Nenhuma transcrição encontrada. Execute o pipeline de transcrição primeiro.")
    else:
        # Group by course → topic
        from collections import defaultdict
        grouped: dict = defaultdict(lambda: defaultdict(list))
        for t in transcriptions:
            grouped[t["course"]][t["topic"]].append(t)

        for course_name, topics in sorted(grouped.items()):
            all_aulas = [t for aulas in topics.values() for t in aulas]
            n_course_done = sum(1 for t in all_aulas if t["summarized"])
            with st.expander(f"📚 {course_name} · {n_course_done}/{len(all_aulas)} resumidos", expanded=False):
              for topic_name, aulas in sorted(topics.items()):
                n_done = sum(1 for t in aulas if t["summarized"])
                with st.expander(f"**{topic_name}** · {n_done}/{len(aulas)} resumidos", expanded=False):
                    aulas_sorted = sorted(aulas, key=lambda x: x["aula_number"] or 0)
                    for t in aulas_sorted:
                        fname = t["file_path"].replace("\\", "/").split("/")[-1]
                        aula_label = fname.rsplit(".", 1)[0]
                        icon = "✅" if t["summarized"] else "⏳"
                        st.markdown(f"**{icon} {aula_label}**")
                        st.caption(f"ID: {t['id']} · {t['created_at'][:10]}")
                        if t.get("video_url"):
                            st.link_button("▶ Assistir aula", t["video_url"], key=f"yt_{t['id']}")
                        if t["summarized"]:
                            st.markdown(t["summary"])
                        else:
                            if st.button("Gerar resumo", key=f"summarize_{t['id']}"):
                                with st.spinner(f"Resumindo {aula_label}… (pode demorar alguns minutos)"):
                                    try:
                                        r = requests.post(f"{API}/summarize/{t['id']}", timeout=600)
                                        if r.ok:
                                            st.success("Resumo gerado!")
                                            st.markdown(r.json()["summary"])
                                            st.session_state.resumos_data = load_transcriptions()
                                            st.rerun()
                                        else:
                                            st.error(f"Erro {r.status_code}: {r.text[:200]}")
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
                        st.divider()


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
