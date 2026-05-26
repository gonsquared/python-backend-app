from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING

from app.config import get_settings

load_dotenv()

settings = get_settings()
MONGO_URI = settings.mongo_uri
DB_NAME = settings.db_name

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]


async def ensure_database_indexes() -> None:
    await db["users"].create_index("email", unique=True)
    await db["notes"].create_index(
        [("user", ASCENDING), ("updatedAt", DESCENDING)],
        name="user_updated_at_idx",
    )
