"""
Search API Routes (SQLAlchemy) - Full-text search and filtering
"""
import time
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.resource import Resource
from app.models.department import Department
from app.schemas.search import SearchQuery, SearchResponse, FilterOptions, ResourceSummaryListResponse

import logging
logger = logging.getLogger(__name__)

router = APIRouter(redirect_slashes=False)


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input can't widen the match."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _department_id_subquery(name_or_code: str):
    return select(Department.id).where(
        or_(
            func.lower(Department.name) == name_or_code.strip().lower(),
            func.lower(Department.code) == name_or_code.strip().lower(),
        )
    )


@router.get("", response_model=SearchResponse)
async def search_resources(
    q: Optional[str] = Query(None, max_length=200),
    course_code: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[str] = None,
    branch: Optional[str] = None,
    program: Optional[str] = None,
    tags: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_ratings: Optional[int] = Query(None, ge=0),
    file_type: Optional[str] = None,
    sort_by: str = Query("relevance", pattern="^(relevance|downloads|rating|recent|views|top_rated)$"),
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
    
    # Text search → SQLite LIKE (wildcards escaped)
    if q:
        q_like = f"%{_escape_like(q)}%"
        filters.append(
            or_(
                Resource.title.ilike(q_like, escape="\\"),
                Resource.course_code.ilike(q_like, escape="\\"),
                Resource.description.ilike(q_like, escape="\\"),
                Resource.file_name.ilike(q_like, escape="\\"),
                Resource.semester.ilike(q_like, escape="\\"),
                Resource.tags_str.ilike(q_like, escape="\\"),
            )
        )
    
    # Field filters
    if course_code:
        filters.append(Resource.course_code == course_code.upper())
    if department:
        filters.append(Resource.department_id.in_(_department_id_subquery(department)))
    if semester:
        filters.append(Resource.semester == semester)
    if branch:
        filters.append(Resource.branch == branch)
    if program:
        filters.append(Resource.program == program)
    if file_type:
        filters.append(Resource.file_extension == file_type.lower())
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
        for tag in tag_list:
            filters.append(Resource.tags_str.ilike(f"%{_escape_like(tag)}%", escape="\\"))
    
    # Rating filters
    if min_rating and min_rating > 0:
        filters.append(Resource.rating_count > 0)
        # rating_sum / rating_count >= min_rating  ⇔  sum >= min * count
        filters.append(Resource.rating_sum >= min_rating * Resource.rating_count)
    if min_ratings and min_ratings > 0:
        # Per-item appearance floor for rating-based rows/items: an item
        # needs this many individual ratings to enter the list at all
        # (prevents a single 5-star rating from topping a "Top Rated" list).
        filters.append(Resource.rating_count >= min_ratings)
    
    combined = and_(*filters)
    
    # Count
    count_result = await db.execute(select(func.count()).select_from(Resource).where(combined))
    total = count_result.scalar()
    
    # Sort — every branch produces an ORDER BY clause list; `.order_by(*…)` applies it.
    if sort_by == "downloads":
        order = [Resource.downloads.desc(), Resource.created_at.desc()]
    elif sort_by == "rating":
        # Average rating, not raw sum (a 2×5-star must beat a 2×3+2-star)
        order = [
            (func.cast(Resource.rating_sum, Float) / func.max(Resource.rating_count, 1)).desc(),
            Resource.created_at.desc(),
        ]
    elif sort_by == "top_rated":
        # IMDb-family Bayesian average: WR = (sum + m·C) / (count + m).
        # Shrinks low-vote items toward the global mean C, so one lonely
        # 5-star can't top the list. m=5 pseudocount for a catalog this size
        # (IMDb's m scales with its own traffic — re-tune as ratings grow).
        stats = await db.execute(
            select(func.sum(Resource.rating_sum), func.sum(Resource.rating_count)).where(
                Resource.is_deleted == False,  # noqa: E712
                Resource.moderation_status == "approved",
            )
        )
        total_sum, total_count = stats.one()
        global_mean = (total_sum / total_count) if (total_count or 0) > 0 else 0.0
        m = 5.0
        order = [
            (
                (func.cast(Resource.rating_sum, Float) + m * global_mean)
                / (Resource.rating_count + m)
            ).desc(),
            Resource.rating_count.desc(),  # stronger evidence wins exact ties
            Resource.created_at.desc(),
        ]
    elif sort_by == "views":
        # "Most read": cumulative visitor-deduped views, most-recent tiebreak.
        # (Time decay would make this a "Trending" row — that's a different label.)
        order = [Resource.views.desc(), Resource.created_at.desc()]
    elif sort_by == "recent":
        order = [Resource.created_at.desc()]
    else:  # relevance
        order = [Resource.downloads.desc()]
    
    result = await db.execute(
        select(Resource)
        .where(combined)
        .order_by(*order)
        .offset((page - 1) * size)
        .limit(size)
    )
    resources = result.scalars().all()
    
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
        # Only options that exist on live public content — a filter that
        # returns zero results is a dead dropdown.
        base_filter = and_(
            Resource.is_deleted == False,
            Resource.visibility == "public",
            Resource.moderation_status == "approved",
        )

        async def get_distinct(column, extra_filter=None):
            f = and_(base_filter, column.isnot(None), column != "")
            result = await db.execute(select(column).distinct().where(f).order_by(column))
            return [r[0] for r in result.all()]

        courses = await get_distinct(Resource.course_code)
        semesters = await get_distinct(Resource.semester)
        branches = await get_distinct(Resource.branch)
        programs = await get_distinct(Resource.program)
        file_types = await get_distinct(Resource.file_extension)

        # Departments come from the Departments table (the upload UI's
        # source of truth), not from resource rows.
        dept_result = await db.execute(
            select(Department.name)
            .where(Department.is_active == True)  # noqa: E712
            .order_by(Department.display_order, Department.name)
        )
        departments = [r[0] for r in dept_result.all()]

        # Static tags
        tags_list = ["notes", "exam", "syllabus", "assignments", "lecture", "tutorial", "solved"]

        return FilterOptions(
            courses=courses,
            departments=departments,
            semesters=semesters,
            branches=branches,
            programs=programs,
            tags=tags_list,
            file_types=file_types,
        )
    except Exception:
        logger.exception("Failed to load filter options")
        return FilterOptions(
            courses=[], departments=[], semesters=[], branches=[], programs=[], tags=[], file_types=[]
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
