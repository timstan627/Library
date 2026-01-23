"""
Ratings API Routes
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.models.user import User
from app.models.resource import Resource
from app.models.rating import Rating
from app.schemas.rating import RatingCreate, RatingResponse
from app.api.v1.deps import get_current_active_user

router = APIRouter()


@router.post("/resources/{resource_id}", response_model=RatingResponse)
async def create_or_update_rating(
    resource_id: uuid.UUID,
    data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Create or update a rating for a resource."""
    resource = await Resource.find_one(Resource.id == resource_id, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Logic for handling Ratings vs Comments
    # If value > 0:Treat as a STAR RATING (Update existing star rating or create new)
    # If value == 0: Treat as a COMMENT (Always create new, multiple allowed)
    
    if data.value > 0:
        # STAR RATING: Check if user already rated with stars
        existing_rating = await Rating.find_one(
            Rating.user.id == current_user.id,
            Rating.resource.id == resource_id,
            Rating.value > 0
        )
        
        if existing_rating:
            # Update existing star rating
            old_value = existing_rating.value
            existing_rating.value = data.value
            if data.review is not None:
                existing_rating.review = data.review
            
            # Update resource aggregates
            resource.rating_sum = resource.rating_sum - old_value + data.value
            
            await existing_rating.save()
            await resource.save()
            return existing_rating
            
        else:
            # Create NEW star rating
            rating = Rating(
                user=current_user,
                resource=resource,
                value=data.value,
                review=data.review,
            )
            await rating.create()
            
            # Update resource aggregates
            resource.rating_sum += data.value
            resource.rating_count += 1
            await resource.save()
            return rating

    else:
        # COMMENT ONLY (value == 0)
        # Always create new
        rating = Rating(
            user=current_user,
            resource=resource,
            value=0,
            review=data.review or "", # Ensure review text exists
        )
        await rating.create()
        return rating


@router.get("/resources/{resource_id}")
async def get_resource_ratings(
    resource_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Get ratings for a resource."""
    resource = await Resource.find_one(Resource.id == resource_id, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Get ratings
    query = Rating.find(Rating.resource.id == resource_id).sort("-created_at")
    
    total = await query.count()
    ratings = await query.skip((page - 1) * size).limit(size).to_list()
    
    # Safely fetch user details
    from beanie.operators import In
    
    user_ids = []
    for r in ratings:
        # Handle Beanie Link id access
        u_id = r.user.ref.id if hasattr(r.user, "ref") else r.user.id
        user_ids.append(u_id)
    
    # Fetch users in one query
    try:
        users = await User.find(In(User.id, user_ids)).to_list()
        user_map = {u.id: (u.display_name or u.email.split('@')[0]) for u in users}
    except Exception as e:
        print(f"Error fetching users for ratings: {e}")
        user_map = {}
    
    # Convert to response objects with names
    results = []
    for r in ratings:
        # Convert Document to Schema
        res = RatingResponse.model_validate(r, from_attributes=True)
        # Inject name
        u_id = r.user.ref.id if hasattr(r.user, "ref") else r.user.id
        res.user_name = user_map.get(u_id, "Anonymous")
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
    resource_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
):
    """Delete user's rating for a resource."""
    # Find rating
    rating = await Rating.find_one(
        Rating.user.id == current_user.id,
        Rating.resource.id == resource_id
    )
    
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found",
        )
    
    # Update resource aggregates
    # Get resource (or fetch from Link if rating loaded it? Beanie links are lazy by default)
    # We'll fetch from DB to be safe/update it.
    resource = await Resource.find_one(Resource.id == resource_id)
    
    if resource:
        resource.rating_sum -= rating.value
        resource.rating_count = max(0, resource.rating_count - 1)
        await resource.save()
    
    # Delete rating
    await rating.delete()
    
    return {"message": "Rating deleted successfully"}
