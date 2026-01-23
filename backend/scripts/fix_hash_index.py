
import asyncio
import os
import sys

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def fix_indexes():
    # Helper to get valid mongo url
    url = settings.database_url
    if "postgresql" in url:
        print("Settings loaded default Postgres URL. Falling back to local MongoDB default.")
        url = "mongodb://localhost:27017"
        
    print(f"Connecting to MongoDB at {url}")
    client = AsyncIOMotorClient(url)
    db = client["student_library"]
    
    print("Checking indexes on 'resources' collection...")
    try:
        indexes = await db.resources.index_information()
        print(f"Current indexes: {list(indexes.keys())}")
        
        # Look for file_hash index
        # Usually named "file_hash_1"
        index_name = "file_hash_1"
        
        if index_name in indexes:
            print(f"Found index '{index_name}'. Checking if unique...")
            # We can just drop it regardless and let Beanie recreate it on next app startup
            # Since we updated the model to non-unique, Beanie will creating it as non-unique (or standard index)
            # But Beanie doesn't auto-remove indexes usually, so dropping is safer.
            
            print(f"Dropping index '{index_name}'...")
            await db.resources.drop_index(index_name)
            print("Index dropped successfully.")
            print("Restart the backend application for Beanie to recreate it with new settings (non-unique).")
        else:
            print(f"Index '{index_name}' not found. No action needed.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_indexes())
