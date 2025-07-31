import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "backendapp")
COLLECTION_NAME = "users"

sample_users = [
    {"name": "Alice", "email": "alice@example.com", "age": 28},
    {"name": "Bob", "email": "bob@example.com", "age": 32},
    {"name": "Charlie", "email": "charlie@example.com", "age": 52},
    {"name": "Dexter", "email": "dexter@example.com", "age": 25}
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
