"""Script to check course department structure"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId, DBRef

async def check_courses():
    mongo_url = "mongodb+srv://f2l1:f2l1@cluster0.hhi78fm.mongodb.net/?appName=Cluster0"
    
    client = AsyncIOMotorClient(mongo_url, uuidRepresentation="standard")
    db = client["student_library"]
    
    # Get all courses raw
    courses = await db.courses.find({}).to_list(100)
    print(f"Found {len(courses)} courses\n")
    
    for course in courses:
        print(f"Course: {course.get('name')}")
        dept = course.get('department')
        print(f"  department type: {type(dept)}")
        print(f"  department value: {dept}")
        
        if isinstance(dept, DBRef):
            print(f"  DBRef collection: {dept.collection}")
            print(f"  DBRef id: {dept.id}")
        elif isinstance(dept, dict):
            print(f"  Dict keys: {dept.keys()}")
            if '$id' in dept:
                print(f"  $id: {dept['$id']}")
            if '$ref' in dept:
                print(f"  $ref: {dept['$ref']}")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_courses())
