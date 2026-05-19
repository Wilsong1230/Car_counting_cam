import sys
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
    pass


def _do_post(url, payload):
    pass


def post_event(url, payload):
    pass


def run_detection(args):
    pass


if __name__ == "__main__":
    run_detection(parse_args())
