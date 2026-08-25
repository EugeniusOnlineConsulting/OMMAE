import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

STORE = Path(tempfile.mkdtemp()) / "ommae-test.json"
os.environ["OMMAE_STORE_PATH"] = str(STORE)

import pytest

from store import configure, reset


@pytest.fixture(autouse=True)
def fresh_store():
    configure(str(STORE))
    reset(str(STORE))
    yield
