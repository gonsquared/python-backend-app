from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.user_model import LoginUser, RegisterUser
from app.routes import auth as auth_route
from app.security import verify_password


class FakeUsersCollection:
    def __init__(self, documents=None):
        self.documents = list(documents or [])
        self.inserted_payload = None

    async def find_one(self, query):
        if "email" in query:
            return next(
                (
                    document
                    for document in self.documents
                    if document.get("email") == query["email"]
                ),
                None,
            )

        return None

    async def insert_one(self, document):
        self.inserted_payload = document.copy()
        document["_id"] = ObjectId("64f1f77bcf86cd7994390111")
        self.documents.append(document)
        return SimpleNamespace(inserted_id=ObjectId("64f1f77bcf86cd7994390111"))


@pytest.fixture(autouse=True)
def restore_users_collection():
    original_collection = auth_route.users_collection
    yield
    auth_route.users_collection = original_collection


@pytest.mark.asyncio
async def test_register_hashes_password_and_returns_user_without_password_data():
    collection = FakeUsersCollection()
    auth_route.users_collection = collection

    result = await auth_route.register(
        RegisterUser(
            firstName="Jane",
            lastName="Doe",
            email="jane@example.com",
            password="VeryStrongPassword123!",
            verifyPassword="VeryStrongPassword123!",
        )
    )

    assert collection.inserted_payload["passwordHash"] != "VeryStrongPassword123!"
    assert collection.inserted_payload["passwordHash"].startswith("$argon2")
    assert verify_password(
        "VeryStrongPassword123!",
        collection.inserted_payload["passwordHash"],
    )
    assert "password" not in result["user"]
    assert "passwordHash" not in result["user"]
    assert result["user"]["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_register_rejects_mismatched_passwords():
    auth_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await auth_route.register(
            RegisterUser(
                firstName="Jane",
                lastName="Doe",
                email="jane@example.com",
                password="VeryStrongPassword123!",
                verifyPassword="DifferentPassword123!",
            )
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Passwords do not match"


@pytest.mark.asyncio
async def test_login_returns_access_token_for_valid_credentials():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    auth_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "passwordHash": auth_route.hash_password("VeryStrongPassword123!"),
            }
        ]
    )

    result = await auth_route.login(
        LoginUser(email="jane@example.com", password="VeryStrongPassword123!")
    )

    assert result["tokenType"] == "bearer"
    assert result["accessToken"]
    assert result["user"]["email"] == "jane@example.com"
    assert "passwordHash" not in result["user"]


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials():
    auth_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await auth_route.login(
            LoginUser(email="missing@example.com", password="WrongPassword123!")
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid email or password"
