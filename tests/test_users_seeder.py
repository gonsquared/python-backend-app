from types import SimpleNamespace
import runpy
import sys
from pathlib import Path

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
        self.updates = []

    async def delete_many(self, query):
        self.deleted_query = query

    async def insert_many(self, documents):
        self.inserted_documents = list(documents)
        return SimpleNamespace(inserted_ids=list(range(len(documents))))

    async def update_one(self, query, update, upsert=False):
        self.updated_query = query
        self.updated_data = update
        self.update_upsert = upsert
        self.updates.append({"query": query, "update": update, "upsert": upsert})
        return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=None)


class FakeClient:
    def __init__(self, collection):
        self.collection = collection
        self.closed = False

    def __getitem__(self, _name):
        return {"users": self.collection}

    def close(self):
        self.closed = True


def test_users_seeder_imports_when_run_as_script(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    seeder_path = project_root / "seeders" / "users_seeder.py"
    seeders_path = str(project_root / "seeders")
    original_path = list(sys.path)
    simulated_script_path = [
        path for path in original_path if Path(path or ".").resolve() != project_root
    ]
    simulated_script_path.insert(0, seeders_path)
    monkeypatch.setattr(sys, "path", simulated_script_path)
    monkeypatch.delitem(sys.modules, "app", raising=False)
    monkeypatch.delitem(sys.modules, "app.security", raising=False)

    runpy.run_path(str(seeder_path), run_name="users_seeder_script_import")


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
    assert admin_data["permissions"] == [
        "manage_users",
        "manage_own",
        "manage_notes",
        "manage_own_notes",
    ]
    assert verify_password("EnvPassword123456!", admin_data["passwordHash"])


@pytest.mark.asyncio
async def test_seed_users_does_not_delete_or_bulk_insert_users(monkeypatch):
    collection = FakeUsersCollection()
    client = FakeClient(collection)
    monkeypatch.setattr(users_seeder, "AsyncIOMotorClient", lambda _uri: client)
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "EnvPassword123456!")

    await users_seeder.seed_users()

    assert collection.deleted_query is None
    assert collection.inserted_documents is None


@pytest.mark.asyncio
async def test_seed_users_only_creates_sample_users_when_missing(monkeypatch):
    collection = FakeUsersCollection()
    client = FakeClient(collection)
    monkeypatch.setattr(users_seeder, "AsyncIOMotorClient", lambda _uri: client)
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "EnvPassword123456!")

    await users_seeder.seed_users()

    sample_updates = collection.updates[: len(users_seeder.sample_users)]
    assert len(sample_updates) == len(users_seeder.sample_users)
    for sample_user, update in zip(users_seeder.sample_users, sample_updates):
        assert update["query"] == {"email": sample_user["email"]}
        assert update["update"] == {"$setOnInsert": sample_user}
        assert update["upsert"] is True


@pytest.mark.asyncio
async def test_seed_users_uses_dotenv_values_when_environment_is_blank(monkeypatch):
    collection = FakeUsersCollection()
    client = FakeClient(collection)
    monkeypatch.setattr(users_seeder, "AsyncIOMotorClient", lambda _uri: client)
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    monkeypatch.setattr(
        users_seeder,
        "dotenv_values",
        lambda: {
            "ADMIN_EMAIL": "dotenv-admin@example.com",
            "ADMIN_PASSWORD": "DotenvPassword123456!",
        },
    )

    await users_seeder.seed_users()

    assert collection.updated_query == {"email": "dotenv-admin@example.com"}
    admin_data = collection.updated_data["$set"]
    assert admin_data["email"] == "dotenv-admin@example.com"
    assert verify_password("DotenvPassword123456!", admin_data["passwordHash"])
