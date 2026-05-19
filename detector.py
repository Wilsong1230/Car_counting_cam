import sys
import argparse
import threading
from datetime import datetime, timezone

import cv2
import requests
from ultralytics import YOLO

VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def parse_args(argv=None):
    pass


def check_crossing(prev_cy, track_id, cy, line_y_px):
    pass


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
