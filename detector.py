import sys
import time
import argparse
import threading
from datetime import datetime, timezone

import cv2
import requests
from ultralytics import YOLO

VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--line-y", type=float, default=0.5, dest="line_y")
    p.add_argument("--backend-url", type=str, default="http://localhost:8000/events", dest="backend_url")
    p.add_argument("--show", action="store_true")
    return p.parse_args(argv)


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


def _do_post(url, payload):
    try:
        resp = requests.post(url, json=payload, timeout=3)
        resp.raise_for_status()
    except Exception as e:
        print(f"POST failed: {e}", file=sys.stderr)


def post_event(url, payload):
    t = threading.Thread(target=_do_post, args=(url, payload), daemon=True)
    t.start()


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
