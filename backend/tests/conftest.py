import os
import sys
import tempfile

os.environ["DISABLE_AI"] = "1"  # tests are deterministic and never hit Gemini
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def clean():
    from app import db as d
    d.init()
    d.wipe_user("t")
    yield
