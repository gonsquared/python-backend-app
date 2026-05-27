from fastapi import APIRouter, Depends

from app.database import db
from app.dependencies.auth import get_current_user

router = APIRouter()
notes_collection = db["notes"]


@router.get("/", summary="Get current user's distinct labels")
async def get_labels(current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    result = await notes_collection.distinct("labels", {"user": user_id})
    return sorted(result)
