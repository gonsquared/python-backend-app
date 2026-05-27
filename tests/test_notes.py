from datetime import datetime
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.note_model import Note, UpdateNote
from app.routes import notes as notes_route


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


class FakeNotesCollection:
    def __init__(self, documents=None):
        self.documents = list(documents or [])
        self.inserted_payload = None
        self.updated_filter = None
        self.updated_data = None
        self.deleted_filter = None
        self.matched_count = 1
        self.deleted_count = 1

    async def find_one(self, query):
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

    def find(self, query=None, projection=None):
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
        document["_id"] = ObjectId("64f1f77bcf86cd7994390222")
        return SimpleNamespace(inserted_id=ObjectId("64f1f77bcf86cd7994390222"))

    async def update_one(self, query, update):
        self.updated_filter = query
        self.updated_data = update
        return SimpleNamespace(matched_count=self.matched_count)

    async def delete_one(self, query):
        self.deleted_filter = query
        return SimpleNamespace(deleted_count=self.deleted_count)


@pytest.fixture(autouse=True)
def restore_collections():
    original_notes = notes_route.notes_collection
    original_users = notes_route.users_collection
    yield
    notes_route.notes_collection = original_notes
    notes_route.users_collection = original_users


def test_note_model_defaults_to_not_published():
    note = Note(title="Draft", contents="A first note")

    assert note.title == "Draft"
    assert note.contents == "A first note"
    assert note.status == "not published"


def test_note_model_rejects_invalid_status():
    with pytest.raises(ValidationError):
        Note(title="Draft", contents="A first note", status="private")


@pytest.mark.asyncio
async def test_create_note_sets_creator_and_timestamps():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    collection = FakeNotesCollection()
    notes_route.notes_collection = collection

    result = await notes_route.create_note(
        Note(title="Launch notes", contents="Ship it"),
        current_user={"_id": user_id, "role": "user", "status": "active"},
    )

    assert result["id"] == "64f1f77bcf86cd7994390222"
    assert result["title"] == "Launch notes"
    assert result["contents"] == "Ship it"
    assert result["status"] == "not published"
    assert result["user"] == str(user_id)
    assert isinstance(collection.inserted_payload["createdAt"], datetime)
    assert isinstance(collection.inserted_payload["updatedAt"], datetime)


@pytest.mark.asyncio
async def test_admin_lists_all_notes():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.users_collection = FakeNotesCollection([])
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "One",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            },
            {
                "_id": ObjectId("64f1f77bcf86cd7994390223"),
                "title": "Two",
                "contents": "Other",
                "status": "archived",
                "user": str(other_id),
            },
        ]
    )

    result = await notes_route.get_notes(
        current_user={"_id": owner_id, "role": "admin", "status": "active"}
    )

    assert [note["title"] for note in result] == ["One", "Two"]


@pytest.mark.asyncio
async def test_user_with_manage_notes_permission_lists_all_notes():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.users_collection = FakeNotesCollection([])
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Mine",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            },
            {
                "_id": ObjectId("64f1f77bcf86cd7994390223"),
                "title": "Theirs",
                "contents": "Other",
                "status": "published",
                "user": str(other_id),
            },
        ]
    )

    result = await notes_route.get_notes(
        current_user={
            "_id": owner_id,
            "role": "user",
            "status": "active",
            "permissions": ["manage_notes"],
        }
    )

    assert [note["title"] for note in result] == ["Mine", "Theirs"]


@pytest.mark.asyncio
async def test_regular_user_lists_only_their_notes():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.users_collection = FakeNotesCollection([])
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Mine",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            },
            {
                "_id": ObjectId("64f1f77bcf86cd7994390223"),
                "title": "Theirs",
                "contents": "Other",
                "status": "published",
                "user": str(other_id),
            },
        ]
    )

    result = await notes_route.get_notes(
        current_user={"_id": owner_id, "role": "user", "status": "active"}
    )

    assert [note["title"] for note in result] == ["Mine"]


@pytest.mark.asyncio
async def test_get_notes_applies_skip_and_limit():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    notes_route.users_collection = FakeNotesCollection([])
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "One",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            },
            {
                "_id": ObjectId("64f1f77bcf86cd7994390223"),
                "title": "Two",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            },
        ]
    )

    result = await notes_route.get_notes(
        limit=1,
        skip=1,
        current_user={"_id": owner_id, "role": "user", "status": "active"},
    )

    assert [note["title"] for note in result] == ["Two"]


