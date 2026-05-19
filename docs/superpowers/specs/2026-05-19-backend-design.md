# backend.py — Vehicle Crossing Event Backend Design

**Date:** 2026-05-19

## Overview

A single-file FastAPI backend that receives vehicle crossing events from `detector.py`, stores them in SQLite, and exposes read endpoints for current totals, hourly/daily aggregates, and a breakdown by vehicle class and direction.

## Goals

- Accept `POST /events` payloads from `detector.py` and persist each crossing to SQLite.
- Expose read endpoints for current, hourly, daily, and breakdown counts.
- No new dependencies beyond what is already in `requirements.txt` (FastAPI, uvicorn, pydantic are all present; sqlite3 is stdlib).

## Non-Goals

- Authentication or rate limiting.
- Multi-camera support.
- Real-time push (WebSocket/SSE) to a dashboard.
- Data retention / purge policy.

---

## Architecture

```
detector.py  →  POST /events  →  crossings table (SQLite)
                                        │
              GET /counts/current  ─────┤
              GET /counts/hourly   ─────┤  SQL GROUP BY queries
              GET /counts/daily    ─────┤
              GET /counts/breakdown ────┘
```

All aggregations are computed at query time via SQL. No separate counters table.

---

## Database Schema

File: `vehicles.db` (configurable via `--db` CLI arg, default: project root)

```sql
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
);
```

`timestamp` is stored as ISO 8601 UTC string (as sent by `detector.py`). SQLite's `strftime` and `date` functions operate on this format directly.

---

## File Structure

```
backend.py
├── init_db(db_path)           create table if not exists, return sqlite3.Connection
├── get_db()                   FastAPI dependency — yields a connection per request
├── EventPayload               Pydantic model matching detector.py payload
├── POST /events               insert one row, return {"id": <row_id>}
├── GET /counts/current        SELECT COUNT grouped by direction (all time)
├── GET /counts/hourly         GROUP BY strftime hour, filtered by ?date=YYYY-MM-DD
├── GET /counts/daily          GROUP BY date(timestamp), last ?days=N days (default 7)
├── GET /counts/breakdown      GROUP BY class_name + direction (all time)
└── __main__                   uvicorn.run() with --host, --port, --db argparse args
```

---

## API

### POST /events

Receives a crossing event from `detector.py`.

**Request body:**
```json
{
  "timestamp": "2026-05-19T14:23:01.123456+00:00",
  "track_id": 42,
  "class_name": "car",
  "direction": "in",
  "bbox": {"x1": 120, "y1": 200, "x2": 280, "y2": 340},
  "confidence": 0.8765
}
```

**Response:** `201 Created`
```json
{"id": 1}
```

---

### GET /counts/current

Total in/out counts across all stored crossings.

**Response:** `200 OK`
```json
{"in": 42, "out": 38}
```

---

### GET /counts/hourly?date=YYYY-MM-DD

Per-hour counts for a given UTC date. Defaults to today UTC if `date` is omitted. Hours with zero crossings are omitted.

**Response:** `200 OK`
```json
[
  {"hour": "2026-05-19T14:00:00Z", "in": 5, "out": 3},
  {"hour": "2026-05-19T15:00:00Z", "in": 8, "out": 7}
]
```

---

### GET /counts/daily?days=N

Per-day counts for the last N days (default 7). Days with zero crossings are omitted.

**Response:** `200 OK`
```json
[
  {"date": "2026-05-18", "in": 120, "out": 110},
  {"date": "2026-05-19", "in": 42, "out": 38}
]
```

---

### GET /counts/breakdown

Counts grouped by `class_name` and `direction`, all time.

**Response:** `200 OK`
```json
[
  {"class_name": "car",        "direction": "in",  "count": 30},
  {"class_name": "car",        "direction": "out", "count": 27},
  {"class_name": "truck",      "direction": "in",  "count": 8},
  {"class_name": "motorcycle", "direction": "out", "count": 4}
]
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Malformed / missing fields in POST body | FastAPI/Pydantic returns 422 automatically |
| DB write fails | 500 with error message logged to stderr |
| Invalid `date` query param format | 400 with message |
| Unknown query params | Ignored, defaults used |

---

## CLI

```
python backend.py [OPTIONS]

Options:
  --host  TEXT  Bind host (default: 0.0.0.0)
  --port  INT   Bind port (default: 8000)
  --db    TEXT  Path to SQLite file (default: vehicles.db)
```

---

## Testing

`tests/test_backend.py` uses FastAPI's `TestClient`. A temporary in-memory SQLite DB (`:memory:`) is injected via FastAPI's dependency override for `get_db()` — no disk writes during tests.

Test coverage:
- `POST /events` stores row and returns id
- `GET /counts/current` returns correct in/out totals
- `GET /counts/hourly` filters by date, groups by hour
- `GET /counts/daily` filters by last N days
- `GET /counts/breakdown` groups by class_name + direction
- `POST /events` with malformed body returns 422

---

## Dependencies

All already present in `venv/`:

| Package | Purpose |
|---|---|
| `fastapi` | Web framework + routing |
| `uvicorn` | ASGI server |
| `pydantic` | Request body validation |
| `sqlite3` | stdlib — DB storage |
