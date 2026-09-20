import pytest
from app.models.scheme import Scheme, SchemeChunk
from app.rag.retriever import HybridRetriever
from app.rag.embeddings import MockEmbedder

@pytest.mark.asyncio
async def test_hybrid_rrf_retriever(db_session):
    # 1. Seed two active schemes (one Maharashtra, one Central)
    s1 = Scheme(
        name="Maharashtra Engineering Scholarship",
        description="Scholarship for engineering students in Maharashtra.",
        state="Maharashtra",
        category="Education",
        status="active",
        source_url="https://maharashtra.gov.in/eng-scholarship"
    )
    s2 = Scheme(
        name="Central Agricultural Fertilizer Subsidy",
        description="Fertilizer subsidy for farmers across India.",
        state="Central",
        category="Agriculture",
        status="active",
        source_url="https://pmkisan.gov.in/fertilizer"
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    embedder = MockEmbedder()
    t1 = "Scholarship for undergraduate engineering students in Maharashtra"
    t2 = "Fertilizer subsidy for all farmers in India"

    v1 = await embedder.get_embedding(t1)
    v2 = await embedder.get_embedding(t2)

    c1 = SchemeChunk(
        scheme_id=s1.id,
        section="eligibility",
        text=t1,
        source_url=s1.source_url,
        embedding=v1
    )
    c2 = SchemeChunk(
        scheme_id=s2.id,
        section="eligibility",
        text=t2,
        source_url=s2.source_url,
        embedding=v2
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    retriever = HybridRetriever(embedder=embedder)

    # 2. Search query for engineering scholarship
    results = await retriever.search(
        db=db_session,
        query="scholarship for engineering students Maharashtra",
        state_filter="Maharashtra",
        top_k=5
    )

    assert len(results) > 0
    top = results[0]
    assert top["scheme_name"] == "Maharashtra Engineering Scholarship"
    assert "source_url" in top
    assert top["rrf_score"] > 0
