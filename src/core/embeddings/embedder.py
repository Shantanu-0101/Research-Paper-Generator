# src/core/embeddings/embedder.py
from sentence_transformers import SentenceTransformer
from src.core.config import settings


class Embedder:

    def __init__(self):
        if settings.embedding_provider != "local":
            raise ValueError(
                f"Unsupported EMBEDDING_PROVIDER '{settings.embedding_provider}'"
            )

        self.model = SentenceTransformer(settings.embedding_model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds a batch of chunk texts. Returns one vector per text."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embeds a single query string (e.g. the user's topic+section)."""
        embedding = self.model.encode([text], show_progress_bar=False)
        return embedding[0].tolist()
