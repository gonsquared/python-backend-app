import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "backendapp")
COLLECTION_NAME = "users"

sample_users = [
    {"firstName": "Alice", "lastName": "Johnson", "email": "alice@example.com", "status": "active"},
    {"firstName": "Bob", "lastName": "Smith", "email": "bob@example.com", "status": "active"},
    {"firstName": "Charlie", "lastName": "Brown", "email": "charlie@example.com", "status": "inactive"},
    {"firstName": "Dexter", "lastName": "Morgan", "email": "dexter@example.com", "status": "archived"},
]

async def seed_users():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db[COLLECTION_NAME]

    await users_collection.delete_many({})
    result = await users_collection.insert_many(sample_users)
    print(f"Inserted {len(result.inserted_ids)} users into '{COLLECTION_NAME}' collection.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_users())
