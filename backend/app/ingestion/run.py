import os
import sys
import yaml
import asyncio
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.db import AsyncSessionLocal, Base, engine as pg_engine
from app.ingestion.crawler import SchemeCrawler
from app.agents.extractor import MockLLMProvider, GeminiLLMProvider
from app.services.scheme_service import process_and_save_scheme
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import MockEmbedder, GeminiEmbeddingProvider
from app.models.scheme import SchemeChunk
from sqlalchemy import select, delete

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IngestionCLI")

SOURCES_FILE = os.path.join(os.path.dirname(__file__), "sources.yaml")

def load_sources_config() -> Dict[str, Any]:
    if not os.path.exists(SOURCES_FILE):
        raise FileNotFoundError(f"Sources config file not found: {SOURCES_FILE}")
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def get_working_session_maker():
    # Attempt Postgres connection
    try:
        async with pg_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return AsyncSessionLocal
    except Exception:
        logger.info("PostgreSQL service not reachable on localhost:5432. Falling back to local async SQLite db 'scheme_agent.db' for CLI ingestion...")
        sqlite_engine = create_async_engine(
            "sqlite+aiosqlite:///scheme_agent.db",
            future=True
        )
        async with sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)

async def run_ingestion(source_id: str = None, limit: int = None, reindex: bool = False):
    config = load_sources_config()
    allowlist = config.get("allowlisted_domains", [])
    all_sources = config.get("sources", [])

    if source_id:
        sources_to_process = [s for s in all_sources if s.get("id") == source_id]
        if not sources_to_process:
            logger.error(f"Source ID '{source_id}' not found in sources.yaml")
            return
    else:
        sources_to_process = all_sources

    if limit and limit > 0:
        sources_to_process = sources_to_process[:limit]

    logger.info(f"Starting ingestion for {len(sources_to_process)} source(s)...")

    session_maker = await get_working_session_maker()

    crawler = SchemeCrawler(allowlisted_domains=allowlist)
    
    if settings.LLM_API_KEY == "placeholder":
        extractor = MockLLMProvider()
        embedder = MockEmbedder()
    else:
        extractor = GeminiLLMProvider(api_key=settings.LLM_API_KEY)
        embedder = GeminiEmbeddingProvider(api_key=settings.LLM_API_KEY)

    chunker = DocumentChunker()

    stats = {
        "fetched": 0,
        "extracted": 0,
        "flagged": 0,
        "rejected": 0
    }

    async with session_maker() as db:
        if reindex:
            logger.info("Reindexing requested: clearing existing scheme chunks...")
            try:
                await db.execute(delete(SchemeChunk))
                await db.commit()
            except Exception as e:
                logger.warning(f"Reindex clear warning: {e}")

        for src in sources_to_process:
            url = src.get("url")
            s_id = src.get("id")
            s_type = src.get("type", "html")
            
            logger.info(f"Processing source [{s_id}]: {url}")
            crawled = await crawler.fetch_url(url)
            if not crawled:
                stats["rejected"] += 1
                logger.warning(f"Rejected or failed to fetch: {url}")
                continue

            stats["fetched"] += 1
            raw_text = crawled["raw_text"]
            c_hash = crawled["content_hash"]

            try:
                extracted_data = await extractor.extract_scheme(raw_text, url)
                stats["extracted"] += 1

                scheme, is_updated = await process_and_save_scheme(
                    db=db,
                    extracted=extracted_data,
                    raw_text=raw_text,
                    source_url=url,
                    content_hash=c_hash,
                    source_type=s_type
                )

                if scheme.status == "unverified":
                    stats["flagged"] += 1

                # Chunking and embedding generation
                scheme_dict = extracted_data.model_dump()
                chunks = chunker.chunk_scheme(str(scheme.id), scheme_dict, url)

                # Clear old chunks for this scheme
                await db.execute(delete(SchemeChunk).where(SchemeChunk.scheme_id == scheme.id))
                
                for ch in chunks:
                    emb_vec = await embedder.get_embedding(ch["text"])
                    chunk_obj = SchemeChunk(
                        scheme_id=scheme.id,
                        section=ch["section"],
                        text=ch["text"],
                        source_url=ch["source_url"],
                        embedding=emb_vec
                    )
                    db.add(chunk_obj)
                await db.commit()
                logger.info(f"Ingested and chunked scheme '{scheme.name}' (Status: {scheme.status})")

            except Exception as e:
                logger.error(f"Extraction or DB save failed for {url}: {str(e)}")
                stats["rejected"] += 1

    # Log IngestionRun record
    try:
        from app.models.scheme import IngestionRun
        async with session_maker() as db_run:
            irun = IngestionRun(
                source=source_id or "all_sources",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                fetched=stats["fetched"],
                extracted=stats["extracted"],
                flagged=stats["flagged"],
                rejected=stats["rejected"],
                errors={"details": f"Processed {len(sources_to_process)} sources"}
            )
            db_run.add(irun)
            await db_run.commit()
    except Exception as e_run:
        logger.warning(f"Could not log IngestionRun: {e_run}")

    print("\n" + "=" * 55)
    print("      OFFLINE INGESTION PIPELINE SUMMARY")
    print("=" * 55)
    print(f"  Total Sources Processed: {len(sources_to_process)}")
    print(f"  Successfully Fetched:    {stats['fetched']}")
    print(f"  Successfully Extracted:  {stats['extracted']}")
    print(f"  Flagged (Unverified):    {stats['flagged']}")
    print(f"  Rejected / Failed:       {stats['rejected']}")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheme Offline Ingestion CLI")
    parser.add_argument("--source", type=str, help="Specific source ID to ingest")
    parser.add_argument("--limit", type=int, help="Maximum number of sources to ingest")
    parser.add_argument("--reindex", action="store_true", help="Reindex and re-chunk vector store")

    args = parser.parse_args()
    asyncio.run(run_ingestion(source_id=args.source, limit=args.limit, reindex=args.reindex))
