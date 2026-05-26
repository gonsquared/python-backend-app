from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import get_settings
from app.models.user_model import UpdateUser, User
from app.models.user_model import UpdateAvatar
from app.middlewares.validate_email import validate_email
from app.routes import users as users_route
from app.security import verify_password


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.skip_value = 0
        self.limit_value = None

    def skip(self, value):
        self.skip_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    async def to_list(self, _limit):
        limit = self.limit_value or _limit
        return self.documents[self.skip_value : self.skip_value + limit]


class FakeUsersCollection:
    def __init__(self, documents=None):
        self.documents = list(documents or [])
        self.inserted_document = None
        self.inserted_payload = None
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

    def find(self, query=None):
        if not query:
            return FakeCursor(self.documents)

        return FakeCursor(
            [
                document
                for document in self.documents
                if all(document.get(key) == value for key, value in query.items())
            ]
        )

    async def insert_one(self, document):
        self.inserted_payload = document.copy()
        self.inserted_document = document
        document["_id"] = ObjectId("64f1f77bcf86cd7994390111")
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
    assert user.status == "inactive"
    assert user.role == "user"
    assert not hasattr(user, "age")


def test_update_avatar_accepts_image_data_url():
    avatar = UpdateAvatar(avatarUrl="data:image/png;base64,ZmFrZS1pbWFnZQ==")

    assert avatar.avatarUrl == "data:image/png;base64,ZmFrZS1pbWFnZQ=="


def test_update_avatar_rejects_non_image_data_url():
    with pytest.raises(ValidationError):
        UpdateAvatar(avatarUrl="data:text/plain;base64,SGVsbG8=")


def test_user_model_rejects_missing_last_name():
    with pytest.raises(ValidationError):
        User(firstName="Jane", email="jane@example.com")


def test_cors_allows_docker_frontend_origin():
    settings = get_settings()

    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins


def test_settings_parse_cors_origins_from_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://app.example.com, http://localhost:5173 ,,https://admin.example.com",
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()

    assert settings.cors_origins == [
        "https://app.example.com",
        "http://localhost:5173",
        "https://admin.example.com",
    ]


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
                "status": "active",
                "role": "admin",
                "avatarUrl": "data:image/png;base64,ZmFrZS1pbWFnZQ==",
            }
        ]
    )

    result = await users_route.get_users(
        current_user={"_id": user_id, "role": "admin", "status": "active"}
    )

    assert result == [
        {
            "id": str(user_id),
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane@example.com",
            "status": "active",
            "role": "admin",
            "permissions": [
                "manage_users",
                "manage_own",
                "manage_notes",
                "manage_own_notes",
            ],
            "avatarUrl": "data:image/png;base64,ZmFrZS1pbWFnZQ==",
        }
    ]


@pytest.mark.asyncio
async def test_user_can_update_their_avatar():
    user_id = "64f1f77bcf86cd7994390111"
    object_id = ObjectId(user_id)
    collection = FakeUsersCollection(
        [
            {
                "_id": object_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "status": "active",
                "role": "user",
            }
        ]
    )
    users_route.users_collection = collection

    result = await users_route.update_user_avatar(
        user_id,
        UpdateAvatar(avatarUrl="data:image/png;base64,ZmFrZS1pbWFnZQ=="),
        current_user={"_id": object_id, "role": "user", "status": "active"},
    )

    assert collection.updated_data == {
        "$set": {"avatarUrl": "data:image/png;base64,ZmFrZS1pbWFnZQ=="}
    }
    assert result["avatarUrl"] == "data:image/png;base64,ZmFrZS1pbWFnZQ=="


@pytest.mark.asyncio
async def test_regular_user_cannot_update_another_users_avatar():
    user_id = "64f1f77bcf86cd7994390111"
    other_user_id = "64f1f77bcf86cd7994390112"
    users_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await users_route.update_user_avatar(
            other_user_id,
            UpdateAvatar(avatarUrl="data:image/png;base64,ZmFrZS1pbWFnZQ=="),
            current_user={
                "_id": ObjectId(user_id),
                "role": "user",
                "status": "active",
            },
        )

    assert error.value.status_code == 403
    assert error.value.detail == "You can only manage your own data"


