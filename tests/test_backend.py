import sys
import sqlite3
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, ".")
from backend import app, get_db, init_db, parse_args


def test_init_db_creates_crossings_table():
    conn = init_db(":memory:")
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='crossings'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_init_db_has_correct_columns():
    conn = init_db(":memory:")
    cursor = conn.execute("PRAGMA table_info(crossings)")
    cols = {row[1] for row in cursor.fetchall()}
    assert cols == {
        "id", "timestamp", "track_id", "class_name", "direction",
        "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
    }
    conn.close()


@pytest.fixture
def mem_conn():
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def client(mem_conn):
    def override():
        yield mem_conn

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


VALID_PAYLOAD = {
    "timestamp": "2026-05-19T14:23:01.123456+00:00",
    "track_id": 42,
    "class_name": "car",
    "direction": "in",
    "bbox": {"x1": 10, "y1": 20, "x2": 30, "y2": 40},
    "confidence": 0.8765,
}


def test_post_event_returns_201_with_id(client):
    resp = client.post("/events", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    assert resp.json()["id"] == 1


def test_post_event_sequential_ids(client):
    r1 = client.post("/events", json=VALID_PAYLOAD)
    r2 = client.post("/events", json=VALID_PAYLOAD)
    assert r2.json()["id"] == r1.json()["id"] + 1


def test_post_event_missing_field_returns_422(client):
    resp = client.post("/events", json={"track_id": 1})
    assert resp.status_code == 422


def test_counts_current_empty(client):
    resp = client.get("/counts/current")
    assert resp.status_code == 200
    assert resp.json() == {"in": 0, "out": 0}


def test_counts_current_with_data(client):
    for _ in range(3):
        client.post("/events", json=VALID_PAYLOAD)
    out_payload = {**VALID_PAYLOAD, "direction": "out"}
    for _ in range(2):
        client.post("/events", json=out_payload)
    resp = client.get("/counts/current")
    assert resp.json() == {"in": 3, "out": 2}
