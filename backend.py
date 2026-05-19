import argparse
import sqlite3
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI
from pydantic import BaseModel

app = FastAPI()

_conn: sqlite3.Connection | None = None


def init_db(db_path: str) -> sqlite3.Connection:
    pass


def get_db():
    pass


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
    pass


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
