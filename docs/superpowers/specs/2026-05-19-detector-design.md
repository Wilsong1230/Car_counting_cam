# detector.py — Vehicle Line-Crossing Counter Design

**Date:** 2026-05-19

## Overview

A single-file `detector.py` that reads a webcam, runs YOLOv8n + ByteTrack to track vehicles, detects when a tracked vehicle crosses a configurable virtual line, and posts a structured event payload to a backend HTTP endpoint.

## Goals

- Count vehicles (car, truck, bus, motorcycle) crossing a virtual horizontal line in the webcam feed.
- Post a rich event payload to a backend URL on each crossing.
- Never block the capture loop on network I/O.
- All dependencies available in the existing `.venv`.

## Non-Goals

- Backend implementation (deferred).
- Persistent storage or queuing of events.
- Multi-camera support.
- GPU acceleration configuration (uses whatever `ultralytics` defaults to).

---

## Architecture

```
webcam (OpenCV VideoCapture)
    │
    ▼
YOLOv8n inference  (ultralytics, vehicle classes: car/truck/bus/motorcycle)
    │
    ▼
ByteTrack  (ultralytics built-in tracker via bytetrack.yaml)
    │  produces: track_id, bbox, class per frame
    ▼
Line-crossing detector  (centroid crosses configured horizontal line this frame?)
    │  on crossing: build event payload
    ▼
HTTP poster  (requests.post in daemon Thread, fire-and-forget)
    │
    ▼
Backend  (configurable URL, not yet implemented)
```

---

## CLI Interface

```
python detector.py [OPTIONS]

Options:
  --camera       INT    OpenCV camera index (default: 0)
  --line-y       FLOAT  Line position as fraction of frame height, 0.0–1.0 (default: 0.5)
  --backend-url  STR    URL to POST events to (default: http://localhost:8000/events)
  --show                Display annotated frame in a window (flag, default: off)
```

---

## Components

### Capture Loop
- Opens `cv2.VideoCapture(camera_index)`. Exits with an error message if the device cannot be opened.
- Reads frames in a tight loop. Skips dropped frames (where `cap.read()` returns `False`) without crashing.
- Draws the virtual line on each frame when `--show` is active.

### YOLOv8n + ByteTrack
- Uses `ultralytics` `YOLO("yolov8n.pt")` with `model.track(frame, tracker="bytetrack.yaml", persist=True)`.
- Filters detections to COCO vehicle classes: car (2), motorcycle (3), bus (5), truck (7).
- Extracts per-detection: `track_id`, `bbox` (x1, y1, x2, y2), `class_name`, `confidence`.

### Line-Crossing Detector
- The virtual line is a horizontal line at `y = line_y * frame_height`.
- For each tracked vehicle, computes the centroid `cy = (y1 + y2) / 2`.
- Maintains a dict `prev_cy: dict[track_id, float]` across frames.
- A crossing is detected when `prev_cy` and current `cy` are on opposite sides of the line.
- `direction = "in"` if centroid moves top-to-bottom (prev < line_y, current >= line_y); `"out"` otherwise.
- Each `track_id` can only trigger one crossing event per side-transition (no double-firing for vehicles lingering at the line).

### HTTP Poster
- On each crossing, spawns a `threading.Thread(daemon=True)` that calls `requests.post(backend_url, json=payload, timeout=3)`.
- Non-2xx responses and network errors are logged to stderr. The capture loop is never blocked.

---

## Event Payload

```json
{
  "timestamp": "2026-05-19T14:23:01.123456Z",
  "track_id": 42,
  "class_name": "car",
  "direction": "in",
  "bbox": {
    "x1": 120,
    "y1": 200,
    "x2": 280,
    "y2": 340
  },
  "confidence": 0.87
}
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Webcam fails to open | Exit with `sys.exit("Error: cannot open camera {index}")` |
| Frame dropped by OpenCV | Skip frame, continue loop |
| Backend POST fails (any reason) | Log to stderr, drop event, continue |
| YOLO model file not found | `ultralytics` will auto-download `yolov8n.pt` on first run |

---

## Dependencies

All present in the existing `.venv` via `requirements.txt`:

| Package | Purpose |
|---|---|
| `ultralytics` | YOLOv8n inference + ByteTrack |
| `opencv-python` | Webcam capture and frame annotation |
| `requests` | HTTP POST to backend |

No new packages required.

---

## File Layout

```
computer_vision_porject/
├── detector.py          ← the deliverable
├── requirements.txt
├── .venv/
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-19-detector-design.md
```
