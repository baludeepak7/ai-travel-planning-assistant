from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.config import Settings


def chat_model(settings: Settings):
    settings.validate_llm()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        reasoning_effort=settings.openai_reasoning_effort or None,
        timeout=settings.llm_timeout_seconds,
        max_retries=1,
    )


def embeddings(settings: Settings):
    if settings.embedding_provider == "local":
        return LocalEmbeddings()
    if settings.embedding_provider != "openai":
        raise ValueError("EMBEDDING_PROVIDER must be local or openai")
    if not settings.openai_api_key.get_secret_value():
        raise ValueError("Set OPENAI_API_KEY in .env before embedding the knowledge base.")
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )


from langchain_core.embeddings import Embeddings


class LocalEmbeddings(Embeddings):
    """Real pretrained all-MiniLM-L6-v2 semantic embeddings via ONNX CPU."""

    def __init__(self):
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self.model = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
