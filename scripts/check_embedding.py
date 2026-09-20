import os
import sys
import asyncio

# Ensure backend directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(script_dir, "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.rag.embeddings import GeminiEmbeddingProvider, MockEmbedder

async def check_embedding():
    sentence = "Government scheme recommendation agent for citizens"

    if not settings.LLM_API_KEY or settings.LLM_API_KEY == "placeholder":
        embedder = MockEmbedder(dimension=settings.EMBEDDING_DIMENSION)
    else:
        embedder = GeminiEmbeddingProvider(api_key=settings.LLM_API_KEY, dimension=settings.EMBEDDING_DIMENSION)

    try:
        vec = await embedder.get_embedding(sentence)
        vec_len = len(vec)
        print(f"Embedding vector length: {vec_len}")

        if vec_len == 768:
            print("768")
        else:
            print(f"Error: Vector length is {vec_len}, expected 768.")
            print(f"Suggested fix: Update EMBEDDING_DIMENSION setting in config or check model '{settings.EMBEDDING_MODEL}'.")
            sys.exit(1)
    except Exception as e:
        print(f"Error generating embedding with model '{settings.EMBEDDING_MODEL}': {e}")
        print("Suggested fix: Verify LLM_API_KEY and EMBEDDING_MODEL setting in configuration.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_embedding())
