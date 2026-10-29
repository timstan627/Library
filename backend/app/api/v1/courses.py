"""
Public API - Courses (SQLAlchemy)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.course import Course
from app.models.department import Department

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("")
async def list_active_courses(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    db: AsyncSession = Depends(get_db),
):
    """List all active courses, optionally filtered by department."""
    try:
        stmt = select(Course).where(Course.is_active == True)
        
        if department_id:
            stmt = stmt.where(Course.department_id == department_id)
        
        stmt = stmt.order_by(Course.code)
        result = await db.execute(stmt)
        courses = result.scalars().all()
        
        # Fetch departments
        dept_ids = {c.department_id for c in courses if c.department_id}
        dept_map = {}
        if dept_ids:
            dept_result = await db.execute(select(Department).where(Department.id.in_(dept_ids)))
            dept_map = {d.id: d.name for d in dept_result.scalars().all()}
        
        results = []
        for course in courses:
            results.append({
                "id": str(course.id),
                "name": course.name,
                "code": course.code,
                "description": course.description,
                "semester": course.semester,
                "credits": course.credits,
                "department_id": course.department_id,
                "department_name": dept_map.get(course.department_id),
                "is_active": course.is_active,
            })
        
        return results
    except HTTPException:
        raise
    except Exception:
        # H3: never leak internal error text to public callers.
        logger.exception("Courses endpoint error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{id}")
async def get_course(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific course by ID."""
    result = await db.execute(
        select(Course).where(Course.id == id, Course.is_active == True)  # noqa: E712
    )
    course = result.scalar_one_or_none()

    if not course:
        # Deactivated courses are hidden from the public surface (M17),
        # matching the is_active filter applied by the list endpoint.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    dept_name = None
    if course.department_id:
        dept_result = await db.execute(select(Department).where(Department.id == course.department_id))
        dept = dept_result.scalar_one_or_none()
        if dept:
            dept_name = dept.name
    
    return {
        "id": str(course.id),
        "name": course.name,
        "code": course.code,
        "description": course.description,
        "semester": course.semester,
        "credits": course.credits,
        "department_id": course.department_id,
        "department_name": dept_name,
        "is_active": course.is_active,
    }
