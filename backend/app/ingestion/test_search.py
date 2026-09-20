import asyncio
from app.ingestion.run import get_working_session_maker
from app.rag.retriever import HybridRetriever

async def test_search_query():
    session_maker = await get_working_session_maker()
    retriever = HybridRetriever()

    query = "scholarship for engineering students Maharashtra"
    print(f"\nExecuting Hybrid Search Query: '{query}'...")
    
    async with session_maker() as db:
        results = await retriever.search(
            db=db,
            query=query,
            state_filter="Maharashtra",
            top_k=5
        )

        print(f"\nFound {len(results)} matching chunks (Fused with RRF):")
        for i, res in enumerate(results, start=1):
            print(f"\n[{i}] Scheme: {res['scheme_name']}")
            print(f"    Section: {res['section']} | State: {res['state']} | RRF Score: {res['rrf_score']}")
            print(f"    Source URL: {res['source_url']}")
            print(f"    Chunk Text snippet: {res['text'][:150]}...")

if __name__ == "__main__":
    asyncio.run(test_search_query())
