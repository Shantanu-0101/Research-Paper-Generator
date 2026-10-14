# src/core/vectorstore/faiss_store.py
import os
import pickle
import numpy as np
import faiss
from src.core.config import settings


class FaissStore:

    def __init__(self):
        self.index = None
        self.chunks: list[dict] = []

    def build(self, chunks: list[dict], vectors: list[list[float]]):
        """Builds a fresh index from chunks + their embeddings."""
        vectors_np = np.array(vectors, dtype="float32")
        dimension = vectors_np.shape[1]

        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(vectors_np)
        self.chunks = chunks

    def search(self, query_vector: list[float], k: int = None) -> list[dict]:
        if self.index is None:
            raise ValueError("Index is empty — call build() or load() first")

        k = k or settings.top_k
        query_np = np.array([query_vector], dtype="float32")
        distances, indices = self.index.search(query_np, k)

        results = []
        for idx in indices[0]:
            if idx != -1:
                results.append(self.chunks[idx])
        return results

    def save(self):
        """Persists the index + chunk metadata to disk."""
        os.makedirs(settings.vector_store_dir, exist_ok=True)
        faiss.write_index(self.index, f"{settings.vector_store_dir}/index.faiss")
        with open(f"{settings.vector_store_dir}/chunks.pkl", "wb") as f:
            pickle.dump(self.chunks, f)

    def load(self):
        """Reloads a previously saved index + chunk metadata."""
        self.index = faiss.read_index(f"{settings.vector_store_dir}/index.faiss")
        with open(f"{settings.vector_store_dir}/chunks.pkl", "rb") as f:
            self.chunks = pickle.load(f)
