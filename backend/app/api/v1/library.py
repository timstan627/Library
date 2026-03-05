"""
Library API — Personal collection management for users.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.v1.deps import get_current_active_user
from app.models.user import User
from app.models.resource import Resource
from app.models.collection import Collection, CollectionItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["library"])


# ────────────────────────────────────────────────────────────────
# Schemas (inline Pydantic for simplicity)
# ────────────────────────────────────────────────────────────────
from pydantic import BaseModel, Field
from datetime import datetime


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    emoji: str = Field(default="📁", max_length=10)
    color: str = Field(default="#6366f1", max_length=7)


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    emoji: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=7)


class CollectionItemAdd(BaseModel):
    resource_ids: List[str]


class CollectionReorder(BaseModel):
    """List of resource IDs in the new order."""
    resource_ids: List[str]


class CollectionItemResponse(BaseModel):
    id: str
    resource_id: str
    sort_order: int
    added_at: datetime
    # Resource details (flattened)
    title: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_extension: Optional[str] = None
    mime_type: Optional[str] = None
    visibility: Optional[str] = None
    slug: Optional[str] = None

    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    emoji: str
    color: str
    sort_order: int
    item_count: int = 0
    total_size: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionDetailResponse(CollectionResponse):
    items: List[CollectionItemResponse] = []


# ────────────────────────────────────────────────────────────────
# Collection CRUD
# ────────────────────────────────────────────────────────────────

@router.get("/collections", response_model=List[CollectionResponse])
async def list_collections(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all collections for the current user."""
    result = await db.execute(
        select(Collection)
        .where(Collection.user_id == current_user.id)
        .options(selectinload(Collection.items).selectinload(CollectionItem.resource))
        .order_by(Collection.sort_order, Collection.created_at.desc())
    )
    collections = result.scalars().all()
    
    return [
        CollectionResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            emoji=c.emoji,
            color=c.color,
            sort_order=c.sort_order,
            item_count=c.item_count,
            total_size=c.total_size,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in collections
    ]


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    data: CollectionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new collection."""
    # Limit collections per user (max 50)
    count_result = await db.execute(
        select(func.count()).select_from(Collection).where(Collection.user_id == current_user.id)
    )
    count = count_result.scalar()
    if count >= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 collections allowed per user",
        )
    
    collection = Collection(
        user_id=current_user.id,
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
        emoji=data.emoji,
        color=data.color,
        sort_order=count,  # Append to end
    )
    db.add(collection)
    await db.flush()
    await db.refresh(collection)
    
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        emoji=collection.emoji,
        color=collection.color,
        sort_order=collection.sort_order,
        item_count=0,
        total_size=0,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.get("/collections/{collection_id}", response_model=CollectionDetailResponse)
async def get_collection(
    collection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get collection details with all items."""
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == current_user.id)
        .options(selectinload(Collection.items).selectinload(CollectionItem.resource))
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    
    items = []
    for item in sorted(collection.items, key=lambda x: x.sort_order):
        r = item.resource
        items.append(CollectionItemResponse(
            id=item.id,
            resource_id=item.resource_id,
            sort_order=item.sort_order,
            added_at=item.added_at,
            title=r.title if r else None,
            file_name=r.file_name if r else None,
            file_size=r.file_size if r else None,
            file_extension=r.file_extension if r else None,
            mime_type=r.mime_type if r else None,
            visibility=r.visibility if r else None,
            slug=r.slug if r else None,
        ))
    
    return CollectionDetailResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        emoji=collection.emoji,
        color=collection.color,
        sort_order=collection.sort_order,
        item_count=collection.item_count,
        total_size=collection.total_size,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        items=items,
    )


