import abc
import json
import logging
from typing import List, Optional, Tuple
import numpy as np
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scheme import Scheme, SchemeChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorStore(abc.ABC):
    @abc.abstractmethod
    async def search(
        self,
        db: AsyncSession,
        query_vector: List[float],
        state_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        top_k: int = 20
    ) -> List[Tuple[float, SchemeChunk, Scheme]]:
        """
        Search for top-k similar scheme chunks given a query vector.
        Returns a list of tuples: (similarity_score, chunk, scheme).
        """
        pass

class SQLiteNumpyVectorStore(VectorStore):
    def __init__(self, expected_dim: Optional[int] = None):
        self.expected_dim = expected_dim or settings.EMBEDDING_DIMENSION

    async def search(
        self,
        db: AsyncSession,
        query_vector: List[float],
        state_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        top_k: int = 20
    ) -> List[Tuple[float, SchemeChunk, Scheme]]:
        if not query_vector:
            return []

        # Validate embedding dimension
        if len(query_vector) != self.expected_dim:
            logger.warning(
                f"Query vector dimension {len(query_vector)} does not match expected {self.expected_dim}"
            )

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = float(np.linalg.norm(q_vec))
        if q_norm == 0:
            q_norm = 1.0

        base_stmt = select(SchemeChunk, Scheme).join(Scheme, SchemeChunk.scheme_id == Scheme.id)
        filters = [Scheme.status == "active"]
        if state_filter:
            filters.append(or_(Scheme.state == state_filter, Scheme.state == "Central"))
        if category_filter:
            filters.append(Scheme.category.ilike(f"%{category_filter}%"))

        stmt = base_stmt.where(*filters)
        res = await db.execute(stmt)
        rows = res.all()

        scored_items: List[Tuple[float, SchemeChunk, Scheme]] = []

        for chunk, scheme in rows:
            if chunk.embedding is None:
                continue
            emb_data = chunk.embedding
            if isinstance(emb_data, str):
                try:
                    emb_data = json.loads(emb_data)
                except Exception:
                    continue
            if not isinstance(emb_data, (list, tuple)) or len(emb_data) != self.expected_dim:
                continue

            c_vec = np.array(emb_data, dtype=np.float32)
            c_norm = float(np.linalg.norm(c_vec))
            if c_norm == 0:
                c_norm = 1.0

            # Cosine similarity
            dot_product = float(np.dot(q_vec, c_vec))
            sim = float(dot_product / (q_norm * c_norm))

            scored_items.append((sim, chunk, scheme))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return scored_items[:top_k]
