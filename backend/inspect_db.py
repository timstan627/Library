import asyncio
import os
from app.core.database import init_db
from app.models.resource import Resource
from app.core.config import settings

async def main():
    print(f"Connecting to: {settings.database_url}")
    await init_db()
    
    print("\n--- ALL PUBLIC RESOURCES ---")
    resources = await Resource.find(Resource.is_deleted == False, Resource.visibility == "public").to_list()
    print(f"Found {len(resources)} public resources.")
    for r in resources:
        print(f"ID: {r.id} (type: {type(r.id)})")
        print(f"Title: {r.title}")
        print(f"Slug: {r.slug}")
        print(f"File: {r.file_name}")
        print(f"Uploader: {r.uploader}")
        print("-" * 20)

    print("\n--- CHECKING TELEGRAM CONFIG ---")
    print(f"API ID: {settings.telegram_api_id}")
    print(f"BOT TOKEN: {'Set' if settings.telegram_bot_token else 'Not Set'}")
    print(f"CHANNEL: {settings.telegram_primary_channel}")

if __name__ == "__main__":
    asyncio.run(main())
