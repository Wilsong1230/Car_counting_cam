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


def test_counts_hourly_groups_by_hour(client):
    hour14 = {**VALID_PAYLOAD, "timestamp": "2026-05-19T14:30:00.000000+00:00"}
    hour15 = {**VALID_PAYLOAD, "timestamp": "2026-05-19T15:10:00.000000+00:00"}
    client.post("/events", json=hour14)
    client.post("/events", json=hour14)
    client.post("/events", json=hour15)
    resp = client.get("/counts/hourly?date=2026-05-19")
    data = resp.json()
    assert resp.status_code == 200
    hours = {item["hour"]: item for item in data}
    assert hours["2026-05-19T14:00:00Z"]["in"] == 2
    assert hours["2026-05-19T15:00:00Z"]["in"] == 1


def test_counts_hourly_filters_by_date(client):
    may18 = {**VALID_PAYLOAD, "timestamp": "2026-05-18T10:00:00.000000+00:00"}
    may19 = {**VALID_PAYLOAD, "timestamp": "2026-05-19T10:00:00.000000+00:00"}
    client.post("/events", json=may18)
    client.post("/events", json=may19)
    resp = client.get("/counts/hourly?date=2026-05-19")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["hour"].startswith("2026-05-19")


def test_counts_daily_groups_by_date(client):
    may18 = {**VALID_PAYLOAD, "timestamp": "2026-05-18T10:00:00.000000+00:00"}
    may19 = {**VALID_PAYLOAD, "timestamp": "2026-05-19T10:00:00.000000+00:00"}
    client.post("/events", json=may18)
    client.post("/events", json=may18)
    client.post("/events", json=may19)
    resp = client.get("/counts/daily?days=30")
    assert resp.status_code == 200
    data = {item["date"]: item for item in resp.json()}
    assert data["2026-05-18"]["in"] == 2
    assert data["2026-05-19"]["in"] == 1


def test_counts_daily_respects_days_filter(client, mem_conn):
    old = {**VALID_PAYLOAD, "timestamp": "2020-01-01T10:00:00.000000+00:00"}
    recent = {**VALID_PAYLOAD, "timestamp": "2026-05-19T10:00:00.000000+00:00"}
    client.post("/events", json=old)
    client.post("/events", json=recent)
    resp = client.get("/counts/daily?days=7")
    dates = [item["date"] for item in resp.json()]
    assert "2020-01-01" not in dates


def test_counts_breakdown_groups_by_class_and_direction(client):
    car_in = {**VALID_PAYLOAD, "class_name": "car", "direction": "in"}
    car_out = {**VALID_PAYLOAD, "class_name": "car", "direction": "out"}
    truck_in = {**VALID_PAYLOAD, "class_name": "truck", "direction": "in"}
    client.post("/events", json=car_in)
    client.post("/events", json=car_in)
    client.post("/events", json=car_out)
    client.post("/events", json=truck_in)
    resp = client.get("/counts/breakdown")
    assert resp.status_code == 200
    data = {(r["class_name"], r["direction"]): r["count"] for r in resp.json()}
    assert data[("car", "in")] == 2
    assert data[("car", "out")] == 1
    assert data[("truck", "in")] == 1


def test_counts_breakdown_empty(client):
    resp = client.get("/counts/breakdown")
    assert resp.status_code == 200
    assert resp.json() == []


def test_parse_args_defaults():
    args = parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 8000
    assert args.db == "vehicles.db"


def test_parse_args_custom():
    args = parse_args(["--host", "127.0.0.1", "--port", "9000", "--db", "custom.db"])
    assert args.host == "127.0.0.1"
    assert args.port == 9000
    assert args.db == "custom.db"
