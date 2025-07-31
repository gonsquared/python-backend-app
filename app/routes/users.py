from fastapi import APIRouter, HTTPException
from app.models.user_model import users_db

router = APIRouter()

@router.get("/", summary="Get all users")
async def get_users():
    return {"users": users_db}

@router.get("/{user_id}", summary="Get user by ID")
async def get_user(user_id: int):
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", summary="Create new user")
async def create_user(user: dict):
    new_id = max([u["id"] for u in users_db], default=0) + 1
    new_user = {"id": new_id, **user}
    users_db.append(new_user)
    return new_user

@router.put("/{user_id}", summary="Update user by ID")
async def update_user(user_id: int, updated_user: dict):
    for idx, user in enumerate(users_db):
        if user["id"] == user_id:
            users_db[idx].update(updated_user)
            return users_db[idx]
    raise HTTPException(status_code=404, detail="User not found")

@router.patch("/{user_id}", summary="Partially update a user")
async def patch_user(user_id: int, partial_update: dict):
    for idx, user in enumerate(users_db):
        if user["id"] == user_id:
            for key, value in partial_update.items():
                if key in users_db[idx]:
                    users_db[idx][key] = value
            return users_db[idx]
    raise HTTPException(status_code=404, detail="User not found")

@router.delete("/{user_id}", summary="Delete user by ID")
async def delete_user(user_id: int):
    for idx, user in enumerate(users_db):
        if user["id"] == user_id:
            deleted = users_db.pop(idx)
            return {"message": "User deleted", "user": deleted}
    raise HTTPException(status_code=404, detail="User not found")
