from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "3072"))

    # Pinecone
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "triageiq-openai-self-rag")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "aiops-runbooks")
    pinecone_cloud: str = os.getenv("PINECONE_CLOUD", "aws")
    pinecone_region: str = os.getenv("PINECONE_REGION", "us-east-1")

    # Internet search
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

    # Self-RAG controls
    top_k: int = int(os.getenv("TOP_K", "5"))
    max_support_retries: int = int(os.getenv("MAX_SUPPORT_RETRIES", "2"))
    max_retrieval_rewrites: int = int(os.getenv("MAX_RETRIEVAL_REWRITES", "2"))
    max_web_rewrites: int = int(os.getenv("MAX_WEB_REWRITES", "2"))
    database_path: str = os.getenv("DATABASE_PATH", "data/audit.db")

    # ADAPTATION (not in the reference repo): demo_mode lets the identical
    # workflow run with no API keys - "auto" uses the offline layer only
    # when OpenAI or Pinecone keys are missing; "online" forces the
    # reference behaviour (raise when a key is missing).
    demo_mode: str = os.getenv("DEMO_MODE", "auto")

    @property
    def database_file(self) -> Path:
        p = Path(self.database_path)
        return p if p.is_absolute() else ROOT / p

    @property
    def offline_mode(self) -> bool:
        if self.demo_mode == "offline":
            return True
        if self.demo_mode == "online":
            return False
        return not (self.openai_api_key and self.pinecone_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
