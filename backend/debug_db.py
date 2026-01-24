import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.department import Department
from app.models.course import Course
from beanie import init_beanie

async def debug_database():
    print(f"Connecting to: {settings.database_url}")
    client = AsyncIOMotorClient(settings.database_url)
    db = client.get_default_database()
    print(f"Database Name: {db.name}")
    
    # Check raw collections
    collections = await db.list_collection_names()
    print(f"Collections found: {collections}")
    
    if "Department" in collections:
        count = await db["Department"].count_documents({})
        print(f"Raw 'Department' count: {count}")
        async for doc in db["Department"].find({}).limit(5):
            print(f" - Dept: {doc.get('name')} (is_active={doc.get('is_active')})")
    else:
        print("Collection 'Department' NOT found (might be 'department' lowercase?)")
        
    if "Course" in collections:
        count = await db["Course"].count_documents({})
        print(f"Raw 'Course' count: {count}")
    
    # Initialize Beanie to check filtering
    await init_beanie(database=db, document_models=[Department, Course])
    
    beanie_count = await Department.find_all().count()
    print(f"Beanie Department count: {beanie_count}")

if __name__ == "__main__":
    asyncio.run(debug_database())
