# CarCounter

A real-time vehicle detection and counting system that uses your camera feed, a YOLO model, and a local dashboard to track how many vehicles cross a line — split by direction and class.

---

## What it does

- Watches a live camera feed and detects vehicles crossing a virtual line
- Tracks cars, motorcycles, buses, and trucks separately
- Records every crossing (direction, class, confidence) to a local database
- Serves a live dashboard you can open in any browser

---

## How it works

```
Camera → detector.py → POST /events → backend.py → vehicles.db
                                                        ↓
                                              frontend/index.html
```

`detector.py` reads the camera, runs YOLOv8 tracking, and fires an event to the backend every time a vehicle crosses the line. `backend.py` stores it and exposes a handful of read endpoints the dashboard polls every 2 seconds.

---

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Start the backend**
```bash
python backend.py
```
Runs on `http://localhost:8000` by default.

**3. Start the detector**
```bash
python detector.py
```

Optional flags:
```
--camera 0          which camera to use (default: 0)
--line-y 0.5        where to draw the counting line, as a fraction of frame height (default: 0.5)
--backend-url ...   backend events endpoint (default: http://localhost:8000/events)
--show              show the live annotated camera feed
```

**4. Open the dashboard**

Just open `frontend/index.html` in your browser. No server needed for the frontend.

---

## Dashboard pages

| Page | What you see |
|------|-------------|
| **Overview** | KPI counters, hourly In vs Out chart, direction split, class breakdown donut |
| **Hourly** | Individual line charts per vehicle class over the last 12 hours |
| **Classes** | Specs for each detectable vehicle class (COCO IDs, thresholds, dimensions) |

---

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /events` | Ingest a crossing event from the detector |
| `GET /counts/current` | Total in/out counts all time |
| `GET /counts/hourly` | Hourly in/out counts for today |
| `GET /counts/hourly/breakdown` | Hourly counts broken down by vehicle class |
| `GET /counts/breakdown` | All-time counts by class and direction |
| `GET /counts/daily` | Daily counts for the last N days |

---

## Requirements

- Python 3.10+
- A webcam or USB camera
- `yolov8n.pt` in the project root (downloaded automatically by Ultralytics on first run)