@pytest.mark.asyncio
async def test_user_without_manage_own_notes_cannot_list_notes():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    notes_route.notes_collection = FakeNotesCollection()

    with pytest.raises(HTTPException) as error:
        await notes_route.get_notes(
            current_user={
                "_id": owner_id,
                "role": "guest",
                "status": "active",
                "permissions": [],
            }
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Manage own notes permission is required"


@pytest.mark.asyncio
async def test_admin_gets_notes_by_user():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Mine",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            },
            {
                "_id": ObjectId("64f1f77bcf86cd7994390223"),
                "title": "Theirs",
                "contents": "Other",
                "status": "published",
                "user": str(other_id),
            },
        ]
    )

    result = await notes_route.get_notes_by_user(
        str(other_id),
        current_user={"_id": owner_id, "role": "admin", "status": "active"},
    )

    assert [note["title"] for note in result] == ["Theirs"]


@pytest.mark.asyncio
async def test_user_with_manage_notes_permission_gets_notes_by_user():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Theirs",
                "contents": "Other",
                "status": "published",
                "user": str(other_id),
            }
        ]
    )

    result = await notes_route.get_notes_by_user(
        str(other_id),
        current_user={
            "_id": owner_id,
            "role": "user",
            "status": "active",
            "permissions": ["manage_notes"],
        },
    )

    assert [note["title"] for note in result] == ["Theirs"]


@pytest.mark.asyncio
async def test_regular_user_gets_their_notes_by_user():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Mine",
                "contents": "Owned",
                "status": "published",
                "user": str(owner_id),
            }
        ]
    )

    result = await notes_route.get_notes_by_user(
        str(owner_id),
        current_user={"_id": owner_id, "role": "user", "status": "active"},
    )

    assert [note["title"] for note in result] == ["Mine"]


@pytest.mark.asyncio
async def test_regular_user_cannot_get_another_users_notes_by_user():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.notes_collection = FakeNotesCollection()

    with pytest.raises(HTTPException) as error:
        await notes_route.get_notes_by_user(
            str(other_id),
            current_user={"_id": owner_id, "role": "user", "status": "active"},
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_user_without_manage_own_notes_cannot_get_their_notes_by_user():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    notes_route.notes_collection = FakeNotesCollection()

    with pytest.raises(HTTPException) as error:
        await notes_route.get_notes_by_user(
            str(owner_id),
            current_user={
                "_id": owner_id,
                "role": "guest",
                "status": "active",
                "permissions": [],
            },
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Manage own notes permission is required"


@pytest.mark.asyncio
async def test_get_notes_by_user_rejects_invalid_user_id():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")

    with pytest.raises(HTTPException) as error:
        await notes_route.get_notes_by_user(
            "not-an-object-id",
            current_user={"_id": owner_id, "role": "admin", "status": "active"},
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid user ID format"


@pytest.mark.asyncio
async def test_regular_user_cannot_read_someone_elses_note():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    other_id = ObjectId("64f1f77bcf86cd7994390112")
    notes_route.notes_collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Private",
                "contents": "Nope",
                "status": "published",
                "user": str(other_id),
            }
        ]
    )

    with pytest.raises(HTTPException) as error:
        await notes_route.get_note_by_id(
            "64f1f77bcf86cd7994390222",
            current_user={"_id": owner_id, "role": "user", "status": "active"},
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_user_without_manage_own_notes_cannot_create_note():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    notes_route.notes_collection = FakeNotesCollection()

    with pytest.raises(HTTPException) as error:
        await notes_route.create_note(
            Note(title="Draft", contents="No access"),
            current_user={
                "_id": owner_id,
                "role": "guest",
                "status": "active",
                "permissions": [],
            },
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Manage own notes permission is required"


@pytest.mark.asyncio
async def test_update_note_refreshes_updated_at():
    owner_id = ObjectId("64f1f77bcf86cd7994390111")
    collection = FakeNotesCollection(
        [
            {
                "_id": ObjectId("64f1f77bcf86cd7994390222"),
                "title": "Old",
                "contents": "Old contents",
                "status": "not published",
                "user": str(owner_id),
            }
        ]
    )
    notes_route.notes_collection = collection

    await notes_route.update_note(
        "64f1f77bcf86cd7994390222",
        UpdateNote(title="New", status="published"),
        current_user={"_id": owner_id, "role": "user", "status": "active"},
    )

    assert collection.updated_filter == {
        "_id": ObjectId("64f1f77bcf86cd7994390222")
    }
    assert collection.updated_data["$set"]["title"] == "New"
    assert collection.updated_data["$set"]["status"] == "published"
    assert isinstance(collection.updated_data["$set"]["updatedAt"], datetime)
