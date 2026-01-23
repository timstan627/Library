"""
Admin API - Course Management
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from beanie import PydanticObjectId

from app.models.user import User
from app.models.department import Department
from app.models.course import Course
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseListResponse
)
from app.api.v1.deps import get_current_user, require_admin
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin/courses", tags=["Admin - Courses"])


@router.get("", response_model=CourseListResponse)
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    department_id: str | None = None,
    is_active: bool | None = None,
    current_user: User = Depends(require_admin),
):
    """List all courses (admin only)."""
    print(f"DEBUG: list_courses called with department_id={department_id}, is_active={is_active}")
    
    # Build query expressions
    expressions = []
    
    if department_id:
        try:
            dept_obj_id = PydanticObjectId(department_id)
            # Use Beanie expression for Link ID
            expressions.append(Course.department.id == dept_obj_id)
        except Exception as e:
            print(f"DEBUG: Invalid department_id: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department ID")
    
    if is_active is not None:
        expressions.append(Course.is_active == is_active)
    
    # Get total count
    total = await Course.find(*expressions).count()
    
    # Get paginated results WITHOUT eager loading to avoid cursor issues
    courses = (
        await Course.find(*expressions)
        .sort("+code")
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list()
    )
    print(f"DEBUG: Expressions: {expressions}")
    print(f"DEBUG: Total courses: {total}")
    print(f"DEBUG: Fetched courses: {len(courses)}")
    
    # Extract department IDs from Link references and batch query
    from app.models.department import Department
    dept_ids = []
    for course in courses:
        if hasattr(course.department, 'ref') and course.department.ref:
            dept_ids.append(course.department.ref.id)
    
    # Fetch all departments in one query
    departments = {}
    if dept_ids:
        dept_list = await Department.find({"_id": {"$in": dept_ids}}).to_list()
        departments = {str(dept.id): dept for dept in dept_list}
    
    # Build response with department info
    results = []
    for course in courses:
        dept_id = None
        dept_name = None
        
        # Get department ID from Link reference
        if hasattr(course.department, 'ref') and course.department.ref:
            dept_id = str(course.department.ref.id)
            if dept_id in departments:
                dept_name = departments[dept_id].name
            
        results.append(
            CourseResponse(
                **course.model_dump(exclude={"id"}),
                id=str(course.id),
                department_id=dept_id,
                department_name=dept_name
            )
        )
    
    return CourseListResponse(
        results=results,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    current_user: User = Depends(require_admin),
):
    """Create a new course (admin only)."""
    # Verify department exists
    try:
        dept_obj_id = PydanticObjectId(data.department_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department ID")
    
    department = await Department.get(dept_obj_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    
    # Check for duplicate code
    existing = await Course.find_one(Course.code == data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with code '{data.code}' already exists"
        )
    
    # Create course
    course_dict = data.model_dump()
    course_dict["department"] = department
    del course_dict["department_id"]
    
    course = Course(**course_dict)
    await course.create()
    
    # Audit log
    try:
        audit = AuditLog(
            action="create_course",
            actor=current_user,
            target_type="course",
            target_id=str(course.id),
            details={"name": course.name, "code": course.code, "department": department.name}
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")
    
    return CourseResponse(
        **course.model_dump(exclude={"id"}),
        id=str(course.id),
        department_id=str(department.id),
        department_name=department.name
    )


@router.put("/{id}", response_model=CourseResponse)
async def update_course(
    id: str,
    data: CourseUpdate,
    current_user: User = Depends(require_admin),
):
    """Update a course (admin only)."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")
    
    course = await Course.get(obj_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    await course.fetch_all_links()
    
    # Update department if provided
    if data.department_id:
        try:
            dept_obj_id = PydanticObjectId(data.department_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department ID")
        
        department = await Department.get(dept_obj_id)
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        
        course.department = department
    
    # Check for duplicate code if changing
    if data.code and data.code != course.code:
        existing = await Course.find_one(Course.code == data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course with code '{data.code}' already exists"
            )
    
    # Update other fields
    update_data = data.model_dump(exclude_unset=True, exclude={"department_id"})
    for key, value in update_data.items():
        setattr(course, key, value)
    
    await course.save()
    
    # Audit log
    try:
        audit = AuditLog(
            action="update_course",
            actor=current_user,
            target_type="course",
            target_id=str(course.id),
            details=update_data
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")
    
    return CourseResponse(
        **course.model_dump(exclude={"id"}),
        id=str(course.id),
        department_id=str(course.department.id) if course.department else None,
        department_name=course.department.name if course.department else None
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    id: str,
    current_user: User = Depends(require_admin),
):
    """Delete a course (admin only)."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")
    
    course = await Course.get(obj_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    # Cascade delete: Delete all resources associated with this course
    from app.models.resource import Resource
    # Delete all resources linked to this course
    await Resource.find(Resource.course_id.id == obj_id).delete()
    
    await course.delete()
    
    # Audit log
    try:
        audit = AuditLog(
            action="delete_course",
            actor=current_user,
            target_type="course",
            target_id=id,
            details={"name": course.name, "code": course.code}
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")
