import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheme import Scheme
from app.core.config import settings

logger = logging.getLogger(__name__)

async def run_daily_maintenance(db: AsyncSession) -> Dict[str, int]:
    """
    Daily Maintenance Job:
    1. Marks schemes 'expired' when deadline_date has passed.
    2. Marks schemes 'outdated' after N consecutive fetch failures.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Expire past deadline schemes
    stmt_expired = (
        select(Scheme)
        .where(Scheme.status == "active")
        .where(Scheme.deadline_date.isnot(None))
        .where(Scheme.deadline_date < now)
    )
    res_expired = await db.execute(stmt_expired)
    expired_schemes = res_expired.scalars().all()

    expired_count = 0
    for s in expired_schemes:
        s.status = "expired"
        expired_count += 1
        logger.info(f"Maintenance: Scheme '{s.name}' (ID: {s.id}) marked expired due to past deadline date.")

    # 2. Mark outdated schemes with N+ fetch failures
    stmt_outdated = (
        select(Scheme)
        .where(Scheme.status == "active")
        .where(Scheme.consecutive_fetch_failures >= settings.MAX_CONSECUTIVE_FETCH_FAILURES)
    )
    res_outdated = await db.execute(stmt_outdated)
    outdated_schemes = res_outdated.scalars().all()

    outdated_count = 0
    for s in outdated_schemes:
        s.status = "outdated"
        outdated_count += 1
        logger.info(f"Maintenance: Scheme '{s.name}' (ID: {s.id}) marked outdated after {s.consecutive_fetch_failures} fetch failures.")

    await db.commit()

    return {
        "expired_count": expired_count,
        "outdated_count": outdated_count
    }

async def record_fetch_failure(db: AsyncSession, source_url: str):
    """
    Increments consecutive_fetch_failures counter for a scheme on fetch failure.
    If limit reached, updates status to 'outdated'.
    """
    stmt = select(Scheme).where(Scheme.source_url == source_url)
    res = await db.execute(stmt)
    schemes = res.scalars().all()

    for s in schemes:
        s.consecutive_fetch_failures += 1
        s.last_fetched_at = datetime.now(timezone.utc)

    await db.commit()
