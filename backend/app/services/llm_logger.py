import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.models.activity import LLMCall

logger = logging.getLogger(__name__)

async def log_llm_call(
    purpose: str,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_ms: int = 0,
    cost_estimate: float = 0.0,
    success: bool = True
):
    """
    Audit log helper for LLM calls.
    """
    try:
        async with AsyncSessionLocal() as db:
            call_rec = LLMCall(
                purpose=purpose,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_estimate=cost_estimate,
                success=success
            )
            db.add(call_rec)
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to log LLM call to DB: {e}")
