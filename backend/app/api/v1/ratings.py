"""
Ratings API Routes (SQLAlchemy)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.models.rating import Rating
from app.schemas.rating import RatingCreate, RatingResponse
from app.api.v1.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/resources/{resource_id}", response_model=RatingResponse)
async def create_or_update_rating(
    resource_id: str,
    data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a rating for a resource.

    One rating row per (user, resource). Stars and review compose:
    - A star value > 0 sets/updates the stars (and the aggregates).
    - A review (when provided) sets/updates the review text without
      discarding previously saved stars, so "4 stars + comment" stores both.
    """
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    existing_result = await db.execute(
        select(Rating).where(
            Rating.user_id == current_user.id,
            Rating.resource_id == resource_id,
        )
    )
    existing_rating = existing_result.scalar_one_or_none()

    if existing_rating:
        # Update the user's single rating row in place.
        old_value = existing_rating.value
        new_value = data.value if data.value > 0 else old_value
        if data.review is not None:
            existing_rating.review = data.review

        if new_value != old_value:
            if old_value == 0 and new_value > 0:
                # Comment-only row becomes a star rating.
                resource.rating_sum += new_value
                resource.rating_count += 1
            elif old_value > 0 and new_value == 0:
                resource.rating_sum = max(0, resource.rating_sum - old_value)
                resource.rating_count = max(0, resource.rating_count - 1)
            else:
                resource.rating_sum = resource.rating_sum - old_value + new_value
            existing_rating.value = new_value

        await db.flush()
        await db.refresh(existing_rating)
        return existing_rating

    # First rating from this user.
    rating = Rating(
        user_id=current_user.id,
        resource_id=resource.id,
        value=data.value,
        review=data.review,
    )
    db.add(rating)

    if data.value > 0:
        resource.rating_sum += data.value
        resource.rating_count += 1
    await db.flush()
    await db.refresh(rating)
    return rating


@router.get("/resources/{resource_id}")
async def get_resource_ratings(
    resource_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get ratings for a resource."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Count
    count_result = await db.execute(
        select(func.count()).select_from(Rating).where(Rating.resource_id == resource_id)
    )
    total = count_result.scalar()
    
    # Fetch ratings
    ratings_result = await db.execute(
        select(Rating)
        .where(Rating.resource_id == resource_id)
        .order_by(Rating.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    ratings = ratings_result.scalars().all()
    
    # Get user info
    user_ids = [r.user_id for r in ratings]
    user_map = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = users_result.scalars().all()
        user_map = {u.id: (u.display_name or u.email.split('@')[0]) for u in users}
    
    # Build response
    results = []
    for r in ratings:
        res = RatingResponse.model_validate(r, from_attributes=True)
        res.user_name = user_map.get(r.user_id, "Anonymous")
        results.append(res)
    
    pages = (total + size - 1) // size if total > 0 else 0
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "pages": pages,
        "average_rating": resource.average_rating,
        "rating_count": resource.rating_count,
    }


@router.delete("/resources/{resource_id}")
async def delete_rating(
    resource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete user's rating for a resource."""
    result = await db.execute(
        select(Rating).where(
            Rating.user_id == current_user.id,
            Rating.resource_id == resource_id,
        )
    )
    rating = result.scalar_one_or_none()
    
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")
    
    # Update resource aggregates
    res_result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = res_result.scalar_one_or_none()
    
    if resource:
        resource.rating_sum -= rating.value
        resource.rating_count = max(0, resource.rating_count - 1)
    
    await db.delete(rating)
    await db.flush()
    
    return {"message": "Rating deleted successfully"}
