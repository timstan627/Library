"""
Public API - Configured catalog shelves (no auth).

Returns the admin-configured shelf definitions the homepage and /browse
should render, active ones in display order. An empty list means "no
custom configuration" and the frontend falls back to its built-in shelfs.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.catalog import CatalogShelf
from app.schemas.catalog import ShelfItemPayload

router = APIRouter()


@router.get("/shelves", response_model=List[ShelfItemPayload])
async def get_shelves(db: AsyncSession = Depends(get_db)):
    """Active catalog shelves in display order (public)."""
    result = await db.execute(
        select(CatalogShelf)
        .where(CatalogShelf.is_active == True)  # noqa: E712
        .order_by(CatalogShelf.position, CatalogShelf.created_at)
    )
    return [
        ShelfItemPayload(
            id=str(s.id), title=s.title, source_type=s.source_type,
            source_value=s.source_value, item_limit=s.item_limit,
        )
        for s in result.scalars().all()
    ]
