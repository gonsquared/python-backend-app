from fastapi import APIRouter, HTTPException, status

from app.database import db
from app.helpers.user_helper import serialize_user
from app.models.user_model import LoginUser, RegisterUser
from app.security import create_access_token, hash_password, verify_password

router = APIRouter()
users_collection = db["users"]


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


async def ensure_email_is_unique(email: str):
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

    result = await users_collection.insert_one(user_dict.copy())
    created_user = {"_id": result.inserted_id, **user_dict}
    return {"user": serialize_user(created_user)}


@router.post("/login", summary="Login a user")
async def login(credentials: LoginUser):
    user = await users_collection.find_one({"email": credentials.email})

    if not user or not verify_password(credentials.password, user.get("passwordHash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token, expires_in = create_access_token(str(user["_id"]))
    return {
        "accessToken": access_token,
        "tokenType": "bearer",
        "expiresIn": expires_in,
        "user": serialize_user(user),
    }
