import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheme import Scheme, SchemeChunk
from app.rag.embeddings import BaseEmbeddingProvider, MockEmbedder

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, embedder: Optional[BaseEmbeddingProvider] = None):
        self.embedder = embedder or MockEmbedder()

    async def search(
        self,
        db: AsyncSession,
        query: str,
        state_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        top_k: int = 5,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        query_clean = query.strip()
        if not query_clean:
            return []

        # 1. Base Query with filters
        base_stmt = select(SchemeChunk, Scheme).join(Scheme, SchemeChunk.scheme_id == Scheme.id)
        
        # Apply metadata filters
        filters = [Scheme.status == "active"]
        if state_filter:
            filters.append(or_(Scheme.state == state_filter, Scheme.state == "Central"))
        if category_filter:
            filters.append(Scheme.category.ilike(f"%{category_filter}%"))

        # --- Sub-Search 1: Full-Text Search (FTS) Ranking ---
        fts_chunks = []
        try:
            # Query matching chunks containing search terms
            terms = [t for t in query_clean.lower().split() if len(t) > 2]
            if terms:
                fts_conditions = [SchemeChunk.text.ilike(f"%{t}%") for t in terms]
                fts_stmt = base_stmt.where(*filters).where(or_(*fts_conditions))
                result = await db.execute(fts_stmt)
                fts_rows = result.all()

                # Score FTS rows by keyword occurrence count
                scored_fts = []
                for chunk, scheme in fts_rows:
                    score = sum(chunk.text.lower().count(t) for t in terms)
                    scored_fts.append((score, chunk, scheme))
                scored_fts.sort(key=lambda x: x[0], reverse=True)
                fts_chunks = [(c, s) for _, c, s in scored_fts]
            else:
                fts_stmt = base_stmt.where(*filters).limit(20)
                result = await db.execute(fts_stmt)
                fts_chunks = [(c, s) for c, s in result.all()]
        except Exception as e:
            logger.error(f"FTS search error: {str(e)}")

        # --- Sub-Search 2: Vector Similarity Search ---
        vec_chunks = []
        try:
            query_vec = await self.embedder.get_embedding(query_clean)
            vec_stmt = base_stmt.where(*filters).limit(20)
            result = await db.execute(vec_stmt)
            all_chunks = [(c, s) for c, s in result.all()]

            # Score by vector similarity (dot product for unit vectors)
            scored_vec = []
            for chunk, scheme in all_chunks:
                if chunk.embedding is not None and len(chunk.embedding) == len(query_vec):
                    sim = sum(a * b for a, b in zip(chunk.embedding, query_vec))
                else:
                    sim = 0.0
                scored_vec.append((sim, chunk, scheme))
            scored_vec.sort(key=lambda x: x[0], reverse=True)
            vec_chunks = [(c, s) for _, c, s in scored_vec]
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")

        # --- Sub-Search 3: Reciprocal Rank Fusion (RRF) ---
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Tuple[SchemeChunk, Scheme]] = {}

        # FTS ranks
        for rank, (chunk, scheme) in enumerate(fts_chunks, start=1):
            cid = str(chunk.id)
            chunk_map[cid] = (chunk, scheme)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        # Vector ranks
        for rank, (chunk, scheme) in enumerate(vec_chunks, start=1):
            cid = str(chunk.id)
            chunk_map[cid] = (chunk, scheme)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        # Sort combined results by fused RRF score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        final_results = []
        for cid in sorted_cids[:top_k]:
            chunk, scheme = chunk_map[cid]
            final_results.append({
                "chunk_id": str(chunk.id),
                "scheme_id": str(scheme.id),
                "scheme_name": scheme.name,
                "section": chunk.section,
                "text": chunk.text,
                "source_url": chunk.source_url or scheme.source_url,
                "state": scheme.state,
                "category": scheme.category,
                "rrf_score": round(rrf_scores[cid], 6)
            })

        return final_results
