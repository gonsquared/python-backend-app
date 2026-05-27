from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.routes import labels as labels_route


class FakeNotesCollection:
    def __init__(self, distinct_result=None):
        self.distinct_result = distinct_result or []
        self.last_field = None
        self.last_filter = None

    async def distinct(self, field, filter_query):
        self.last_field = field
        self.last_filter = filter_query
        return self.distinct_result


@pytest.mark.asyncio
async def test_get_labels_returns_sorted_distinct_labels():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    labels_route.notes_collection = FakeNotesCollection(["work", "personal", "ideas"])

    result = await labels_route.get_labels(
        current_user={"_id": user_id, "role": "user", "status": "active"}
    )

    assert result == ["ideas", "personal", "work"]
    assert labels_route.notes_collection.last_field == "labels"
    assert labels_route.notes_collection.last_filter == {"user": str(user_id)}


@pytest.mark.asyncio
async def test_get_labels_returns_empty_list_when_no_labels():
    user_id = ObjectId("64f1f77bcf86cd7994390111")
    labels_route.notes_collection = FakeNotesCollection([])

    result = await labels_route.get_labels(
        current_user={"_id": user_id, "role": "user", "status": "active"}
    )

    assert result == []
