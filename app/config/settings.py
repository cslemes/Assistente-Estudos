from pydantic_settings import BaseSettings
from typing import Optional


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
5. **Se não encontrar no contexto** — diga claramente que o assunto não foi encontrado nas aulas disponíveis.

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
5. **Se não encontrar no contexto** — diga claramente que o assunto não foi encontrado nas aulas disponíveis.

Contexto:
{context}

Pergunta: {query}

Responda em português, de forma didática e completa."""

    # LangSmith Configuration
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "assistente-estudos"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing: bool = False

    model_config = {"env_file": ".env", "extra": "allow"}