@pytest.mark.asyncio
async def test_regular_user_only_lists_their_own_user():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    other_user_id = ObjectId("64f1f77bcf86cd7994390112")
    users_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "status": "active",
                "role": "user",
            },
            {
                "_id": other_user_id,
                "firstName": "Ada",
                "lastName": "Lovelace",
                "email": "ada@example.com",
                "status": "active",
                "role": "user",
            },
        ]
    )

    result = await users_route.get_users(
        current_user={"_id": user_id, "role": "user", "status": "active"}
    )

    assert [user["id"] for user in result] == [str(user_id)]


@pytest.mark.asyncio
async def test_get_users_applies_skip_and_limit():
    user_ids = [
        ObjectId("64f1f77bcf86cd7994390111"),
        ObjectId("64f1f77bcf86cd7994390112"),
        ObjectId("64f1f77bcf86cd7994390113"),
    ]
    users_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": user_id,
                "firstName": f"User{index}",
                "lastName": "Example",
                "email": f"user{index}@example.com",
                "status": "active",
                "role": "user",
            }
            for index, user_id in enumerate(user_ids)
        ]
    )

    result = await users_route.get_users(
        limit=1,
        skip=1,
        current_user={"_id": user_ids[0], "role": "admin", "status": "active"},
    )

    assert [user["id"] for user in result] == [str(user_ids[1])]


def test_user_routes_do_not_use_email_body_middleware():
    route_dependencies = [
        dependency.call
        for route in users_route.router.routes
        for dependency in getattr(route, "dependencies", [])
    ]

    assert validate_email not in route_dependencies


@pytest.mark.asyncio
async def test_regular_user_cannot_create_users():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    users_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await users_route.create_user(
            User(firstName="Ada", lastName="Lovelace", email="ada@example.com"),
            current_user={"_id": user_id, "role": "user", "status": "active"},
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Manage users permission is required"


@pytest.mark.asyncio
async def test_regular_user_cannot_update_another_user():
    user_id = "64f1f77bcf86cd7994390111"
    other_user_id = "64f1f77bcf86cd7994390112"
    users_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": ObjectId(other_user_id),
                "firstName": "Ada",
                "lastName": "Lovelace",
                "email": "ada@example.com",
                "status": "active",
                "role": "user",
            }
        ]
    )

    with pytest.raises(HTTPException) as error:
        await users_route.patch_user(
            other_user_id,
            UpdateUser(firstName="Updated"),
            current_user={"_id": ObjectId(user_id), "role": "user", "status": "active"},
        )

    assert error.value.status_code == 403
    assert error.value.detail == "You can only manage your own data"


@pytest.mark.asyncio
async def test_regular_user_cannot_change_their_role_or_status():
    user_id = "64f1f77bcf86cd7994390111"
    object_id = ObjectId(user_id)
    collection = FakeUsersCollection(
        [
            {
                "_id": object_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "status": "active",
                "role": "user",
            }
        ]
    )
    users_route.users_collection = collection

    await users_route.patch_user(
        user_id,
        UpdateUser(firstName="Janet", status="archived", role="admin"),
        current_user={"_id": object_id, "role": "user", "status": "active"},
    )

    assert collection.updated_data == {"$set": {"firstName": "Janet"}}


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
            ),
            current_user={
                "_id": ObjectId("64f1f77bcf86cd7994390111"),
                "role": "admin",
                "status": "active",
            },
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
        ),
        current_user={
            "_id": ObjectId("64f1f77bcf86cd7994390111"),
            "role": "admin",
            "status": "active",
        },
    )

    assert collection.inserted_payload == {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane@example.com",
        "status": "inactive",
        "role": "user",
        "createdBy": "64f1f77bcf86cd7994390111",
    }
    assert result["firstName"] == "Jane"
    assert result["lastName"] == "Doe"
    assert result["email"] == "jane@example.com"
    assert result["status"] == "inactive"
    assert "_id" not in result


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_does_not_return_password_data():
    collection = FakeUsersCollection()
    users_route.users_collection = collection

    result = await users_route.create_user(
        User(
            firstName="Jane",
            lastName="Doe",
            email="jane@example.com",
            password="VeryStrongPassword123!",
        ),
        current_user={
            "_id": ObjectId("64f1f77bcf86cd7994390111"),
            "role": "admin",
            "status": "active",
        },
    )

    assert collection.inserted_payload["passwordHash"] != "VeryStrongPassword123!"
    assert collection.inserted_payload["passwordHash"].startswith("$argon2")
    assert verify_password(
        "VeryStrongPassword123!",
        collection.inserted_payload["passwordHash"],
    )
    assert "password" not in result
    assert "passwordHash" not in result


