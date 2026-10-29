"""
Search API Routes (SQLAlchemy) - Full-text search and filtering
"""
import time
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.resource import Resource
from app.schemas.search import SearchQuery, SearchResponse, FilterOptions, ResourceSummaryListResponse

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
    tags: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    file_type: Optional[str] = None,
    sort_by: str = Query("relevance", pattern="^(relevance|downloads|rating|recent)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search resources with full-text search and filters."""
    start_time = time.time()
    
    # Base filters
    filters = [
        Resource.is_deleted == False,
        Resource.visibility == "public",
        Resource.moderation_status == "approved",
    ]
    
    # Text search → SQLite LIKE
    if q:
        q_like = f"%{q}%"
        filters.append(
            or_(
                Resource.title.ilike(q_like),
                Resource.course_code.ilike(q_like),
                Resource.description.ilike(q_like),
                Resource.file_name.ilike(q_like),
                Resource.semester.ilike(q_like),
                Resource.tags_str.ilike(q_like),
            )
        )
    
    # Field filters
    if course_code:
        filters.append(Resource.course_code == course_code.upper())
    if semester:
        filters.append(Resource.semester == semester)
    if branch:
        filters.append(Resource.branch == branch)
    if file_type:
        filters.append(Resource.file_extension == file_type.lower())
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
        for tag in tag_list:
            filters.append(Resource.tags_str.ilike(f"%{tag}%"))
    
    # Rating filter
    if min_rating and min_rating > 0:
        # rating_sum / max(rating_count, 1) >= min_rating
        filters.append(Resource.rating_count > 0)
        # Use SQL expression: rating_sum >= min_rating * rating_count
        filters.append(Resource.rating_sum >= min_rating * Resource.rating_count)
    
    try:
        combined = and_(*filters)
        
        # Count
        count_result = await db.execute(select(func.count()).select_from(Resource).where(combined))
        total = count_result.scalar()
        
        # Sort
        if sort_by == "downloads":
            order = Resource.downloads.desc()
        elif sort_by == "rating":
            order = Resource.rating_sum.desc()
        elif sort_by == "recent":
            order = Resource.created_at.desc()
        else:  # relevance
            order = Resource.downloads.desc()
        
        result = await db.execute(
            select(Resource)
            .where(combined)
            .order_by(order)
            .offset((page - 1) * size)
            .limit(size)
        )
        resources = result.scalars().all()
        
    except Exception as e:
        logger.error(f"Search query failed: {e}")
        total = 0
        resources = []
    
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
async def get_filter_options(
    db: AsyncSession = Depends(get_db),
):
    """Get available filter options for the search UI."""
    try:
        base_filter = and_(Resource.is_deleted == False, Resource.visibility == "public")
        
        async def get_distinct(column, extra_filter=None):
            f = and_(base_filter, column.isnot(None), column != "")
            result = await db.execute(select(column).distinct().where(f).order_by(column))
            return [r[0] for r in result.all()]
        
        courses = await get_distinct(Resource.course_code)
        semesters = await get_distinct(Resource.semester)
        branches = await get_distinct(Resource.branch)
        file_types = await get_distinct(Resource.file_extension)
        
        # Static tags
        tags_list = ["notes", "exam", "syllabus", "assignments", "lecture", "tutorial", "solved"]
        
        return FilterOptions(
            courses=courses,
            departments=[],
            semesters=semesters,
            branches=branches,
            tags=tags_list,
            file_types=file_types,
        )
    except Exception as e:
        logger.error(f"Failed to load filters: {e}")
        return FilterOptions(
            courses=[], departments=[], semesters=[], branches=[], tags=[], file_types=[]
        )


@router.get("/popular", response_model=ResourceSummaryListResponse)
async def get_popular_resources(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get most downloaded resources (safe summary fields only)."""
    result = await db.execute(
        select(Resource)
        .where(Resource.is_deleted == False, Resource.visibility == "public", Resource.moderation_status == "approved")
        .order_by(Resource.downloads.desc())
        .limit(limit)
    )
    resources = result.scalars().all()
    return {"results": resources}


@router.get("/recent", response_model=ResourceSummaryListResponse)
async def get_recent_resources(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get recently uploaded resources (safe summary fields only)."""
    result = await db.execute(
        select(Resource)
        .where(Resource.is_deleted == False, Resource.visibility == "public", Resource.moderation_status == "approved")
        .order_by(Resource.created_at.desc())
        .limit(limit)
    )
    resources = result.scalars().all()
    return {"results": resources}
