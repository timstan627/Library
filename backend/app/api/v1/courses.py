"""
Public API - Courses (for dropdowns in upload forms)
"""
from typing import List
from fastapi import APIRouter, Query, HTTPException, status
from beanie import PydanticObjectId

from app.models.course import Course
from app.models.department import Department

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("")
async def list_active_courses(
    department_id: str | None = Query(None, description="Filter by department ID")
):
    """List all active courses, optionally filtered by department."""
    try:
        # Build query expressions
        expressions = [Course.is_active == True]
        
        if department_id:
            try:
                dept_obj_id = PydanticObjectId(department_id)
                expressions.append(Course.department.id == dept_obj_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid department ID"
                )
        
        courses = await Course.find(*expressions).sort("+code").to_list(1000)
        
        # Extract department IDs using model_dump to get raw data
        dept_ids = set()
        for course in courses:
            raw = course.model_dump()
            if 'department' in raw and raw['department']:
                dept_ref = raw['department']
                if isinstance(dept_ref, dict) and '$id' in dept_ref:
                    dept_ids.add(dept_ref['$id'])
                elif hasattr(dept_ref, 'id'):
                    dept_ids.add(dept_ref.id)
        
        # Fetch all departments in one query
        departments = {}
        if dept_ids:
            dept_list = await Department.find({"_id": {"$in": list(dept_ids)}}).to_list()
            departments = {str(dept.id): dept for dept in dept_list}
        
        # Build response
        results = []
        for course in courses:
            dept_id = None
            dept_name = None
            
            # Get department from raw dump
            raw = course.model_dump()
            if 'department' in raw and raw['department']:
                dept_ref = raw['department']
                if isinstance(dept_ref, dict) and '$id' in dept_ref:
                    dept_id = str(dept_ref['$id'])
                elif hasattr(dept_ref, 'id'):
                    dept_id = str(dept_ref.id)
                
                if dept_id and dept_id in departments:
                    dept_name = departments[dept_id].name
            
            results.append({
                "id": str(course.id),
                "name": course.name,
                "code": course.code,
                "description": course.description,
                "semester": course.semester,
                "credits": course.credits,
                "department_id": dept_id,
                "department_name": dept_name,
                "is_active": course.is_active,
            })
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        print(f"Courses endpoint error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}")
async def get_course(id: str):
    """Get a specific course by ID."""
    try:
        obj_id = PydanticObjectId(id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID"
        )
    
    course = await Course.get(obj_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    dept_id = None
    dept_name = None
    raw = course.model_dump()
    if 'department' in raw and raw['department']:
        dept_ref = raw['department']
        if isinstance(dept_ref, dict) and '$id' in dept_ref:
            dept_id = str(dept_ref['$id'])
        
        # Fetch department for name
        if dept_id:
            dept = await Department.get(PydanticObjectId(dept_id))
            if dept:
                dept_name = dept.name
    
    return {
        "id": str(course.id),
        "name": course.name,
        "code": course.code,
        "description": course.description,
        "semester": course.semester,
        "credits": course.credits,
        "department_id": dept_id,
        "department_name": dept_name,
        "is_active": course.is_active,
    }
