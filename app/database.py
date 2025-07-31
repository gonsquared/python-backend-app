from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI

MONGO_URL = "mongodb://localhost:27017"
MONGO_DB_NAME = "backendapp"

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]
