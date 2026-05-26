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
        self.updated_filter = None
        self.updated_data = None
        self.matched_count = 1

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

        if "_id" in query:
            return next(
                (
                    document
                    for document in self.documents
                    if document.get("_id") == query["_id"]
                ),
                None,
            )

        return None

    async def insert_one(self, document):
        self.inserted_payload = document.copy()
        document["_id"] = ObjectId("64f1f77bcf86cd7994390111")
        self.documents.append(document)
        return SimpleNamespace(inserted_id=ObjectId("64f1f77bcf86cd7994390111"))

    async def update_one(self, query, update):
        self.updated_filter = query
        self.updated_data = update
        for document in self.documents:
            if document.get("_id") == query.get("_id"):
                document.update(update.get("$set", {}))
        return SimpleNamespace(matched_count=self.matched_count)


@pytest.fixture(autouse=True)
def restore_users_collection():
    original_collection = auth_route.users_collection
    yield
    auth_route.users_collection = original_collection


@pytest.mark.asyncio
async def test_register_hashes_password_sends_activation_email_and_returns_safe_user(monkeypatch):
    collection = FakeUsersCollection()
    auth_route.users_collection = collection
    sent_messages = []
    monkeypatch.setattr(
        auth_route,
        "send_activation_email",
        lambda email, link: sent_messages.append({"email": email, "link": link}),
    )

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
    assert result["user"]["status"] == "inactive"
    assert result["user"]["role"] == "user"
    assert result["user"]["permissions"] == ["manage_own", "manage_own_notes"]
    assert collection.inserted_payload["status"] == "inactive"
    assert collection.inserted_payload["role"] == "user"
    assert sent_messages[0]["email"] == "jane@example.com"
    assert "http://localhost:5173/activate-account?token=" in sent_messages[0]["link"]
    assert result["message"] == "Registration successful. Please check your email to activate your account."


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
                "status": "active",
                "role": "admin",
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
    assert result["user"]["role"] == "admin"
    assert result["user"]["permissions"] == [
        "manage_users",
        "manage_own",
        "manage_notes",
        "manage_own_notes",
    ]
    assert "passwordHash" not in result["user"]


@pytest.mark.asyncio
async def test_login_rejects_inactive_email():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    auth_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "status": "inactive",
                "passwordHash": auth_route.hash_password("VeryStrongPassword123!"),
            }
        ]
    )

    with pytest.raises(HTTPException) as error:
        await auth_route.login(
            LoginUser(email="jane@example.com", password="VeryStrongPassword123!")
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Email address needs to be activated before login"


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials():
    auth_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await auth_route.login(
            LoginUser(email="missing@example.com", password="WrongPassword123!")
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_allows_legacy_activated_user():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    auth_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "isEmailActivated": True,
                "passwordHash": auth_route.hash_password("VeryStrongPassword123!"),
            }
        ]
    )

    result = await auth_route.login(
        LoginUser(email="jane@example.com", password="VeryStrongPassword123!")
    )

    assert result["user"]["status"] == "active"


@pytest.mark.asyncio
async def test_activate_account_marks_user_as_active():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "status": "inactive",
                "passwordHash": auth_route.hash_password("VeryStrongPassword123!"),
            }
        ]
    )
    auth_route.users_collection = collection
    token = auth_route.create_email_activation_token(str(user_id))

    result = await auth_route.activate_account(token)

    assert collection.updated_filter == {"_id": user_id}
    assert collection.updated_data == {"$set": {"status": "active"}}
    assert collection.documents[0]["status"] == "active"
    assert result == {"message": "Email address activated successfully"}
