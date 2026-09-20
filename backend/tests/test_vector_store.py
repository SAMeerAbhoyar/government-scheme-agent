import pytest
import uuid
import numpy as np
from app.models.scheme import Scheme, SchemeChunk
from app.rag.vector_store import SQLiteNumpyVectorStore
from app.rag.retriever import HybridRetriever

@pytest.mark.asyncio
async def test_vector_store_top_k_order_and_filters(db_session):
    # 1. Create 3 schemes (2 Active in Maharashtra, 1 Active in Central, 1 Inactive)
    s1 = Scheme(
        id=uuid.uuid4(),
        name="MH Scheme 1",
        state="Maharashtra",
        category="Agriculture",
        status="active"
    )
    s2 = Scheme(
        id=uuid.uuid4(),
        name="Central Scheme 1",
        state="Central",
        category="Agriculture",
        status="active"
    )
    s3 = Scheme(
        id=uuid.uuid4(),
        name="Inactive Scheme",
        state="Maharashtra",
        category="Agriculture",
        status="inactive"
    )
    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    # Base query vector (768 dimensions)
    vec_base = np.zeros(768, dtype=np.float32)
    vec_base[0] = 1.0

    # Chunk 1: Very close vector (sim ~ 1.0)
    c1 = SchemeChunk(
        id=uuid.uuid4(),
        scheme_id=s1.id,
        section="eligibility",
        text="Farmer grant in Maharashtra",
        embedding=vec_base.tolist()
    )

    # Chunk 2: Orthogonal vector (sim ~ 0.0)
    vec_ortho = np.zeros(768, dtype=np.float32)
    vec_ortho[1] = 1.0
    c2 = SchemeChunk(
        id=uuid.uuid4(),
        scheme_id=s2.id,
        section="eligibility",
        text="Central farmer assistance",
        embedding=vec_ortho.tolist()
    )

    # Chunk 3: Opposite vector (sim ~ -1.0) on inactive scheme
    vec_opp = np.zeros(768, dtype=np.float32)
    vec_opp[0] = -1.0
    c3 = SchemeChunk(
        id=uuid.uuid4(),
        scheme_id=s3.id,
        section="eligibility",
        text="Inactive farmer scheme",
        embedding=vec_opp.tolist()
    )

    db_session.add_all([c1, c2, c3])
    await db_session.commit()

    store = SQLiteNumpyVectorStore(expected_dim=768)

    # Query with vec_base
    results = await store.search(
        db_session,
        query_vector=vec_base.tolist(),
        state_filter="Maharashtra",
        category_filter="Agriculture",
        top_k=5
    )

    # Inactive scheme (s3) should be filtered out.
    # s1 and s2 should remain, ordered by similarity score (c1 first, c2 second).
    assert len(results) == 2
    top_sim, top_chunk, top_scheme = results[0]
    second_sim, second_chunk, second_scheme = results[1]

    assert top_scheme.name == "MH Scheme 1"
    assert top_sim > 0.99
    assert second_scheme.name == "Central Scheme 1"
    assert abs(second_sim) < 0.01

@pytest.mark.asyncio
async def test_fts_and_hybrid_retriever_search(db_session):
    scheme = Scheme(
        id=uuid.uuid4(),
        name="Scholarship for Engineering",
        state="Maharashtra",
        category="Education",
        status="active"
    )
    db_session.add(scheme)
    await db_session.commit()

    chunk = SchemeChunk(
        id=uuid.uuid4(),
        scheme_id=scheme.id,
        section="benefits",
        text="Tuition fee reimbursement for degree in engineering students",
        embedding=[0.01] * 768
    )
    db_session.add(chunk)
    await db_session.commit()

    retriever = HybridRetriever()
    results = await retriever.search(
        db_session,
        query="engineering tuition fee scholarship",
        state_filter="Maharashtra",
        category_filter="Education",
        top_k=5
    )

    assert len(results) > 0
    match = results[0]
    assert match["scheme_name"] == "Scholarship for Engineering"
    assert "engineering" in match["text"].lower()
