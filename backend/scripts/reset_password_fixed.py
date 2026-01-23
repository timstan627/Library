import asyncio
from app.models.user import User
from app.core.security import security_manager
from app.core.database import init_db

async def reset_password():
    await init_db()
    email = "rajeshpaul1414@gmail.com"
    new_password = "Rajesh123%"
    
    # Try to find the user
    user = await User.find_one(User.email == email)
    
    if user:
        # User found, update password_hash directly (since field name is password_hash)
        user.password_hash = security_manager.hash_password(new_password)
        await user.save()
        print(f"✅ SUCCESS! Password reset for {user.email}")
        print(f"🔑 New Password: {new_password}")
        print(f"👤 Role: {user.role}")
    else:
        print(f"❌ User {email} not found")

if __name__ == "__main__":
    try:
        asyncio.run(reset_password())
    except Exception as e:
        print(f"❌ Error during reset: {str(e)}")
