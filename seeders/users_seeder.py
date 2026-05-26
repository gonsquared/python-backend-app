import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values, load_dotenv
from app.helpers.user_helper import ADMIN_PERMISSIONS
from app.security import hash_password

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "backendapp")
COLLECTION_NAME = "users"

sample_users = [
    {"firstName": "Alice", "lastName": "Johnson", "email": "alice@example.com", "status": "active", "role": "user"},
    {"firstName": "Bob", "lastName": "Smith", "email": "bob@example.com", "status": "active", "role": "user"},
    {"firstName": "Charlie", "lastName": "Brown", "email": "charlie@example.com", "status": "inactive", "role": "user"},
    {"firstName": "Dexter", "lastName": "Morgan", "email": "dexter@example.com", "status": "archived", "role": "user"},
]

def get_required_admin_config(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value

    dotenv_value = dotenv_values().get(name)
    if dotenv_value:
        return dotenv_value

    raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be configured")

async def seed_users():
    admin_email = get_required_admin_config("ADMIN_EMAIL")
    admin_password = get_required_admin_config("ADMIN_PASSWORD")

    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db[COLLECTION_NAME]

    for user in sample_users:
        await users_collection.update_one(
            {"email": user["email"]},
            {"$setOnInsert": user},
            upsert=True,
        )
    print(f"Seeded {len(sample_users)} sample users if missing.")

    await users_collection.update_one(
        {"email": admin_email},
        {
            "$set": {
                "firstName": "Dar",
                "lastName": "Gon",
                "email": admin_email,
                "status": "active",
                "role": "admin",
                "permissions": ADMIN_PERMISSIONS,
                "passwordHash": hash_password(admin_password),
            }
        },
        upsert=True,
    )
    print(f"Upserted admin user '{admin_email}'.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_users())
