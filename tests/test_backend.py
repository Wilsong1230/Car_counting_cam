import sys
import sqlite3
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, ".")
from backend import app, get_db, init_db, parse_args
