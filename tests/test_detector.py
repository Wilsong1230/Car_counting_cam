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
