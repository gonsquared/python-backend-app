from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import db
from app.dependencies.auth import get_current_user
from app.helpers.user_helper import get_user_role, serialize_user
from app.models.user_model import User, UpdateAvatar, UpdateUser
from app.security import hash_password
from app.utils import model_to_dict

router = APIRouter()
users_collection = db["users"]
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


def model_field_was_set(model, field_name: str) -> bool:
    fields_set = getattr(model, "model_fields_set", None)
    if fields_set is None:
        fields_set = getattr(model, "__fields_set__", set())
    return field_name in fields_set

async def ensure_email_is_unique(email: str, user_id: str | None = None):
    existing = await users_collection.find_one({"email": email})
    if not existing:
        return

    if user_id and existing.get("_id") == ObjectId(user_id):
        return

    raise HTTPException(status_code=400, detail="Email already exists")

def user_is_admin(user) -> bool:
    return get_user_role(user) == "admin"

def require_manage_users(user):
    if user_is_admin(user):
        return

    raise HTTPException(status_code=403, detail="Manage users permission is required")

def require_manage_own_or_users(target_user_id: str, current_user):
    if user_is_admin(current_user):
        return

    if str(current_user.get("_id")) == target_user_id:
        return

    raise HTTPException(status_code=403, detail="You can only manage your own data")

def apply_non_admin_field_restrictions(update_data: dict, current_user) -> dict:
    if user_is_admin(current_user):
        return update_data

    return {
        field: value
        for field, value in update_data.items()
        if field not in {"role", "status", "permissions", "createdBy"}
    }

@router.post("/", summary="Create a new user")
async def create_user(user: User, current_user=Depends(get_current_user)):
    require_manage_users(current_user)
    await ensure_email_is_unique(user.email)

    user_dict = model_to_dict(user)
    password = user_dict.pop("password", None)
    if password:
        user_dict["passwordHash"] = hash_password(password)
    user_dict["createdBy"] = str(current_user["_id"])

    result = await users_collection.insert_one(user_dict.copy())
    return serialize_user({"_id": result.inserted_id, **user_dict})

@router.get("/", summary="Get all users")
async def get_users(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    skip: Annotated[int, Query(ge=0)] = 0,
    current_user=Depends(get_current_user),
):
    query = {} if user_is_admin(current_user) else {"_id": current_user["_id"]}
    users = await users_collection.find(query).skip(skip).limit(limit).to_list(limit)
    return [serialize_user(user) for user in users]

@router.get("/by-email/{email}", summary="Get user by email")
async def get_user_by_email(email: str, current_user=Depends(get_current_user)):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    require_manage_own_or_users(str(user["_id"]), current_user)
    return serialize_user(user)

@router.get("/{user_id}", summary="Get user by ID")
async def get_user_by_id(user_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    require_manage_own_or_users(user_id, current_user)

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user(user)

@router.put("/{user_id}", summary="Update user by ID")
async def update_user(user_id: str, updated_user: User, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    require_manage_own_or_users(user_id, current_user)

    update_data = model_to_dict(updated_user)
    if not model_field_was_set(updated_user, "status"):
        update_data.pop("status", None)
    if not model_field_was_set(updated_user, "role"):
        update_data.pop("role", None)
    update_data = apply_non_admin_field_restrictions(update_data, current_user)

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

@router.patch("/{user_id}", summary="Update user partially by ID")
async def patch_user(user_id: str, updated_user: UpdateUser, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    require_manage_own_or_users(user_id, current_user)

    update_data = {k: v for k, v in model_to_dict(updated_user).items() if v is not None}
    update_data = apply_non_admin_field_restrictions(update_data, current_user)
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

@router.patch("/{user_id}/avatar", summary="Update user avatar")
async def update_user_avatar(
    user_id: str, updated_avatar: UpdateAvatar, current_user=Depends(get_current_user)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    require_manage_own_or_users(user_id, current_user)

    update_data = {"avatarUrl": updated_avatar.avatarUrl}
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user({**user, **update_data})

@router.delete("/{user_id}", summary="Delete user by ID")
async def delete_user(user_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    require_manage_own_or_users(user_id, current_user)

    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
