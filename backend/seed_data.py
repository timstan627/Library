import asyncio
import os
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.department import Department
from app.models.course import Course
from app.models.user import User
from app.models.resource import Resource
from app.models.download import Download
from app.models.rating import Rating
from app.models.report import Report
from app.models.audit_log import AuditLog

async def seed_data():
    """Seed initial data for the application."""
    print("Connecting to database...")
    client = AsyncIOMotorClient(settings.database_url)
    await init_beanie(
        database=client.get_default_database(),
        document_models=[
            User, Resource, Download, Rating, Report, 
            Department, Course, AuditLog
        ],
    )
    print("Connected.")

    # 1. Departments
    departments = [
        {"name": "Computer Science", "code": "CSE", "is_active": True},
        {"name": "Information Technology", "code": "IT", "is_active": True},
        {"name": "Electronics & Communication", "code": "ECE", "is_active": True},
        {"name": "Electrical Engineering", "code": "EE", "is_active": True},
        {"name": "Mechanical Engineering", "code": "ME", "is_active": True},
        {"name": "Civil Engineering", "code": "CE", "is_active": True},
    ]
    
    print(f"Seeding {len(departments)} departments...")
    for dept_data in departments:
        existing = await Department.find_one(Department.code == dept_data["code"])
        if not existing:
            dept = Department(**dept_data)
            await dept.create()
            print(f"Created department: {dept.name}")
        else:
            print(f"Department exists: {existing.name}")

    # 2. Courses (Sample)
    # Fetch departments to link
    cse = await Department.find_one(Department.code == "CSE")
    
    if cse:
        courses = [
            {"name": "Data Structures", "code": "CS101", "semester": "3", "department": cse},
            {"name": "Algorithms", "code": "CS102", "semester": "4", "department": cse},
            {"name": "Database Management", "code": "CS103", "semester": "5", "department": cse},
            {"name": "Operating Systems", "code": "CS104", "semester": "5", "department": cse},
        ]
        
        print(f"Seeding {len(courses)} courses for CSE...")
        for course_data in courses:
            existing = await Course.find_one(Course.code == course_data["code"])
            if not existing:
                course = Course(**course_data)
                await course.create()
                print(f"Created course: {course.name}")
            else:
                print(f"Course exists: {existing.name}")

    print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
