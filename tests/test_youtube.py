import json
import sys

import pytest

from piplayer import youtube
from piplayer.app import create_app
from piplayer.config import Config
from conftest import FAKE, SONG, wait_for

VID = {"kind": "yt", "id": "rFZHOHl-L8A", "title": "lofi radio", "artist": "Lofi Girl", "duration": 120}


def post(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


@pytest.fixture
def yt(tmp_path):
    seen = {"resolved": []}
    cfg = Config(host="127.0.0.1", port=0, data_dir=tmp_path,
                 mpv_cmd=(sys.executable, FAKE), socket_path=str(tmp_path / "mpv.sock"))

    def yt_resolver(vid):
        seen["resolved"].append(vid)
        return "http://example/yt.m4a"

    app = create_app(cfg, resolver=lambda vid: f"http://example/{vid}.m4a", search=lambda q, kind: [SONG],
                     trending=lambda: [SONG], yt_search=lambda q, kind: [VID], yt_resolver=yt_resolver)
    yield app.test_client(), seen
    app.extensions["piplayer"].player.close()


def test_search_sources(yt):
    client, _ = yt
    assert client.get("/api/search?q=x&source=youtube").json == [VID]
    assert client.get("/api/search?q=x").json == [SONG]


def test_trending_endpoint(yt):
    client, _ = yt
    assert client.get("/api/trending").json == [SONG]


def test_yt_item_plays_by_id(yt):
    client, seen = yt
    assert post(client, "/api/play", {"items": [VID]}).status_code == 200
    assert wait_for(lambda: seen["resolved"] == [VID["id"]])


@pytest.mark.parametrize("bad_id", ["short", "has space!!", "way-too-long-for-a-video-id", "a;b|c&d$e", ""])
def test_yt_id_validation(yt, bad_id):
    client, _ = yt
    assert post(client, "/api/play", {"items": [{**VID, "id": bad_id}]}).status_code == 400


def test_resolve_rejects_bad_id():
    with pytest.raises(ValueError):
        youtube.resolve("not an id")


class FakeYDL:
    entries = []

    def __init__(self, opts=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        return {"entries": FakeYDL.entries}


def test_search_maps_entries(monkeypatch):
    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYDL)
    th = [{"url": "small.jpg"}, {"url": "big.jpg"}]
    FakeYDL.entries = [
        {"id": "rFZHOHl-L8A", "title": "A", "channel": "Ch", "duration": 61.9, "thumbnails": th},
        {"id": "bad", "title": "skipped: not a video id"},
        {"id": "n61ULEU7CO0", "title": "", "channel": "x"},
        {"id": "5yx6BWlEVcY", "title": "Live", "uploader": "Up", "duration": None},
    ]
    out = youtube.search("q")
    assert [t["id"] for t in out] == ["rFZHOHl-L8A", "5yx6BWlEVcY"]
    assert out[0]["artist"] == "Ch" and out[0]["duration"] == 61 and out[0]["thumb"] == "small.jpg" and out[0]["art"] == "big.jpg"
    assert out[1]["duration"] is None and "i.ytimg.com" in out[1]["thumb"]
