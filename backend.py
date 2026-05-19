import argparse
import sqlite3
from datetime import datetime, timezone
from typing import Literal

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_conn = None

# initializes data base and creates table if it doesn't exist. table includes:
# id, timestamp, track_id, class_name, direction, confidence, and bounding box coordinates.
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


# dependency to get db connection for each request
def get_db():
    yield _conn


# command line argument parser
def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", type=str, default="vehicles.db")
    return parser.parse_args(argv)


# pydantic models for request validation
class BBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

# payload model for events
class EventPayload(BaseModel):
    timestamp: str
    track_id: int
    class_name: str
    direction: Literal["in", "out"]
    bbox: BBox
    confidence: float


# endpoint to receive events from detector
@app.post("/events", status_code=201)
def post_event(payload: EventPayload, db: sqlite3.Connection = Depends(get_db)):
    ts = datetime.fromisoformat(payload.timestamp).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = db.execute(
        """
        INSERT INTO crossings
            (timestamp, track_id, class_name, direction, confidence,
             bbox_x1, bbox_y1, bbox_x2, bbox_y2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
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

# endpoint to get current counts
@app.get("/counts/current")
def counts_current(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT direction, COUNT(*) as cnt FROM crossings GROUP BY direction"
    ).fetchall()
    totals = {"in": 0, "out": 0}
    for row in rows:
        totals[row["direction"]] = row["cnt"]
    return totals


# endpoint to get hourly counts 
@app.get("/counts/hourly")
def counts_hourly(date: str | None = None, db: sqlite3.Connection = Depends(get_db)):
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = db.execute(
        """
        SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
               direction,
               COUNT(*) as cnt
        FROM crossings
        WHERE date(timestamp) = ?
        GROUP BY hour, direction
        ORDER BY hour
        """,
        (date,),
    ).fetchall()
    by_hour: dict = {}
    for row in rows:
        h = row["hour"]
        if h not in by_hour:
            by_hour[h] = {"hour": h, "in": 0, "out": 0}
        by_hour[h][row["direction"]] = row["cnt"]
    return list(by_hour.values())

# endpoint to get daily counts
@app.get("/counts/daily")
def counts_daily(days: int = 7, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        """
        SELECT date(timestamp) as day,
               direction,
               COUNT(*) as cnt
        FROM crossings
        WHERE date(timestamp) >= date('now', '-' || ? || ' days')
        GROUP BY day, direction
        ORDER BY day
        """,
        (days - 1,),
    ).fetchall()
    by_day: dict = {}
    for row in rows:
        d = row["day"]
        if d not in by_day:
            by_day[d] = {"date": d, "in": 0, "out": 0}
        by_day[d][row["direction"]] = row["cnt"]
    return list(by_day.values())


# endpoint to get breakdown of counts by class and direction
@app.get("/counts/breakdown")
def counts_breakdown(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        """
        SELECT class_name, direction, COUNT(*) as count
        FROM crossings
        GROUP BY class_name, direction
        ORDER BY class_name, direction
        """
    ).fetchall()
    return [
        {"class_name": r["class_name"], "direction": r["direction"], "count": r["count"]}
        for r in rows
    ]


@app.get("/counts/hourly/breakdown")
def counts_hourly_breakdown(date: str | None = None, db: sqlite3.Connection = Depends(get_db)):
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = db.execute(
        """
        SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
               class_name,
               COUNT(*) as cnt
        FROM crossings
        WHERE date(timestamp) = ?
        GROUP BY hour, class_name
        ORDER BY class_name, hour
        """,
        (date,),
    ).fetchall()
    by_class: dict = {}
    for row in rows:
        cls = row["class_name"]
        if cls not in by_class:
            by_class[cls] = {}
        by_class[cls][row["hour"]] = row["cnt"]
    return [
        {"class_name": cls, "hourly": data}
        for cls, data in sorted(by_class.items())
    ]


if __name__ == "__main__":
    args = parse_args()
    _conn = init_db(args.db)
    uvicorn.run(app, host=args.host, port=args.port)
