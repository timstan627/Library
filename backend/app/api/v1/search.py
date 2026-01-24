"""
Search API Routes - Full-text search and filtering
"""
import time
from typing import Optional, List
from fastapi import APIRouter, Depends, Query

from app.core.database import init_db
from app.models.resource import Resource
from app.schemas.search import SearchQuery, SearchResponse, FilterOptions
from app.services.cache import cache_service

import logging

logger = logging.getLogger(__name__)

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=SearchResponse)
async def search_resources(
    q: Optional[str] = Query(None, max_length=200),
    course_code: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[str] = None,
    branch: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    file_type: Optional[str] = None,
    sort_by: str = Query("relevance", pattern="^(relevance|downloads|rating|recent)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Search resources with full-text search and filters.
    """
    start_time = time.time()
    
    # Base filters
    filters = [
        Resource.is_deleted == False,
        Resource.visibility == "public",
        Resource.moderation_status == "approved"
    ]
    
    # Smart Search Logic
    if q:
        import re
        q_regex = re.escape(q)
        
        logger.info(f"Search query received: '{q}'")

        # Combine Text Search (Relevance) with Regex Partial Match (Intuitive)
        # Combine Text Search (Relevance) with Regex Partial Match (Intuitive)
        or_conditions = [
            {"title": {"$regex": q_regex, "$options": "i"}},
            {"course_code": {"$regex": q_regex, "$options": "i"}},
            {"description": {"$regex": q_regex, "$options": "i"}},
            {"tags": {"$in": [q.lower()]}}
        ]
        
        # Only use Text Search for longer queries to avoid "stop words only" errors or poor performance
        if len(q) > 2:
            or_conditions.insert(0, {"$text": {"$search": q}})
        
        search_condition = {"$or": or_conditions}
        filters.append(search_condition)
        logger.info(f"Search filters: {filters}")
    
    # Field filters
    if course_code:
        filters.append(Resource.course_code == course_code.upper())
    
    if department:
        filters.append(Resource.department == department)
        
    if semester:
        filters.append(Resource.semester == semester)
        
    if branch:
        filters.append(Resource.branch == branch)
        
    if file_type:
        filters.append(Resource.file_extension == file_type.lower())
        
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
        if tag_list:
            filters.append(Resource.tags == {"$in": tag_list})

    # Rating filter requires aggregation or manual filter if computed
    # Average rating is a property, not stored. But we have rating_sum and rating_count.
    if min_rating:
        # (rating_sum / rating_count) >= min_rating
        # rating_sum >= min_rating * rating_count
        # This is hard to do with standard find() without $expr
        filters.append({
            "$expr": {
                "$gte": [
                    {"$divide": ["$rating_sum", {"$max": ["$rating_count", 1]}]}, 
                    min_rating
                ]
            }
        })

    query = Resource.find(*filters)
    
    # Sort
    if sort_by == "downloads":
        query = query.sort("-downloads")
    elif sort_by == "rating":
        # Sort by avg rating is tricky without stored field. 
        # For now, sort by rating_sum as proxy or rating_count
        query = query.sort("-rating_sum", "-rating_count")
    elif sort_by == "recent":
        query = query.sort("-created_at")
    else: # relevance
        # Fallback to downloads for now to prevent 500 error with textScore
        query = query.sort("-downloads")
            
    total = await query.count()
    logger.info(f"Search query '{q or ''}' returned {total} results")
    resources = await query.skip((page - 1) * size).limit(size).to_list()
    
    pages = (total + size - 1) // size if total > 0 else 0
    took_ms = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        results=resources,
        total=total,
        page=page,
        pages=pages,
        took_ms=took_ms,
        query=q,
    )


@router.get("/filters", response_model=FilterOptions)
async def get_filter_options():
    """Get available filter options for the search UI."""
    # Aggregations to get distinct values
    
    courses = await Resource.get_motor_collection().distinct(
        "course_code", 
        {"is_deleted": False, "visibility": "public"}
    )
    courses.sort()
    
    departments = await Resource.get_motor_collection().distinct(
        "department", 
        {"is_deleted": False, "visibility": "public", "department": {"$ne": None}}
    )
    departments.sort()
    
    semesters = await Resource.get_motor_collection().distinct(
        "semester", 
        {"is_deleted": False, "visibility": "public", "semester": {"$ne": None}}
    )
    semesters.sort()
    
    branches = await Resource.get_motor_collection().distinct(
        "branch", 
        {"is_deleted": False, "visibility": "public", "branch": {"$ne": None}}
    )
    branches.sort()
    
    file_types = await Resource.get_motor_collection().distinct(
        "file_extension", 
        {"is_deleted": False, "visibility": "public"}
    )
    file_types.sort()
    
    # Tags would need unwinding
    tags = ["notes", "exam", "syllabus", "assignments", "lecture", "tutorial", "solved"]
    
    return FilterOptions(
        courses=courses,
        departments=departments,
        semesters=semesters,
        branches=branches,
        tags=tags,
        file_types=file_types,
    )


@router.get("/popular")
async def get_popular_resources(
    limit: int = Query(10, ge=1, le=50),
):
    """Get most downloaded resources."""
    resources = await Resource.find(
        Resource.is_deleted == False,
        Resource.visibility == "public",
        Resource.moderation_status == "approved"
    ).sort("-downloads").limit(limit).to_list()
    
    return {"results": resources}


@router.get("/recent")
async def get_recent_resources(
    limit: int = Query(10, ge=1, le=50),
):
    """Get recently uploaded resources."""
    resources = await Resource.find(
        Resource.is_deleted == False,
        Resource.visibility == "public",
        Resource.moderation_status == "approved"
    ).sort("-created_at").limit(limit).to_list()
    
    return {"results": resources}
