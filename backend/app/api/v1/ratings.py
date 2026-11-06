"""
Ratings API Routes (SQLAlchemy)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.models.rating import Rating
from app.schemas.rating import RatingCreate, RatingResponse
from app.api.v1.deps import get_current_active_user, get_current_user, ensure_resource_viewable

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

    One rating row per (user, resource) — enforced by a unique index, with
    concurrent double-submits surfacing as IntegrityError → 409.

    Stars and review compose:
    - A star value > 0 sets/updates the stars (and the aggregates).
    - A review (when provided) sets/updates the review text without
      discarding previously saved stars, so "4 stars + comment" stores both.

    Aggregate changes are applied as atomic UPDATE statements (x = x + delta),
    never read-modify-write: concurrent ratings cannot lose increments.
    """
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()

    if not resource or resource.moderation_status != "approved":
        # Unapproved content is unratable (and its existence stays hidden)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    # Visibility gate: private resources are owner/moderator-only — do not
    # let others rate content they cannot view.
    ensure_resource_viewable(resource, current_user)

    if resource.uploader_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot rate your own resource",
        )

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
                await db.execute(
                    sql_update(Resource)
                    .where(Resource.id == resource_id)
                    .values(
                        rating_sum=Resource.rating_sum + new_value,
                        rating_count=Resource.rating_count + 1,
                    )
                )
            elif old_value > 0 and new_value == 0:
                await db.execute(
                    sql_update(Resource)
                    .where(Resource.id == resource_id)
                    .values(
                        rating_sum=func.max(0, Resource.rating_sum - old_value),
                        rating_count=func.max(0, Resource.rating_count - 1),
                    )
                )
            else:
                await db.execute(
                    sql_update(Resource)
                    .where(Resource.id == resource_id)
                    .values(rating_sum=Resource.rating_sum - old_value + new_value)
                )
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
        await db.execute(
            sql_update(Resource)
            .where(Resource.id == resource_id)
            .values(
                rating_sum=Resource.rating_sum + data.value,
                rating_count=Resource.rating_count + 1,
            )
        )
    try:
        await db.flush()
    except IntegrityError:
        # Lost a race against a concurrent first-rating from the same user.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this resource",
        )
    await db.refresh(rating)
    return rating


@router.get("/resources/{resource_id}")
async def get_resource_ratings(
    resource_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ratings for a resource."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Same moderation + visibility gate as the resource endpoints: pending
    # resources stay hidden (404) and private resources owner/moderator-only
    # (403) — ratings must not leak what the resource itself withholds.
    ensure_resource_viewable(resource, current_user)
    
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
        user_map = {u.id: (u.display_name or "Student") for u in users}
    
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
        "page_size": size,
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

    if rating.value > 0:
        # Review-only rows (value 0) never contributed to the aggregates.
        await db.execute(
            sql_update(Resource)
            .where(Resource.id == resource_id)
            .values(
                rating_sum=func.max(0, Resource.rating_sum - rating.value),
                rating_count=func.max(0, Resource.rating_count - 1),
            )
        )

    await db.delete(rating)
    await db.flush()

    return {"message": "Rating deleted successfully"}
