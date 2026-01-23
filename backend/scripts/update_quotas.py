
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def update_quotas():
    # Fix URL logic same as before
    url = settings.database_url
    if "postgresql" in url:
        print("Fallback to localhost mongo")
        url = "mongodb://localhost:27017"
        
    print(f"Connecting to {url}")
    client = AsyncIOMotorClient(url)
    db = client["student_library"]
    
    # 100TB
    new_quota = 109_951_162_777_600
    
    print(f"Updating all users to quota: {new_quota} bytes (100TB)...")
    result = await db.users.update_many(
        {}, 
        {"$set": {"storage_quota_bytes": new_quota}}
    )
    
    print(f"Matched: {result.matched_count}")
    print(f"Modified: {result.modified_count}")
    print("Done.")
    client.close()

if __name__ == "__main__":
    asyncio.run(update_quotas())
