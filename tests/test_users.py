from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.user_model import UpdateUser, User
from app.routes import users as users_route


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    async def to_list(self, _limit):
        return self.documents


class FakeUsersCollection:
    def __init__(self, documents=None):
        self.documents = list(documents or [])
        self.inserted_document = None
        self.updated_filter = None
        self.updated_data = None
        self.deleted_filter = None
        self.matched_count = 1
        self.deleted_count = 1

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

    def find(self):
        return FakeCursor(self.documents)

    async def insert_one(self, document):
        self.inserted_document = document
        return SimpleNamespace(inserted_id=ObjectId("64f1f77bcf86cd7994390111"))

    async def update_one(self, query, update):
        self.updated_filter = query
        self.updated_data = update
        return SimpleNamespace(matched_count=self.matched_count)

    async def delete_one(self, query):
        self.deleted_filter = query
        return SimpleNamespace(deleted_count=self.deleted_count)


@pytest.fixture(autouse=True)
def restore_users_collection():
    original_collection = users_route.users_collection
    yield
    users_route.users_collection = original_collection


def test_user_model_requires_first_name_last_name_and_email():
    user = User(
        firstName="Jane",
        lastName="Doe",
        email="jane@example.com",
    )

    assert user.firstName == "Jane"
    assert user.lastName == "Doe"
    assert user.email == "jane@example.com"
    assert not hasattr(user, "age")


def test_user_model_rejects_missing_last_name():
    with pytest.raises(ValidationError):
        User(firstName="Jane", email="jane@example.com")


@pytest.mark.asyncio
async def test_get_users_returns_serialized_users():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    users_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
            }
        ]
    )

    result = await users_route.get_users()

    assert result == [
        {
            "id": str(user_id),
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane@example.com",
        }
    ]


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email():
    users_route.users_collection = FakeUsersCollection(
        [{"email": "jane@example.com"}]
    )

    with pytest.raises(HTTPException) as error:
        await users_route.create_user(
            User(
                firstName="Jane",
                lastName="Doe",
                email="jane@example.com",
            )
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Email already exists"


@pytest.mark.asyncio
async def test_create_user_inserts_new_user():
    collection = FakeUsersCollection()
    users_route.users_collection = collection

    result = await users_route.create_user(
        User(
            firstName="Jane",
            lastName="Doe",
            email="jane@example.com",
        )
    )

    assert collection.inserted_document == {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane@example.com",
    }
    assert result["firstName"] == "Jane"
    assert result["lastName"] == "Doe"
    assert result["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_patch_user_rejects_empty_update():
    users_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await users_route.patch_user(
            "64f1f77bcf86cd7994390111",
            UpdateUser(),
        )

    assert error.value.status_code == 400
    assert error.value.detail == "No valid fields provided for update"


@pytest.mark.asyncio
async def test_delete_user_deletes_by_id():
    collection = FakeUsersCollection()
    user_id = "64f1f77bcf86cd7994390111"
    users_route.users_collection = collection

    result = await users_route.delete_user(user_id)

    assert collection.deleted_filter == {"_id": ObjectId(user_id)}
    assert result == {"message": "User deleted successfully"}
