import asyncio
from app.core.database import init_db
from app.models.user import User

async def main():
    await init_db()
    
    email = "blasteranna1414@gmail.com"
    user = await User.find_one(User.email == email)
    
    if user:
        print(f"User found: {user.email}")
        print(f"Current Role: '{user.role}'")
        print(f"Active: {user.is_active}")
        
        if user.role != "admin":
            print(f"Updating role from '{user.role}' to 'admin'...")
            user.role = "admin"
            await user.save()
            print("Role updated successfully.")
        else:
            print("User is already an admin.")
    else:
        print(f"User {email} not found!")

if __name__ == "__main__":
    asyncio.run(main())
