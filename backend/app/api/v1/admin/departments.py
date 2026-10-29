"""
Admin API - Department Management (SQLAlchemy)
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
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentListResponse
from app.api.v1.deps import require_admin
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=DepartmentListResponse)
async def list_departments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all departments (admin only)."""
    filters = []
    if is_active is not None:
        filters.append(Department.is_active == is_active)
    
    combined = and_(*filters) if filters else True
    
    count_result = await db.execute(select(func.count()).select_from(Department).where(combined))
    total = count_result.scalar()
    
    result = await db.execute(
        select(Department).where(combined)
        .order_by(Department.display_order, Department.name)
        .offset((page - 1) * page_size).limit(page_size)
    )
    departments = result.scalars().all()

    # Batch course counts for the page (single GROUP BY query)
    course_counts: dict = {}
    if departments:
        counts_result = await db.execute(
            select(Course.department_id, func.count())
            .where(Course.department_id.in_([d.id for d in departments]))
            .group_by(Course.department_id)
        )
        course_counts = {dept_id: count for dept_id, count in counts_result.all()}

    return DepartmentListResponse(
        results=[DepartmentResponse(id=str(d.id), name=d.name, code=d.code,
                description=d.description, is_active=d.is_active, display_order=d.display_order,
                course_count=course_counts.get(d.id, 0),
                created_at=d.created_at, updated_at=d.updated_at)
                for d in departments],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new department."""
    existing = await db.execute(select(Department).where(Department.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Department with code '{data.code}' already exists")
    
    department = Department(**data.model_dump())
    db.add(department)
    await db.flush()
    await db.refresh(department)
    
    try:
        audit = AuditLog(action="create_department", actor_id=current_user.id, target_type="department",
                        target_id=str(department.id), details_json=json.dumps({"name": department.name, "code": department.code}))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    
    return DepartmentResponse(id=str(department.id), name=department.name, code=department.code,
                              description=department.description, is_active=department.is_active,
                              display_order=department.display_order,
                              created_at=department.created_at, updated_at=department.updated_at)


@router.get("/{id}", response_model=DepartmentResponse)
async def get_department(id: str, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return DepartmentResponse(id=str(department.id), name=department.name, code=department.code,
                              description=department.description, is_active=department.is_active,
                              display_order=department.display_order,
                              created_at=department.created_at, updated_at=department.updated_at)


@router.put("/{id}", response_model=DepartmentResponse)
async def update_department(
    id: str, data: DepartmentUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Department).where(Department.id == id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    if data.code and data.code != department.code:
        dup = await db.execute(select(Department).where(Department.code == data.code))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Department with code '{data.code}' already exists")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(department, key, value)
    
    audit = AuditLog(action="update_department", actor_id=current_user.id, target_type="department",
                    target_id=str(department.id), details_json=json.dumps(update_data))
    db.add(audit)
    await db.flush()
    
    return DepartmentResponse(id=str(department.id), name=department.name, code=department.code,
                              description=department.description, is_active=department.is_active,
                              display_order=department.display_order,
                              created_at=department.created_at, updated_at=department.updated_at)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(id: str, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    # H2: never hard-cascade courses/resources. Count children first; any
    # course (even empty) blocks deletion so nothing is silently destroyed.
    course_count = (
        await db.execute(
            select(func.count()).select_from(Course).where(Course.department_id == id)
        )
    ).scalar()

    if course_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Department '{department.code}' has {course_count} course(s); "
                "move or delete its courses before deleting the department"
            ),
        )

    await db.delete(department)

    try:
        audit = AuditLog(action="delete_department", actor_id=current_user.id, target_type="department",
                        target_id=id, details_json=json.dumps({
                            "name": department.name, "code": department.code,
                            "course_count": course_count,
                        }))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")

    await db.flush()


@router.patch("/{id}/toggle", response_model=DepartmentResponse)
async def toggle_department(id: str, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    department.is_active = not department.is_active
    
    try:
        audit = AuditLog(action="toggle_department", actor_id=current_user.id, target_type="department",
                        target_id=id, details_json=json.dumps({"is_active": department.is_active}))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    
    await db.flush()
    return DepartmentResponse(id=str(department.id), name=department.name, code=department.code,
                              description=department.description, is_active=department.is_active,
                              display_order=department.display_order,
                              created_at=department.created_at, updated_at=department.updated_at)
