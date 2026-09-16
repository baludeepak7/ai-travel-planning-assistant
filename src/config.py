import logging
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    llm_provider: str = "openai"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    openai_reasoning_effort: str = ""
    openai_base_url: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "local"
    chroma_dir: Path = ROOT / "data/chroma"
    collection_name: str = "singapore_travel"
    rag_top_k: int = Field(default=5, ge=1, le=10)
    rag_min_relevance: float = Field(default=0.3, ge=0, le=1)
    http_timeout_seconds: float = Field(default=10, gt=0)
    llm_timeout_seconds: float = Field(default=60, gt=0)
    app_destination: str = "Singapore"
    debug_provenance: bool = False

    def validate_llm(self):
        if self.llm_provider != "openai":
            raise ValueError("Set LLM_PROVIDER=openai (OpenAI-compatible endpoints supported).")
        if not self.openai_api_key.get_secret_value() or not self.openai_model:
            raise ValueError("Set OPENAI_API_KEY and OPENAI_MODEL in .env before starting.")


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
