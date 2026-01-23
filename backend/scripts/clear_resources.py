"""Script to delete all resources from MongoDB Atlas"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear_all_resources():
    # MongoDB Atlas connection
    mongo_url = "mongodb+srv://f2l1:f2l1@cluster0.hhi78fm.mongodb.net/?appName=Cluster0"
    
    client = AsyncIOMotorClient(mongo_url, uuidRepresentation="standard")
    db = client["student_library"]
    
    # Delete all resources
    result = await db.resources.delete_many({})
    print(f"Deleted {result.deleted_count} resources")
    
    # Also reset user storage
    await db.users.update_many({}, {"$set": {"storage_used_bytes": 0}})
    print("Reset user storage counts")
    
    # Delete downloads log
    downloads_result = await db.downloads.delete_many({})
    print(f"Deleted {downloads_result.deleted_count} download logs")
    
    client.close()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(clear_all_resources())
