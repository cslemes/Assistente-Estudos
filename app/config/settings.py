from typing import Optional

from pydantic_settings import BaseSettings

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")


class Settings(BaseSettings):
    # API Configuration
    api_title: str = "Assistente Estudos API"
    api_description: str = "RAG API for PUC-Rio AI classes"
    api_version: str = "1.0.0"

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection_name: str = "aulas"
    qdrant_timeout: float = 60.0
    prefetch_limit: int = 25

    # Embedding Models
    dense_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    bm25_model_name: str = "Qdrant/bm25"
    late_interaction_model_name: str = "colbert-ir/colbertv2.0"

    # LLM Provider Selection ("groq" or "openai")
    llm_provider: str = "groq"

    # Transcription Provider Selection ("deepgram", "openai", "groq")
    transcription_provider: str = "deepgram"
    openai_whisper_model: str = "whisper-1"
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.5
    openai_max_output_tokens: int = 4096
    openai_system_prompt: str = """Você é um assistente acadêmico especializado nas aulas de Pós-Graduação em IA da PUC-Rio.
Seu papel principal é explicar e ensinar o conteúdo das aulas, usando os trechos do contexto como base.

Cada trecho do contexto tem um cabeçalho no formato [Curso — Tópico | link] indicando de qual aula veio.

Como responder:
1. **Explique o conteúdo** — responda à pergunta de forma completa, usando as informações do contexto. Se o professor explicou um conceito, reproduza e elabore essa explicação.
2. **Cite a fonte** — ao final ou inline, mencione de qual aula/tópico veio a informação (ex: "como explicado na aula de Redes Neurais...").
3. **Inclua o link** — se houver link de vídeo no cabeçalho, inclua-o para o aluno assistir o trecho exato.
4. **Se a pergunta for "em qual aula"** — responda com o tópico/curso E dê um resumo do que foi explicado.
5. **Se o contexto não cobrir completamente o tema** — complemente com seu conhecimento geral sobre IA, deixando claro o que veio das aulas e o que é conhecimento geral.

Contexto:
{context}

Pergunta: {query}

Responda em português, de forma didática e completa."""

    # Groq Configuration
    Groq_api_key: Optional[str] = None
    Groq_model: str = "openai/gpt-oss-120b"
    Groq_temperature: float = 0.5
    Groq_max_output_tokens: int = 4096
    Groq_system_prompt: str = """Você é um assistente acadêmico especializado nas aulas de Pós-Graduação em IA da PUC-Rio.
Seu papel principal é explicar e ensinar o conteúdo das aulas, usando os trechos do contexto como base.

Cada trecho do contexto tem um cabeçalho no formato [Curso — Tópico | link] indicando de qual aula veio.

Como responder:
1. **Explique o conteúdo** — responda à pergunta de forma completa, usando as informações do contexto. Se o professor explicou um conceito, reproduza e elabore essa explicação.
2. **Cite a fonte** — ao final ou inline, mencione de qual aula/tópico veio a informação (ex: "como explicado na aula de Redes Neurais...").
3. **Inclua o link** — se houver link de vídeo no cabeçalho, inclua-o para o aluno assistir o trecho exato.
4. **Se a pergunta for "em qual aula"** — responda com o tópico/curso E dê um resumo do que foi explicado.
5. **Se o contexto não cobrir completamente o tema** — complemente com seu conhecimento geral sobre IA, deixando claro o que veio das aulas e o que é conhecimento geral.

Contexto:
{context}

Pergunta: {query}

Responda em português, de forma didática e completa."""

    # Summarization
    summarize_chunk_size: int = 3000  # chars per Map chunk (~750 tokens)
    summarize_max_tokens: int = 1024  # max output tokens per LLM call
    summarize_reduce_max_chars: int = 15000  # max chars fed into a single Reduce call
    summarize_tpm_limit: int = (
        7500  # token-per-minute budget (leave headroom below provider limit)
    )
    # Use a large-context model for summarization, independent of chat model
    summarize_groq_model: str = (
        "llama-3.3-70b-versatile"  # 128k ctx, better for long transcripts
    )
    summarize_openai_model: str = "gpt-4o-mini"

    # Model used for flashcard generation (needs JSON output + decent context)
    flashcard_groq_model: str = "llama-3.3-70b-versatile"
    flashcard_openai_model: str = "gpt-4o-mini"
    summarize_map_prompt: str = (
        "Você é um assistente acadêmico especializado em IA. "
        "Resuma o trecho de aula abaixo em português, destacando: "
        "conceitos principais, definições, exemplos e fórmulas. "
        "Seja objetivo e preserve termos técnicos.\n\n{chunk}"
    )
    summarize_reduce_prompt: str = (
        "Você é um assistente acadêmico especializado em IA. "
        "A seguir estão resumos parciais de uma aula longa. "
        "Combine-os em um único guia de estudo executivo em português, "
        "organizado por tópicos, com destaques para conceitos-chave, "
        "definições e exemplos práticos.\n\n{partial_summaries}"
    )

    # Cloudflare R2 Storage
    cloudflare_account_id: Optional[str] = None
    cloudflare_r2_access_key_id: Optional[str] = None
    cloudflare_r2_secret_access_key: Optional[str] = None
    cloudflare_r2_bucket_name: Optional[str] = None
    cloudflare_r2_public_url: Optional[str] = None  # e.g. https://pub-xxx.r2.dev

    # LangSmith Configuration
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "assistente-estudos"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing: bool = False

    # RunPod Serverless GPU Workers
    use_runpod: bool = False
    runpod_api_key: Optional[str] = None
    runpod_timeout: int = 120
    runpod_base_url: str = "https://api.runpod.ai/v2"
    runpod_embed_endpoint_id: Optional[str] = None
    runpod_ner_endpoint_id: Optional[str] = None
    runpod_ocr_endpoint_id: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "allow"}
