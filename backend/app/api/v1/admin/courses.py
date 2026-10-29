"""
Admin API - Course Management (SQLAlchemy)
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.department import Department
from app.models.course import Course
from app.models.resource import Resource
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseListResponse
from app.api.v1.deps import require_admin
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=CourseListResponse)
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    department_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all courses (admin only)."""
    filters = []
    if department_id:
        filters.append(Course.department_id == department_id)
    if is_active is not None:
        filters.append(Course.is_active == is_active)
    
    combined = and_(*filters) if filters else True
    
    count_result = await db.execute(select(func.count()).select_from(Course).where(combined))
    total = count_result.scalar()
    
    result = await db.execute(
        select(Course).where(combined).order_by(Course.code)
        .offset((page - 1) * page_size).limit(page_size)
    )
    courses = result.scalars().all()
    
    # Batch fetch departments
    dept_ids = {c.department_id for c in courses if c.department_id}
    dept_map = {}
    if dept_ids:
        dept_result = await db.execute(select(Department).where(Department.id.in_(dept_ids)))
        dept_map = {d.id: d for d in dept_result.scalars().all()}
    
    results = []
    for course in courses:
        dept = dept_map.get(course.department_id)
        results.append(CourseResponse(
            id=str(course.id), name=course.name, code=course.code,
            description=course.description, semester=course.semester,
            credits=course.credits, is_active=course.is_active,
            department_id=course.department_id,
            department_name=dept.name if dept else None,
            created_at=course.created_at, updated_at=course.updated_at,
        ))
    
    return CourseListResponse(results=results, total=total, page=page, page_size=page_size)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new course."""
    dept_result = await db.execute(select(Department).where(Department.id == data.department_id))
    department = dept_result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    existing = await db.execute(select(Course).where(Course.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Course with code '{data.code}' already exists")
    
    course = Course(
        department_id=data.department_id,
        name=data.name, code=data.code, description=data.description,
        semester=data.semester, credits=data.credits,
        is_active=data.is_active if hasattr(data, 'is_active') else True,
    )
    db.add(course)

    await db.flush()
    await db.refresh(course)

    # Audit after flush so target_id is the real course id (M9).
    try:
        audit = AuditLog(action="create_course", actor_id=current_user.id, target_type="course",
                        target_id=str(course.id), details_json=json.dumps({"name": course.name, "code": course.code}))
        db.add(audit)
        await db.flush()
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    
    return CourseResponse(
        id=str(course.id), name=course.name, code=course.code,
        description=course.description, semester=course.semester,
        credits=course.credits, is_active=course.is_active,
        department_id=course.department_id, department_name=department.name,
        created_at=course.created_at, updated_at=course.updated_at,
    )


@router.put("/{id}", response_model=CourseResponse)
async def update_course(
    id: str, data: CourseUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a course."""
    result = await db.execute(select(Course).where(Course.id == id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    if data.department_id:
        dept_result = await db.execute(select(Department).where(Department.id == data.department_id))
        if not dept_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        course.department_id = data.department_id
    
    if data.code and data.code != course.code:
        existing = await db.execute(select(Course).where(Course.code == data.code))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Course with code '{data.code}' already exists")
    
    update_data = data.model_dump(exclude_unset=True, exclude={"department_id"})
    for key, value in update_data.items():
        setattr(course, key, value)
    
    try:
        audit = AuditLog(action="update_course", actor_id=current_user.id, target_type="course",
                        target_id=str(course.id), details_json=json.dumps(update_data))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    
    await db.flush()
    
    # Get department name
    dept_name = None
    if course.department_id:
        dept_result = await db.execute(select(Department).where(Department.id == course.department_id))
        dept = dept_result.scalar_one_or_none()
        if dept:
            dept_name = dept.name
    
    return CourseResponse(
        id=str(course.id), name=course.name, code=course.code,
        description=course.description, semester=course.semester,
        credits=course.credits, is_active=course.is_active,
        department_id=course.department_id, department_name=dept_name,
        created_at=course.created_at, updated_at=course.updated_at,
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a course."""
    result = await db.execute(select(Course).where(Course.id == id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # H2: never hard-cascade resources. Resources keep an FK reference to the
    # course row, so any child row (soft-deleted included) blocks deletion.
    resource_count = (
        await db.execute(
            select(func.count()).select_from(Resource).where(Resource.course_id == id)
        )
    ).scalar()

    if resource_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Course '{course.code}' has {resource_count} resource(s); "
                "deactivate the course or reassign its resources before deleting"
            ),
        )

    await db.delete(course)

    try:
        audit = AuditLog(action="delete_course", actor_id=current_user.id, target_type="course",
                        target_id=id, details_json=json.dumps({
                            "name": course.name, "code": course.code,
                            "resource_count": resource_count,
                        }))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")

    await db.flush()
