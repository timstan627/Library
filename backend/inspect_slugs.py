import asyncio
from app.core.database import init_db
from app.models.resource import Resource

async def main():
    await init_db()
    resources = await Resource.find().to_list()
    for r in resources:
        print(f"TITLE: {r.title} | SLUG: {r.slug} | DELETED: {r.is_deleted} | VISIBILITY: {r.visibility} | ID: {r.id}")

if __name__ == "__main__":
    asyncio.run(main())
