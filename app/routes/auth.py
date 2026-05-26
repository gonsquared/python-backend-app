import os

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.database import db
from app.helpers.email_helper import send_activation_email
from app.helpers.user_helper import get_user_status, serialize_user
from app.models.user_model import LoginUser, RegisterUser
from app.security import (
    create_access_token,
    create_email_activation_token,
    hash_password,
    verify_email_activation_token,
    verify_password,
)
from app.utils import model_to_dict

router = APIRouter()
users_collection = db["users"]


async def ensure_email_is_unique(email: str) -> None:
    existing = await users_collection.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")


@router.post("/register", summary="Register a new user")
async def register(user: RegisterUser):
    if user.password != user.verifyPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    await ensure_email_is_unique(user.email)

    user_dict = model_to_dict(user)
    password = user_dict.pop("password")
    user_dict.pop("verifyPassword")
    user_dict["passwordHash"] = hash_password(password)
    user_dict["status"] = "inactive"
    user_dict["role"] = "user"

    result = await users_collection.insert_one(user_dict.copy())
    created_user = {"_id": result.inserted_id, **user_dict}
    token = create_email_activation_token(str(result.inserted_id))
    frontend_base_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    activation_link = f"{frontend_base_url}/activate-account?token={token}"
    await run_in_threadpool(send_activation_email, user.email, activation_link)
    return {
        "message": "Registration successful. Please check your email to activate your account.",
        "user": serialize_user(created_user),
    }


@router.post("/login", summary="Login a user")
async def login(credentials: LoginUser):
    user = await users_collection.find_one({"email": credentials.email})

    if not user or not verify_password(credentials.password, user.get("passwordHash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if get_user_status(user) != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address needs to be activated before login",
        )

    access_token, expires_in = create_access_token(str(user["_id"]))
    return {
        "accessToken": access_token,
        "tokenType": "bearer",
        "expiresIn": expires_in,
        "user": serialize_user(user),
    }


@router.get("/activate", summary="Activate user email address")
async def activate_account(token: str):
    user_id = verify_email_activation_token(token)
    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid or expired activation link")

    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"status": "active"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Email address activated successfully"}
