import sys
import time
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, ".")
import detector


def test_parse_args_defaults():
    args = detector.parse_args([])
    assert args.camera == 0
    assert args.line_y == 0.5
    assert args.backend_url == "http://localhost:8000/events"
    assert args.show is False


def test_parse_args_custom():
    args = detector.parse_args([
        "--camera", "2",
        "--line-y", "0.3",
        "--backend-url", "http://example.com/ev",
        "--show",
    ])
    assert args.camera == 2
    assert args.line_y == 0.3
    assert args.backend_url == "http://example.com/ev"
    assert args.show is True


def test_check_crossing_in():
    prev_cy = {1: 190.0}
    result = detector.check_crossing(prev_cy, 1, 210.0, 200.0)
    assert result == "in"


def test_check_crossing_out():
    prev_cy = {1: 210.0}
    result = detector.check_crossing(prev_cy, 1, 190.0, 200.0)
    assert result == "out"


def test_check_crossing_same_side_returns_none():
    prev_cy = {1: 100.0}
    result = detector.check_crossing(prev_cy, 1, 110.0, 200.0)
    assert result is None


def test_check_crossing_first_frame_returns_none():
    prev_cy = {}
    result = detector.check_crossing(prev_cy, 1, 210.0, 200.0)
    assert result is None
    assert prev_cy[1] == 210.0


def test_check_crossing_updates_prev_cy():
    prev_cy = {1: 190.0}
    detector.check_crossing(prev_cy, 1, 210.0, 200.0)
    assert prev_cy[1] == 210.0


def test_build_payload_structure():
    payload = detector.build_payload(42, "car", "in", (10, 20, 30, 40), 0.87654)
    assert payload["track_id"] == 42
    assert payload["class_name"] == "car"
    assert payload["direction"] == "in"
    assert payload["bbox"] == {"x1": 10, "y1": 20, "x2": 30, "y2": 40}
    assert payload["confidence"] == 0.8765
    assert "timestamp" in payload


def test_build_payload_coerces_types():
    payload = detector.build_payload(1.0, "truck", "out", (0.9, 1.9, 2.9, 3.9), 0.9)
    assert isinstance(payload["track_id"], int)
    assert isinstance(payload["bbox"]["x1"], int)
    assert isinstance(payload["confidence"], float)
