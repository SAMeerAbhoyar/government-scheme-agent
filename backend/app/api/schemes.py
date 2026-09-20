from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.rag.retriever import HybridRetriever

router = APIRouter(prefix="/schemes", tags=["Schemes & Search"])
retriever = HybridRetriever()

@router.get("/search")
async def search_schemes(
    q: str = Query(..., min_length=2, description="Search query string"),
    state: Optional[str] = Query(None, description="Central or Maharashtra"),
    category: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    results = await retriever.search(
        db=db,
        query=q,
        state_filter=state,
        category_filter=category,
        top_k=limit
    )
    return {
        "query": q,
        "state_filter": state,
        "category_filter": category,
        "count": len(results),
        "results": results
    }
