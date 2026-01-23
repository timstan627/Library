"""
Database Configuration and Initialization (MongoDB)
"""
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings

# Import models to register
# Note: We will add models here as we rewrite them
# from app.models.user import User
# from app.models.resource import Resource
# ...

async def init_db():
    """Initialize MongoDB connection and Beanie ODM."""
    # Create Motor client
    client = AsyncIOMotorClient(
        settings.database_url,
        uuidRepresentation="standard"
    )
    
    # Get database name from connection string or default
    db_name = "student_library"
    if "mongodb.net" in settings.database_url and not settings.database_url.endswith("/"):
        # Atlas connection strings often have the db name in the path or params
        pass 
        
    # Initialize Beanie with the document models
    # We'll need to import the models inside the function or at module level 
    # but strictly after they are defined to avoid circular imports during refactoring
    
    # For now, we'll start with an empty list and add models as we migrate them
    document_models = []
    
    try:
        from app.models.user import User, Session, APIKey
        document_models.extend([User, Session, APIKey])
    except ImportError:
        pass
        
    try:
        from app.models.resource import Resource
        document_models.append(Resource)
    except ImportError:
        pass
        
    try:
        from app.models.rating import Rating
        document_models.append(Rating)
    except ImportError:
        pass

    try:
        from app.models.download import Download
        document_models.append(Download)
    except ImportError:
        pass
        
    try:
        from app.models.report import Report
        document_models.append(Report)
    except ImportError:
        pass
        
    try:
        from app.models.audit_log import AuditLog
        document_models.append(AuditLog)
    except ImportError:
        pass
    
    try:
        from app.models.department import Department
        document_models.append(Department)
    except ImportError:
        pass
    
    try:
        from app.models.course import Course
        document_models.append(Course)
    except ImportError:
        pass

    # MIGRATION: Drop strict file_hash index if it exists
    # This allow Beanie to recreate it as non-unique
    try:
        db = client[db_name]
        # Check if collection exists first to avoid auto-creation issues
        cols = await db.list_collection_names()
        if "resources" in cols:
            await db.resources.drop_index("file_hash_1")
            print("Migration: Dropped strict file_hash index.")

        # MIGRATION: Drop strict rating index (user_1_resource_1) to allow multiple comments
        if "ratings" in cols:
             try:
                await db.ratings.drop_index("user_1_resource_1")
                print("Migration: Dropped strict user_resource rating index.")
             except Exception:
                pass # Index might not exist or already dropped
            
        # MIGRATION: Update all users to 100TB quota
        if "users" in cols:
             # 100TB = 109951162777600
             await db.users.update_many({}, {"$set": {"storage_quota_bytes": 109951162777600}})
             print("Migration: Updated users storage quota to 100TB.")
             
    except Exception:
        pass # Index might not exist or other error, safe to ignore

    await init_beanie(
        database=client[db_name],
        document_models=document_models
    )

async def close_db():
    """Close database connections."""
    # Motor/Mongo client handles pooling automatically, explicit close 
    # is usually not required for async apps giving control back to event loop,
    # but good for cleanup.
    pass


async def seed_default_admin():
    """Create default admin user if it doesn't exist."""
    from app.models.user import User
    from app.core.security import security_manager
    
    default_admin_email = "blasteranna1414@gmail.com"
    
    # Check if default admin already exists
    existing = await User.find_one(User.email == default_admin_email)
    if existing:
        return  # Admin already exists
    
    # Create default admin
    admin = User(
        email=default_admin_email,
        password_hash=security_manager.hash_password("Blaster1414&"),
        display_name="The Creater",
        role="admin",
        is_active=True,
        is_banned=False,
        is_email_verified=True,
        storage_quota_bytes=10 * 1024 * 1024 * 1024,  # 10GB
    )
    await admin.create()
    print(f"✓ Default admin created: {default_admin_email}")
