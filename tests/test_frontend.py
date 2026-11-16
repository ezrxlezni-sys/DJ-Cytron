"""Front-end checks that need no browser: music.js runs in Node against a tiny fake DOM and a fake API
(tests/frontend/music_harness.js). It covers the Music pages' logic, not how they look."""
import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).parent / "frontend" / "music_harness.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_music_pages_logic():
    r = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ALL PASSED" in r.stdout
