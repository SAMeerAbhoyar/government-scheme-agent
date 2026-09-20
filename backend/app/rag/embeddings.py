import hashlib
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings

class BaseEmbeddingProvider(ABC):
    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        pass

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            emb = await self.get_embedding(text)
            results.append(emb)
        return results


class MockEmbedder(BaseEmbeddingProvider):
    """
    Deterministic Mock Embedder for testing and offline development.
    Generates a normalized pseudo-embedding based on SHA-256 hash of the input text.
    """
    async def get_embedding(self, text: str) -> List[float]:
        # Hash text to generate repeatable floats
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self.dimension):
            byte_val = h[i % len(h)]
            vec.append((byte_val / 255.0) - 0.5)

        # Normalize vector to unit length
        norm = (sum(x * x for x in vec)) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str = None, dimension: int = 768):
        super().__init__(dimension=dimension)
        self.api_key = api_key or settings.LLM_API_KEY

    async def get_embedding(self, text: str) -> List[float]:
        if not self.api_key or self.api_key == "placeholder":
            mock = MockEmbedder(dimension=self.dimension)
            return await mock.get_embedding(text)

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result["embedding"][:self.dimension]
        except Exception:
            mock = MockEmbedder(dimension=self.dimension)
            return await mock.get_embedding(text)
