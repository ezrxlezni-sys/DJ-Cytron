import os
import sys
import time
from pathlib import Path

import pytest

from piplayer.app import create_app
from piplayer.config import Config

os.environ["PIPLAYER_TTS"] = "off"            # the tests never speak out loud (door tests inject a fake speaker)

FAKE = str(Path(__file__).parent / "fake_mpv.py")
SONG = {"kind": "ytm", "id": "abc", "title": "Song", "artist": "Artist"}


@pytest.fixture(autouse=True)
def _pause_when_empty(monkeypatch):
    """Most door tests are about pausing; the quiet idle music (default 30 %) has its own tests that set `idle`."""
    from piplayer import bathrooms
    monkeypatch.setitem(bathrooms.DEFAULTS, "idle", 0)


@pytest.fixture
def app(tmp_path):
    cfg = Config(host="127.0.0.1", port=0, data_dir=tmp_path,
                 mpv_cmd=(sys.executable, FAKE), socket_path=str(tmp_path / "mpv.sock"))
    app = create_app(cfg, resolver=lambda vid: f"http://example/{vid}.m4a",
                     search=lambda q, kind: [SONG], trending=lambda: [])
    yield app
    app.extensions["piplayer"].player.close()


@pytest.fixture
def client(app):
    return app.test_client()


def wait_for(fn, timeout=3):
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture(autouse=True)
def _fresh_search_cache():
    """The YouTube / SoundCloud search cache is module-wide: every test starts and ends with it empty."""
    from piplayer import api
    api._search_cache.clear()
    yield
    api._search_cache.clear()
