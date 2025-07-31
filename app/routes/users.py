from fastapi import APIRouter, HTTPException
from bson import ObjectId
from app.database import db
from app.helpers.user_helper import serialize_user
from app.models.user_model import User, UpdateUser

router = APIRouter()
users_collection = db["users"]

@router.post("/", summary="Create a new user")
async def create_user(user: User):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    user_dict = user.dict()
    result = await users_collection.insert_one(user_dict)
    return {"id": str(result.inserted_id), **user_dict}

@router.get("/", summary="Get all users")
async def get_users():
    users = await users_collection.find().to_list(100)
    return [serialize_user(user) for user in users]

@router.get("/{user_id}", summary="Get user by ID")
async def get_user_by_id(user_id: str):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user(user)

@router.get("/by-email/{email}", summary="Get user by email")
async def get_user_by_email(email: str):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user(user)

@router.put("/{user_id}", summary="Update user by ID")
async def update_user(user_id: str, updated_user: User):
    update_data = updated_user.dict()
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return serialize_user(user)

@router.patch("/{user_id}", summary="Update user partially by ID")
async def patch_user(user_id: str, updated_user: UpdateUser):
    update_data = {k: v for k, v in updated_user.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return serialize_user(user)

@router.delete("/{user_id}", summary="Delete user by ID")
async def delete_user(user_id: str):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
