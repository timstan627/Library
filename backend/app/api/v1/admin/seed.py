from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.deps import require_admin
from app.models.department import Department
from app.models.course import Course

router = APIRouter()

@router.post("/seed")
async def seed_database(
    current_user = Depends(require_admin),
):
    """Seed the database with initial data (Departments/Courses)."""
    
    # 1. Departments
    departments = [
        {"name": "Computer Science", "code": "CSE", "is_active": True},
        {"name": "Information Technology", "code": "IT", "is_active": True},
        {"name": "Electronics & Comm.", "code": "ECE", "is_active": True},
        {"name": "Electrical Engineering", "code": "EE", "is_active": True},
        {"name": "Mechanical Engineering", "code": "ME", "is_active": True},
        {"name": "Civil Engineering", "code": "CE", "is_active": True},
    ]
    
    created_depts = 0
    created_courses = 0
    
    for dept_data in departments:
        existing = await Department.find_one(Department.code == dept_data["code"])
        if not existing:
            dept = Department(**dept_data)
            await dept.create()
            created_depts += 1
            
            # Create sample courses for CSE only to start
            if dept.code == "CSE":
                courses = [
                    {"name": "Data Structures", "code": "CS101", "semester": "3"},
                    {"name": "Algorithms", "code": "CS102", "semester": "4"},
                    {"name": "Database Management", "code": "CS103", "semester": "5"},
                    {"name": "Operating Systems", "code": "CS104", "semester": "5"},
                ]
                for c_data in courses:
                    # Explicitly set department linkage
                    course = Course(**c_data, department=dept)
                    await course.create()
                    created_courses += 1
    
    return {
        "message": "Seeding complete",
        "departments_created": created_depts,
        "courses_created": created_courses
    }
