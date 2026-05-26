from types import SimpleNamespace

import pytest

from seeders import users_seeder
from app.security import verify_password


class FakeUsersCollection:
    def __init__(self):
        self.deleted_query = None
        self.inserted_documents = None
        self.updated_query = None
        self.updated_data = None
        self.update_upsert = None

    async def delete_many(self, query):
        self.deleted_query = query

    async def insert_many(self, documents):
        self.inserted_documents = list(documents)
        return SimpleNamespace(inserted_ids=list(range(len(documents))))

    async def update_one(self, query, update, upsert=False):
        self.updated_query = query
        self.updated_data = update
        self.update_upsert = upsert
        return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=None)


class FakeClient:
    def __init__(self, collection):
        self.collection = collection
        self.closed = False

    def __getitem__(self, _name):
        return {"users": self.collection}

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_seed_users_upserts_admin_from_environment(monkeypatch):
    collection = FakeUsersCollection()
    client = FakeClient(collection)
    monkeypatch.setattr(users_seeder, "AsyncIOMotorClient", lambda _uri: client)
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "EnvPassword123456!")

    await users_seeder.seed_users()

    assert collection.updated_query == {"email": "admin@example.com"}
    assert collection.update_upsert is True
    admin_data = collection.updated_data["$set"]
    assert admin_data["email"] == "admin@example.com"
    assert admin_data["role"] == "admin"
    assert admin_data["status"] == "active"
    assert verify_password("EnvPassword123456!", admin_data["passwordHash"])
