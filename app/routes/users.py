from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from app.database import db
from app.helpers.user_helper import serialize_user
from app.models.user_model import User, UpdateUser
from app.middlewares.validate_email import validate_email
from app.security import hash_password

router = APIRouter()
users_collection = db["users"]

def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()

async def ensure_email_is_unique(email: str, user_id: str | None = None):
    existing = await users_collection.find_one({"email": email})
    if not existing:
        return

    if user_id and existing.get("_id") == ObjectId(user_id):
        return

    raise HTTPException(status_code=400, detail="Email already exists")

@router.post("/", summary="Create a new user", dependencies=[Depends(validate_email)])
async def create_user(user: User):
    await ensure_email_is_unique(user.email)

    user_dict = model_to_dict(user)
    password = user_dict.pop("password", None)
    if password:
        user_dict["passwordHash"] = hash_password(password)

    result = await users_collection.insert_one(user_dict.copy())
    return serialize_user({"_id": result.inserted_id, **user_dict})

@router.get("/", summary="Get all users")
async def get_users():
    users = await users_collection.find().to_list(100)
    return [serialize_user(user) for user in users]

@router.get("/{user_id}", summary="Get user by ID")
async def get_user_by_id(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

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

@router.put("/{user_id}", summary="Update user by ID", dependencies=[Depends(validate_email)])
async def update_user(user_id: str, updated_user: User):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    update_data = model_to_dict(updated_user)
    password = update_data.pop("password", None)
    if password:
        update_data["passwordHash"] = hash_password(password)

    await ensure_email_is_unique(updated_user.email, user_id)
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return serialize_user(user)

@router.patch("/{user_id}", summary="Update user partially by ID", dependencies=[Depends(validate_email)])
async def patch_user(user_id: str, updated_user: UpdateUser):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    update_data = {k: v for k, v in model_to_dict(updated_user).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    password = update_data.pop("password", None)
    if password:
        update_data["passwordHash"] = hash_password(password)

    if "email" in update_data:
        await ensure_email_is_unique(update_data["email"], user_id)

    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return serialize_user(user)

@router.delete("/{user_id}", summary="Delete user by ID")
async def delete_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
