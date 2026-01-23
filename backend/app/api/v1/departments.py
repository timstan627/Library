"""
Public API - Departments (for dropdowns in upload forms)
"""
from typing import List
from fastapi import APIRouter
from beanie import PydanticObjectId

from app.models.department import Department
from app.schemas.department import DepartmentResponse

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentResponse])
async def list_active_departments():
    """List all active departments (public endpoint for forms)."""
    departments = (
        await Department.find(Department.is_active == True)
        .sort("+display_order", "+name")
        .to_list()
    )
    
    return [
        DepartmentResponse(**dept.model_dump(exclude={"id"}), id=str(dept.id))
        for dept in departments
    ]


@router.get("/{id}", response_model=DepartmentResponse)
async def get_department(id: str):
    """Get a specific department by ID."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid department ID"
        )
    
    department = await Department.get(obj_id)
    if not department:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    return DepartmentResponse(**department.model_dump(exclude={"id"}), id=str(department.id))
