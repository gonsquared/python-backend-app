import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import os
import random

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "backendapp")

sample_task_labels = [
    "cook dinner",
    "cook lunch",
    "cook breakfast",
    "clean toilet",
    "clean kitchen"
]

statuses = ["pending", "on-going", "done"]

async def seed_tasks():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db["users"]
    tasks_collection = db["tasks"]

    await tasks_collection.delete_many({})

    users = await users_collection.find().to_list(None)
    if not users:
        print("No users found. Please seed users first.")
        return

    tasks_to_insert = []
    for user in users:
        user_id = user["_id"]
        for _ in range(3):
            now = datetime.utcnow()
            task = {
                "user": ObjectId(user_id),
                "label": random.choice(sample_task_labels),
                "status": random.choice(statuses),
                "createdAt": now,
                "updatedAt": now
            }
            tasks_to_insert.append(task)

    if tasks_to_insert:
        result = await tasks_collection.insert_many(tasks_to_insert)
        print(f"Inserted {len(result.inserted_ids)} tasks for {len(users)} users.")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed_tasks())
