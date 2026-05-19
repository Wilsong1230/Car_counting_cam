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
