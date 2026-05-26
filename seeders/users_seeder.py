import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from app.security import hash_password

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "backendapp")
COLLECTION_NAME = "users"

ADMIN_EMAIL = "gonsquared@gmail.com"
ADMIN_PASSWORD = "L3tmein1234567890!"

sample_users = [
    {"firstName": "Alice", "lastName": "Johnson", "email": "alice@example.com", "status": "active", "role": "user"},
    {"firstName": "Bob", "lastName": "Smith", "email": "bob@example.com", "status": "active", "role": "user"},
    {"firstName": "Charlie", "lastName": "Brown", "email": "charlie@example.com", "status": "inactive", "role": "user"},
    {"firstName": "Dexter", "lastName": "Morgan", "email": "dexter@example.com", "status": "archived", "role": "user"},
]

async def seed_users():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db[COLLECTION_NAME]

    await users_collection.delete_many({})
    result = await users_collection.insert_many(sample_users)
    print(f"Inserted {len(result.inserted_ids)} users into '{COLLECTION_NAME}' collection.")

    await users_collection.update_one(
        {"email": ADMIN_EMAIL},
        {
            "$set": {
                "firstName": "Gon",
                "lastName": "Squared",
                "email": ADMIN_EMAIL,
                "status": "active",
                "role": "admin",
                "passwordHash": hash_password(ADMIN_PASSWORD),
            }
        },
        upsert=True,
    )
    print(f"Upserted admin user '{ADMIN_EMAIL}'.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_users())
