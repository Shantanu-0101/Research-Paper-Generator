import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class Settings:

    llm_provider: str = os.getenv("LLM_PROVIDER", "xai").lower()

    # xAI (Grok)
    xai_api_key: str = os.getenv("XAI_API_KEY", "")
    xai_model: str = os.getenv("XAI_MODEL", "grok-2")

    # Groq
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # Gemini
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    # OpenRouter
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "")

    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    unsplash_api_key: str = os.getenv("UNSPLASH_API_KEY", "")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local").lower()
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"
    )

    chunk_size: int = int(os.getenv("CHUNK_SIZE", 1000))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", 200))
    top_k: int = int(os.getenv("TOP_K", 5))
    min_files: int = 3
    max_files: int = 8

    upload_dir: str = "data/uploads"
    vector_store_dir: str = "data/vector_store"

    def validate(self) -> None:

        provider_key_map = {
            "xai": self.xai_api_key,
            "groq": self.groq_api_key,
            "gemini": self.google_api_key,
            "openrouter": self.openrouter_api_key,
        }

        if self.llm_provider not in provider_key_map:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.llm_provider}'."
                f"Choose one of: {list(provider_key_map)}"
            )

        if not provider_key_map[self.llm_provider]:
            raise ValueError(
                f"LLM_PROVIDER is '{self.llm_provider}' but its "
                f"API key is missing in .env"
            )

        if self.embedding_provider != "local":
            raise ValueError(f"Unknown EMBEDDING_PROVIDER '{self.embedding_provider}'. Choose 'local'")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


settings = Settings()
