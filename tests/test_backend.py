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
