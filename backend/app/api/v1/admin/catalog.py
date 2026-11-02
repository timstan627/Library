"""
Admin API - Catalog Shelves (SQLAlchemy)

CRUD for the discovery shelf rows rendered by the homepage and /browse.
A configured, active shelf set replaces the frontend's built-in default
shelves; an empty (or failed) read means the frontend keeps its defaults.
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.catalog import CatalogShelf
from app.schemas.catalog import (
    CatalogShelfCreate, CatalogShelfUpdate, CatalogShelfResponse, MoveDirectionRequest,
)
from app.api.v1.deps import require_admin
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()

# Shelf types that read fixed datasets (no source_value) vs. value-driven ones.
_VALUE_TYPES = {"tag", "branch", "subject"}


def _validate_shelf_data(data: CatalogShelfCreate | CatalogShelfUpdate) -> None:
    if data.source_type in _VALUE_TYPES:
        if not (data.source_value or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A source value is required for source_type '{data.source_type}'",
            )
        data.source_value = data.source_value.strip()[:100]
    else:
        data.source_value = None


async def _next_position(db: AsyncSession) -> int:
    max_pos = (await db.execute(
        select(func.max(CatalogShelf.position))
    )).scalar()
    return (max_pos if max_pos is not None else -1) + 1


def _respond(shelf: CatalogShelf) -> CatalogShelfResponse:
    return CatalogShelfResponse(
        id=str(shelf.id), title=shelf.title, source_type=shelf.source_type,
        source_value=shelf.source_value, item_limit=shelf.item_limit,
        position=shelf.position, is_active=shelf.is_active,
    )


async def _audit(db: AsyncSession, actor: User, action: str, shelf: CatalogShelf, details: dict) -> None:
    """Audit failure must never fail the user action (unified policy)."""
    try:
        db.add(AuditLog(
            action=action, actor_id=actor.id, target_type="catalog_shelf",
            target_id=str(shelf.id), details_json=json.dumps(details),
        ))
    except Exception:
        logger.exception("Audit log error for catalog shelf %s", action)


@router.get("", response_model=List[CatalogShelfResponse])
async def list_shelves(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List every shelf row (including inactive ones) in display order."""
    result = await db.execute(select(CatalogShelf).order_by(CatalogShelf.position, CatalogShelf.created_at))
    return [_respond(s) for s in result.scalars().all()]


@router.post("", response_model=CatalogShelfResponse, status_code=status.HTTP_201_CREATED)
async def create_shelf(
    data: CatalogShelfCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a shelf; it is appended at the end unless a position is given."""
    _validate_shelf_data(data)
    shelf = CatalogShelf(**data.model_dump())
    if shelf.position == 0:
        shelf.position = await _next_position(db)
    db.add(shelf)
    await db.flush()
    await db.refresh(shelf)
    await _audit(db, current_user, "create_catalog_shelf", shelf, {
        "title": shelf.title, "source_type": shelf.source_type,
        "source_value": shelf.source_value, "position": shelf.position,
    })
    await db.commit()
    return _respond(shelf)


@router.put("/{shelf_id}", response_model=CatalogShelfResponse)
async def update_shelf(
    shelf_id: str,
    data: CatalogShelfUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CatalogShelf).where(CatalogShelf.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    _validate_shelf_data(data)
    changed = data.model_dump()
    for key, value in changed.items():
        setattr(shelf, key, value)
    await _audit(db, current_user, "update_catalog_shelf", shelf, changed)
    await db.commit()
    await db.refresh(shelf)
    return _respond(shelf)


@router.patch("/{shelf_id}/toggle", response_model=CatalogShelfResponse)
async def toggle_shelf(
    shelf_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CatalogShelf).where(CatalogShelf.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    shelf.is_active = not shelf.is_active
    await _audit(db, current_user, "toggle_catalog_shelf", shelf, {"is_active": shelf.is_active})
    await db.commit()
    await db.refresh(shelf)
    return _respond(shelf)


@router.patch("/{shelf_id}/move", response_model=List[CatalogShelfResponse])
async def move_shelf(
    shelf_id: str,
    data: MoveDirectionRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Swap the shelf with its nearest neighbor in display order."""
    result = await db.execute(select(CatalogShelf).order_by(CatalogShelf.position, CatalogShelf.created_at))
    ordered = list(result.scalars().all())
    index = next((i for i, shelf in enumerate(ordered) if str(shelf.id) == shelf_id), None)
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")

    neighbor = index - 1 if data.direction == "up" else index + 1
    if 0 <= neighbor < len(ordered):
        # Normalize positions as contiguous indexes so duplicates/gaps
        # left by edits can never break later swaps.
        for i, shelf in enumerate(ordered):
            if shelf.position != i:
                shelf.position = i
        a, b = ordered[index], ordered[neighbor]
        a.position, b.position = b.position, a.position
        await _audit(db, current_user, "move_catalog_shelf", a, {
            "direction": data.direction, "position": a.position,
        })
        await db.commit()

    result = await db.execute(select(CatalogShelf).order_by(CatalogShelf.position, CatalogShelf.created_at))
    return [_respond(s) for s in result.scalars().all()]


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelf(
    shelf_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CatalogShelf).where(CatalogShelf.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    await db.delete(shelf)
    await _audit(db, current_user, "delete_catalog_shelf", shelf, {
        "title": shelf.title, "source_type": shelf.source_type,
    })
    await db.commit()
