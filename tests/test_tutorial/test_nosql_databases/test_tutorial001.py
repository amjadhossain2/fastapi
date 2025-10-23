import importlib
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from tests.utils import needs_py39, needs_py310


@pytest.fixture(
    name="client",
    params=[
        "tutorial001",
        pytest.param("tutorial001_an_py39", marks=needs_py39),
        pytest.param("tutorial001_an_py310", marks=needs_py310),
    ],
)
def get_client(request: pytest.FixtureRequest):
    # Mock MongoDB collection
    mock_collection = MagicMock()
    mock_database = MagicMock()
    mock_client = MagicMock()

    # Setup mock return values
    mock_database.__getitem__ = MagicMock(return_value=mock_collection)
    mock_client.__getitem__ = MagicMock(return_value=mock_database)

    # Store documents in memory for testing
    documents = {}

    async def mock_insert_one(doc):
        doc_id = ObjectId()
        documents[doc_id] = {**doc, "_id": doc_id}
        result = MagicMock()
        result.inserted_id = doc_id
        return result

    async def mock_find_one(query):
        doc_id = query.get("_id")
        return documents.get(doc_id)

    async def mock_update_one(query, update):
        doc_id = query.get("_id")
        if doc_id in documents:
            documents[doc_id].update(update.get("$set", {}))
            result = MagicMock()
            result.matched_count = 1
            return result
        result = MagicMock()
        result.matched_count = 0
        return result

    async def mock_delete_one(query):
        doc_id = query.get("_id")
        result = MagicMock()
        if doc_id in documents:
            del documents[doc_id]
            result.deleted_count = 1
        else:
            result.deleted_count = 0
        return result

    class MockCursor:
        def __init__(self, docs):
            self.docs = list(docs)
            self.skip_count = 0
            self.limit_count = None

        def skip(self, count):
            self.skip_count = count
            return self

        def limit(self, count):
            self.limit_count = count
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            docs = self.docs[self.skip_count:]
            if self.limit_count is not None:
                docs = docs[:self.limit_count]

            if not hasattr(self, '_index'):
                self._index = 0

            if self._index < len(docs):
                doc = docs[self._index]
                self._index += 1
                return doc
            else:
                raise StopAsyncIteration

    def mock_find():
        return MockCursor(documents.values())

    # Assign mock methods
    mock_collection.insert_one = mock_insert_one
    mock_collection.find_one = mock_find_one
    mock_collection.update_one = mock_update_one
    mock_collection.delete_one = mock_delete_one
    mock_collection.find = mock_find

    with patch("motor.motor_asyncio.AsyncIOMotorClient") as mock_motor_client:
        mock_motor_client.return_value = mock_client

        mod = importlib.import_module(f"docs_src.nosql_databases.{request.param}")

        # Override get_collection to return our mock
        def patched_get_collection():
            return mock_collection

        mod.get_collection = patched_get_collection

        with TestClient(mod.app) as c:
            yield c


def test_create_hero(client: TestClient):
    response = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson", "age": 30},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Deadpond"
    assert data["secret_name"] == "Dive Wilson"
    assert data["age"] == 30
    assert "_id" in data


def test_create_hero_incomplete(client: TestClient):
    response = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Deadpond"
    assert data["secret_name"] == "Dive Wilson"
    assert data["age"] is None


def test_create_hero_invalid(client: TestClient):
    response = client.post(
        "/heroes/",
        json={"name": "Deadpond"},
    )
    assert response.status_code == 422


def test_read_heroes(client: TestClient):
    # Create some heroes first
    client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson", "age": 30},
    )
    client.post(
        "/heroes/",
        json={"name": "Spider-Boy", "secret_name": "Pedro Parqueador", "age": 25},
    )

    response = client.get("/heroes/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) >= 2


def test_read_heroes_with_pagination(client: TestClient):
    # Create heroes
    for i in range(5):
        client.post(
            "/heroes/",
            json={"name": f"Hero{i}", "secret_name": f"Secret{i}", "age": 20 + i},
        )

    # Test with limit
    response = client.get("/heroes/?limit=2")

    assert response.status_code == 200


def test_read_hero(client: TestClient):
    # Create a hero first
    create_response = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson", "age": 30},
    )
    hero_id = create_response.json()["_id"]

    # Read the hero
    response = client.get(f"/heroes/{hero_id}")
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Deadpond"
    assert data["_id"] == hero_id


def test_read_hero_not_found(client: TestClient):
    # Use a valid ObjectId format
    fake_id = str(ObjectId())
    response = client.get(f"/heroes/{fake_id}")
    assert response.status_code == 404


def test_read_hero_invalid_id(client: TestClient):
    response = client.get("/heroes/invalid-id")
    assert response.status_code == 400


def test_update_hero(client: TestClient):
    # Create a hero first
    create_response = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson", "age": 30},
    )
    hero_id = create_response.json()["_id"]

    # Update the hero
    response = client.patch(
        f"/heroes/{hero_id}",
        json={"name": "Deadpond Updated", "age": 31},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Deadpond Updated"
    assert data["age"] == 31


def test_update_hero_not_found(client: TestClient):
    fake_id = str(ObjectId())
    response = client.patch(
        f"/heroes/{fake_id}",
        json={"name": "Updated"},
    )
    assert response.status_code == 404


def test_update_hero_invalid_id(client: TestClient):
    response = client.patch(
        "/heroes/invalid-id",
        json={"name": "Updated"},
    )
    assert response.status_code == 400


def test_delete_hero(client: TestClient):
    # Create a hero first
    create_response = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson", "age": 30},
    )
    hero_id = create_response.json()["_id"]

    # Delete the hero
    response = client.delete(f"/heroes/{hero_id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify hero is deleted
    get_response = client.get(f"/heroes/{hero_id}")
    assert get_response.status_code == 404


def test_delete_hero_not_found(client: TestClient):
    fake_id = str(ObjectId())
    response = client.delete(f"/heroes/{fake_id}")
    assert response.status_code == 404


def test_delete_hero_invalid_id(client: TestClient):
    response = client.delete("/heroes/invalid-id")
    assert response.status_code == 400
