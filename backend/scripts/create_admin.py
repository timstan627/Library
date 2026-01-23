"""
Script to create an admin user for testing
"""
import asyncio
from app.core.database import init_db
from app.models.user import User
from app.core.security import security_manager


async def create_admin():
    # Initialize database
    await init_db()
    
    # Check if admin exists
    existing = await User.find_one(User.email == "admintest@library.com")
    if existing:
        print(f"Admin user already exists: {existing.email}")
        # Update to admin role if needed
        if existing.role != "admin":
            existing.role = "admin"
            await existing.save()
            print("Updated existing user to admin role")
        return
    
    # Create new admin user
    hashed_password = security_manager.hash_password("AdminTest123!")
    admin_user = User(
        email="admintest@library.com",
        display_name="Admin Test User",
        hashed_password=hashed_password,
        role="admin",
        is_active=True
    )
    
    await admin_user.insert()
    print(f"✅ Admin user created successfully!")
    print(f"Email: admintest@library.com")
    print(f"Password: AdminTest123!")
    print(f"Role: {admin_user.role}")


if __name__ == "__main__":
    asyncio.run(create_admin())
