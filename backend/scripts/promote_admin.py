import asyncio
from app.models.user import User
from app.core.database import init_db

async def promote_to_admin():
    await init_db()
    
    user = await User.find_one(User.email == "rajeshpaul1414@gmail.com")
    if user:
        user.role = "admin"
        await user.save()
        print(f"✅ SUCCESS! Promoted to admin")
        print(f"\n📧 Email: {user.email}")
        print(f"👤 Role: {user.role}")
        print(f"🔑 Password: Use your original password (Rajesh123% or similar)")
    else:
        print("❌ User not found")

if __name__ == "__main__":
    asyncio.run(promote_to_admin())
