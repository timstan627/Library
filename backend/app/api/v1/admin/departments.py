"""
Admin API - Department Management
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from beanie import PydanticObjectId

from app.models.user import User
from app.models.department import Department
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentListResponse
)
from app.api.v1.deps import get_current_user, require_admin
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin/departments", tags=["Admin - Departments"])


@router.get("", response_model=DepartmentListResponse)
async def list_departments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    current_user: User = Depends(require_admin),
):
    """List all departments (admin only)."""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    
    # Get total count
    total = await Department.find(query).count()
    
    # Get paginated results
    departments = (
        await Department.find(query)
        .sort("+display_order", "+name")
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list()
    )
    
    return DepartmentListResponse(
        results=[DepartmentResponse(**dept.model_dump(exclude={"id"}), id=str(dept.id)) for dept in departments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(require_admin),
):
    """Create a new department (admin only)."""
    # Check for duplicate code
    existing = await Department.find_one(Department.code == data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with code '{data.code}' already exists"
        )
    
    # Create department
    department = Department(**data.model_dump())
    await department.create()
    
    # Audit log
    try:
        audit = AuditLog(
            action="create_department",
            actor=current_user,
            target_type="department",
            target_id=str(department.id),
            details={"name": department.name, "code": department.code}
        )
        await audit.create()
    except Exception as e:
        # Don't block creation if audit fails
        import traceback
        traceback.print_exc()
        print(f"AUDIT LOG ERROR: {e}")
    
    return DepartmentResponse(**department.model_dump(exclude={"id"}), id=str(department.id))


@router.get("/{id}", response_model=DepartmentResponse)
async def get_department(
    id: str,
    current_user: User = Depends(require_admin),
):
    """Get a specific department by ID (admin only)."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid department ID"
        )
    
    department = await Department.get(obj_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    return DepartmentResponse(**department.model_dump(exclude={"id"}), id=str(department.id))


@router.put("/{id}", response_model=DepartmentResponse)
async def update_department(
    id: str,
    data: DepartmentUpdate,
    current_user: User = Depends(require_admin),
):
    """Update a department (admin only)."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")
    
    department = await Department.get(obj_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    # Check for duplicate code if changing
    if data.code and data.code != department.code:
        existing = await Department.find_one(Department.code == data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with code '{data.code}' already exists"
            )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(department, key, value)
    
    await department.save()
    
    # Audit log
    audit = AuditLog(
        action="update_department",
        actor=current_user,
        target_type="department",
        target_id=str(department.id),
        details=update_data
    )
    await audit.create()
    
    return DepartmentResponse(**department.model_dump(exclude={"id"}), id=str(department.id))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    id: str,
    current_user: User = Depends(require_admin),
):
    """Delete a department (admin only)."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")
    
    department = await Department.get(obj_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    # Cascade delete: Delete all courses and their resources
    from app.models.course import Course
    from app.models.resource import Resource
    
    # Find and delete all courses in this department
    courses = await Course.find(Course.department.id == obj_id).to_list()
    for course in courses:
        # Delete resources for this course
        await Resource.find(Resource.course_id.id == course.id).delete()
        # Delete the course
        await course.delete()
    
    await department.delete()
    
    # Audit log
    # Audit log
    try:
        audit = AuditLog(
            action="delete_department",
            actor=current_user,
            target_type="department",
            target_id=id,
            details={"name": department.name, "code": department.code}
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")


@router.patch("/{id}/toggle", response_model=DepartmentResponse)
async def toggle_department(
    id: str,
    current_user: User = Depends(require_admin),
):
    """Toggle department active status (admin only)."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")
    
    department= await Department.get(obj_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    department.is_active = not department.is_active
    await department.save()
    
    # Audit log
    # Audit log
    try:
        audit = AuditLog(
            action="toggle_department",
            actor=current_user,
            target_type="department",
            target_id=id,
            details={"is_active": department.is_active}
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")
    
    return DepartmentResponse(**department.model_dump(exclude={"id"}), id=str(department.id))