@router.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    data: CollectionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a collection's name, emoji, color, or description."""
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == current_user.id)
        .options(selectinload(Collection.items).selectinload(CollectionItem.resource))
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    
    if data.name is not None:
        collection.name = data.name.strip()
    if data.description is not None:
        collection.description = data.description.strip() if data.description else None
    if data.emoji is not None:
        collection.emoji = data.emoji
    if data.color is not None:
        collection.color = data.color
    
    await db.flush()
    await db.refresh(collection)
    
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        emoji=collection.emoji,
        color=collection.color,
        sort_order=collection.sort_order,
        item_count=collection.item_count,
        total_size=collection.total_size,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a collection (items are removed, resources are NOT deleted)."""
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == current_user.id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    
    await db.delete(collection)
    await db.flush()
    
    return {"message": "Collection deleted successfully"}


# ────────────────────────────────────────────────────────────────
# Collection Items
# ────────────────────────────────────────────────────────────────

@router.post("/collections/{collection_id}/items")
async def add_items_to_collection(
    collection_id: str,
    data: CollectionItemAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add resources to a collection. Resources must belong to the current user."""
    # Verify collection ownership
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == current_user.id)
        .options(selectinload(Collection.items))
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    
    # Get existing resource IDs in this collection
    existing_ids = {item.resource_id for item in collection.items}
    max_sort = max((item.sort_order for item in collection.items), default=-1)
    
    added = 0
    skipped = 0
    
    for resource_id in data.resource_ids:
        # Skip duplicates
        if resource_id in existing_ids:
            skipped += 1
            continue
        
        # Verify resource exists and belongs to user
        res_result = await db.execute(
            select(Resource).where(
                Resource.id == resource_id,
                Resource.uploader_id == current_user.id,
                Resource.is_deleted == False,
            )
        )
        resource = res_result.scalar_one_or_none()
        
        if not resource:
            skipped += 1
            continue
        
        max_sort += 1
        item = CollectionItem(
            collection_id=collection_id,
            resource_id=resource_id,
            sort_order=max_sort,
        )
        db.add(item)
        existing_ids.add(resource_id)
        added += 1
    
    await db.flush()
    
    return {"message": f"Added {added} file(s), skipped {skipped}", "added": added, "skipped": skipped}


@router.delete("/collections/{collection_id}/items/{resource_id}")
async def remove_item_from_collection(
    collection_id: str,
    resource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a resource from a collection."""
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.resource_id == resource_id,
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in collection")
    
    # Verify ownership via collection
    coll_result = await db.execute(
        select(Collection).where(Collection.id == collection_id, Collection.user_id == current_user.id)
    )
    if not coll_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your collection")
    
    await db.delete(item)
    await db.flush()
    
    return {"message": "Removed from collection"}


@router.put("/collections/{collection_id}/reorder")
async def reorder_collection_items(
    collection_id: str,
    data: CollectionReorder,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder items in a collection."""
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == current_user.id)
        .options(selectinload(Collection.items))
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    
    # Build lookup
    items_by_resource = {item.resource_id: item for item in collection.items}
    
    for i, resource_id in enumerate(data.resource_ids):
        if resource_id in items_by_resource:
            items_by_resource[resource_id].sort_order = i
    
    await db.flush()
    
    return {"message": "Reordered successfully"}


# ────────────────────────────────────────────────────────────────
# Recent uploads (for library quick-access section)
# ────────────────────────────────────────────────────────────────

@router.get("/recent")
async def get_recent_uploads(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's most recent uploads."""
    result = await db.execute(
        select(Resource)
        .where(Resource.uploader_id == current_user.id, Resource.is_deleted == False)
        .order_by(Resource.created_at.desc())
        .limit(min(limit, 50))
    )
    resources = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "slug": r.slug,
            "file_name": r.file_name,
            "file_size": r.file_size,
            "file_extension": r.file_extension,
            "visibility": r.visibility,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in resources
    ]


@router.get("/uncategorized-count")
async def get_uncategorized_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Count resources not in any collection."""
    # Total user resources
    total_result = await db.execute(
        select(func.count()).select_from(Resource).where(
            Resource.uploader_id == current_user.id,
            Resource.is_deleted == False,
        )
    )
    total = total_result.scalar()
    
    # Resources in at least one collection
    in_collection_result = await db.execute(
        select(func.count(func.distinct(CollectionItem.resource_id)))
        .select_from(CollectionItem)
        .join(Collection, CollectionItem.collection_id == Collection.id)
        .where(Collection.user_id == current_user.id)
    )
    in_collection = in_collection_result.scalar()
    
    return {"uncategorized": max(0, total - in_collection), "total": total}
