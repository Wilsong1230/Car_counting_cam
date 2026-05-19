import argparse
import sqlite3
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI
from pydantic import BaseModel

app = FastAPI()

_conn: sqlite3.Connection | None = None


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crossings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT    NOT NULL,
            track_id   INTEGER NOT NULL,
            class_name TEXT    NOT NULL,
            direction  TEXT    NOT NULL,
            confidence REAL    NOT NULL,
            bbox_x1    INTEGER NOT NULL,
            bbox_y1    INTEGER NOT NULL,
            bbox_x2    INTEGER NOT NULL,
            bbox_y2    INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get_db():
    yield _conn


def parse_args(argv=None):
    pass


class BBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class EventPayload(BaseModel):
    timestamp: str
    track_id: int
    class_name: str
    direction: str
    bbox: BBox
    confidence: float


@app.post("/events", status_code=201)
def post_event(payload: EventPayload, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        """
        INSERT INTO crossings
            (timestamp, track_id, class_name, direction, confidence,
             bbox_x1, bbox_y1, bbox_x2, bbox_y2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.timestamp,
            payload.track_id,
            payload.class_name,
            payload.direction,
            payload.confidence,
            payload.bbox.x1,
            payload.bbox.y1,
            payload.bbox.x2,
            payload.bbox.y2,
        ),
    )
    db.commit()
    return {"id": cursor.lastrowid}


@app.get("/counts/current")
def counts_current(db: sqlite3.Connection = Depends(get_db)):
    pass


@app.get("/counts/hourly")
def counts_hourly(date: str | None = None, db: sqlite3.Connection = Depends(get_db)):
    pass


@app.get("/counts/daily")
def counts_daily(days: int = 7, db: sqlite3.Connection = Depends(get_db)):
    pass


@app.get("/counts/breakdown")
def counts_breakdown(db: sqlite3.Connection = Depends(get_db)):
    pass


if __name__ == "__main__":
    args = parse_args()
    globals()['_conn'] = init_db(args.db)
    uvicorn.run(app, host=args.host, port=args.port)
