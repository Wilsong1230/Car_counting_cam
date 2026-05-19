import sys
import time
import argparse
import threading
from datetime import datetime, timezone

import cv2
import requests
from ultralytics import YOLO

VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

CLASS_COLORS_BGR = {
    "car":        (246, 130,  59),
    "motorcycle": ( 11, 158, 245),
    "bus":        (250, 139, 167),
    "truck":      (153, 211,  52),
}

# parses command line arguments for camera index, line postion, backend url, and weather show feed or not. defaults to camera 0, line at 50% of frame height, and localhost backend.
def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--line-y", type=float, default=0.5, dest="line_y")
    p.add_argument("--backend-url", type=str, default="http://localhost:8000/events", dest="backend_url")
    p.add_argument("--show", action="store_true")
    return p.parse_args(argv)

# Check if object is moving up or down accross the line. Parameters are the previous y center, the track id, current y center, and line y in pixels. 
def check_crossing(prev_cy, track_id, cy, line_y_px):
    result = None
    if track_id in prev_cy:
        prev = prev_cy[track_id]
        if prev < line_y_px <= cy:
            result = "in"
        elif prev >= line_y_px > cy:
            result = "out"
    prev_cy[track_id] = cy
    return result

# build the payload for backend. paremeters are id, class name, direction, bounding box, and confidence.
# includes timestamp, ID, classname, direction, box and confidence. 
def build_payload(track_id, class_name, direction, bbox, confidence):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "track_id": int(track_id),
        "class_name": class_name,
        "direction": direction,
        "bbox": {
            "x1": int(bbox[0]),
            "y1": int(bbox[1]),
            "x2": int(bbox[2]),
            "y2": int(bbox[3]),
        },
        "confidence": round(float(confidence), 4),
    }

# posts events in sepereate thread to avoid blocking
def _do_post(url, payload):
    try:
        resp = requests.post(url, json=payload, timeout=3)
        resp.raise_for_status()
    except Exception as e:
        print(f"POST failed: {e}", file=sys.stderr)

# helper to post events without blocking the main thread
def post_event(url, payload):
    t = threading.Thread(target=_do_post, args=(url, payload), daemon=True)
    t.start()

# main detection loop. Initializes model and video, conitinuosuly reads frames, runs detection and tracking, checks for crossing, builds payload, and posts
# if --show is enabled, also draws line and bounding boxes in feed. 
def run_detection(args):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit(f"Error: cannot open camera {args.camera}")

    ok, frame = cap.read()
    if not ok:
        sys.exit(f"Error: could not read first frame from camera {args.camera}")
    h, w = frame.shape[:2]
    line_y_px = int(args.line_y * h)

    prev_cy = {}

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            results = model.track(frame, tracker="bytetrack.yaml", persist=True, verbose=False)

            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i])
                    if cls_id not in VEHICLE_CLASSES:
                        continue
                    track_id = int(boxes.id[i])
                    x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                    cy = (y1 + y2) / 2
                    conf = float(boxes.conf[i])
                    class_name = VEHICLE_CLASSES[cls_id]

                    direction = check_crossing(prev_cy, track_id, cy, line_y_px)
                    if direction:
                        payload = build_payload(track_id, class_name, direction, (x1, y1, x2, y2), conf)
                        post_event(args.backend_url, payload)

                    if args.show:
                        color = CLASS_COLORS_BGR.get(class_name, (200, 200, 200))
                        ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
                        cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), color, 2)
                        label = f"{class_name} #{track_id}  {conf:.0%}"
                        (lw, lh), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                        ly = max(iy1 - 4, lh + baseline)
                        cv2.rectangle(frame, (ix1, ly - lh - baseline), (ix1 + lw + 4, ly + 2), color, -1)
                        cv2.putText(frame, label, (ix1 + 2, ly - baseline + 1),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            if args.show:
                cv2.line(frame, (0, line_y_px), (w, line_y_px), (0, 255, 0), 2)
                cv2.imshow("detector", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    run_detection(parse_args())
