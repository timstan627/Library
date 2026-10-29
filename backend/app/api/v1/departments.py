"""
Public API - Departments (SQLAlchemy)
"""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.department import Department
from app.schemas.department import DepartmentResponse

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentResponse])
async def list_active_departments(
    db: AsyncSession = Depends(get_db),
):
    """List all active departments (public endpoint for forms)."""
    result = await db.execute(
        select(Department)
        .where(Department.is_active == True)
        .order_by(Department.display_order, Department.name)
    )
    departments = result.scalars().all()
    
    return [
        DepartmentResponse(id=str(dept.id), name=dept.name, code=dept.code,
                          description=dept.description, is_active=dept.is_active,
                          display_order=dept.display_order,
                          created_at=dept.created_at, updated_at=dept.updated_at)
        for dept in departments
    ]


@router.get("/{id}", response_model=DepartmentResponse)
async def get_department(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific department by ID."""
    result = await db.execute(
        select(Department).where(Department.id == id, Department.is_active == True)  # noqa: E712
    )
    department = result.scalar_one_or_none()

    if not department:
        # Deactivated departments are hidden from the public surface (M17),
        # matching the is_active filter applied by the list endpoint.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    return DepartmentResponse(id=str(department.id), name=department.name, code=department.code,
                              description=department.description, is_active=department.is_active,
                              display_order=department.display_order,
                              created_at=department.created_at, updated_at=department.updated_at)