@pytest.mark.asyncio
async def test_update_user_rejects_email_used_by_another_user():
    user_id = "64f1f77bcf86cd7994390111"
    other_user_id = ObjectId("64f1f77bcf86cd7994390112")
    users_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": other_user_id,
                "firstName": "Ada",
                "lastName": "Lovelace",
                "email": "ada@example.com",
            }
        ]
    )

    with pytest.raises(HTTPException) as error:
        await users_route.update_user(
            user_id,
            User(
                firstName="Jane",
                lastName="Doe",
                email="ada@example.com",
            ),
            current_user={
                "_id": ObjectId("64f1f77bcf86cd7994390113"),
                "role": "admin",
                "status": "active",
            },
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Email already exists"


@pytest.mark.asyncio
async def test_update_user_allows_existing_email_for_same_user():
    user_id = "64f1f77bcf86cd7994390111"
    object_id = ObjectId(user_id)
    collection = FakeUsersCollection(
        [
            {
                "_id": object_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
            }
        ]
    )
    users_route.users_collection = collection

    result = await users_route.update_user(
        user_id,
        User(
            firstName="Jane",
            lastName="Updated",
            email="jane@example.com",
        ),
        current_user={
            "_id": ObjectId("64f1f77bcf86cd7994390113"),
            "role": "admin",
            "status": "active",
        },
    )

    assert collection.updated_filter == {"_id": object_id}
    assert result["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_update_user_does_not_reset_status_when_status_is_omitted():
    user_id = "64f1f77bcf86cd7994390111"
    object_id = ObjectId(user_id)
    collection = FakeUsersCollection(
        [
            {
                "_id": object_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "status": "active",
            }
        ]
    )
    users_route.users_collection = collection

    await users_route.update_user(
        user_id,
        User(
            firstName="Jane",
            lastName="Updated",
            email="jane@example.com",
        ),
        current_user={
            "_id": ObjectId("64f1f77bcf86cd7994390113"),
            "role": "admin",
            "status": "active",
        },
    )

    assert "status" not in collection.updated_data["$set"]


@pytest.mark.asyncio
async def test_patch_user_rejects_email_used_by_another_user():
    user_id = "64f1f77bcf86cd7994390111"
    other_user_id = ObjectId("64f1f77bcf86cd7994390112")
    users_route.users_collection = FakeUsersCollection(
        [
            {
                "_id": other_user_id,
                "firstName": "Ada",
                "lastName": "Lovelace",
                "email": "ada@example.com",
            }
        ]
    )

    with pytest.raises(HTTPException) as error:
        await users_route.patch_user(
            user_id,
            UpdateUser(email="ada@example.com"),
            current_user={
                "_id": ObjectId("64f1f77bcf86cd7994390113"),
                "role": "admin",
                "status": "active",
            },
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Email already exists"


@pytest.mark.asyncio
async def test_patch_user_allows_existing_email_for_same_user():
    user_id = "64f1f77bcf86cd7994390111"
    object_id = ObjectId(user_id)
    collection = FakeUsersCollection(
        [
            {
                "_id": object_id,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
            }
        ]
    )
    users_route.users_collection = collection

    result = await users_route.patch_user(
        user_id,
        UpdateUser(email="jane@example.com"),
        current_user={
            "_id": ObjectId("64f1f77bcf86cd7994390113"),
            "role": "admin",
            "status": "active",
        },
    )

    assert collection.updated_filter == {"_id": object_id}
    assert result["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_patch_user_rejects_empty_update():
    users_route.users_collection = FakeUsersCollection()

    with pytest.raises(HTTPException) as error:
        await users_route.patch_user(
            "64f1f77bcf86cd7994390111",
            UpdateUser(),
            current_user={
                "_id": ObjectId("64f1f77bcf86cd7994390113"),
                "role": "admin",
                "status": "active",
            },
        )

    assert error.value.status_code == 400
    assert error.value.detail == "No valid fields provided for update"


@pytest.mark.asyncio
async def test_delete_user_deletes_by_id():
    collection = FakeUsersCollection()
    user_id = "64f1f77bcf86cd7994390111"
    users_route.users_collection = collection

    result = await users_route.delete_user(
        user_id,
        current_user={
            "_id": ObjectId("64f1f77bcf86cd7994390113"),
            "role": "admin",
            "status": "active",
        },
    )

    assert collection.deleted_filter == {"_id": ObjectId(user_id)}
    assert result == {"message": "User deleted successfully"}
