import json
import sys

import pytest

from piplayer import soundcloud
from piplayer.app import create_app
from piplayer.config import Config
from conftest import FAKE, SONG, wait_for

GOOD = {"kind": "sc", "id": "88335161", "title": "Get Lucky", "artist": "DJ KB", "duration": 246,
        "url": "https://soundcloud.com/eldjkb/get-lucky-original-version"}


def post(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


@pytest.fixture
def sc(tmp_path):
    seen = {"resolved": []}
    cfg = Config(host="127.0.0.1", port=0, data_dir=tmp_path,
                 mpv_cmd=(sys.executable, FAKE), socket_path=str(tmp_path / "mpv.sock"))

    def sc_resolver(url):
        seen["resolved"].append(url)
        return "http://example/sc.m4a"

    app = create_app(cfg, resolver=lambda vid: f"http://example/{vid}.m4a", search=lambda q, kind: [SONG],
                     trending=lambda: [], sc_search=lambda q, kind: [GOOD], sc_resolver=sc_resolver)
    yield app.test_client(), app, seen
    app.extensions["piplayer"].player.close()


def test_search_source_switch(sc):
    client, _, _ = sc
    assert client.get("/api/search?q=x&source=soundcloud").json == [GOOD]
    assert client.get("/api/search?q=x").json == [SONG]                      # default stays YouTube Music


def test_sc_track_plays_through_its_permalink(sc):
    client, app, seen = sc
    assert post(client, "/api/play", {"items": [GOOD]}).status_code == 200
    assert wait_for(lambda: seen["resolved"] == [GOOD["url"]])


@pytest.mark.parametrize("bad", [
    {**GOOD, "url": "https://evil.example/eldjkb/track"},                    # not soundcloud.com
    {**GOOD, "url": "http://soundcloud.com/eldjkb/track"},                   # not https
    {**GOOD, "url": "https://soundcloud.com.evil.example/a/b"},              # look-alike host
    {**GOOD, "url": "file:///etc/passwd"},
    {**GOOD, "url": None},
    {**GOOD, "id": "12;rm -rf"},                                             # id must be numeric
])
def test_sc_item_validation(sc, bad):
    client, _, _ = sc
    assert post(client, "/api/play", {"items": [bad]}).status_code == 400
    assert post(client, "/api/queue", {"items": [bad]}).status_code == 400


def test_sc_item_keeps_url_in_queue_and_playlist(sc):
    client, _, _ = sc
    assert post(client, "/api/queue", {"items": [GOOD]}).status_code == 200
    q = client.get("/api/state").json["queue"]
    assert q and q[0]["url"] == GOOD["url"] and q[0]["kind"] == "sc"


def test_resolve_rejects_non_soundcloud_url():
    with pytest.raises(ValueError):
        soundcloud.resolve("https://evil.example/a/b")


class FakeYDL:
    entries = []
    info = {}

    def __init__(self, opts=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        return {"entries": FakeYDL.entries} if url.startswith("scsearch") else FakeYDL.info


def _entry(tid, dur, url=None, title="T"):
    return {"id": tid, "title": title, "uploader": "U", "duration": dur,
            "webpage_url": url or f"https://soundcloud.com/u/t{tid}",
            "thumbnails": [{"id": "t200x200", "url": "s"}, {"id": "t500x500", "url": "b"}]}


def test_search_hides_previews_and_bad_entries(monkeypatch):
    monkeypatch.setattr(soundcloud.yt_dlp, "YoutubeDL", FakeYDL)
    FakeYDL.entries = [_entry("1", 246.4), _entry("2", 30.0), _entry("3", 180, url="https://evil.example/a/b"),
                       _entry("4", 200, title=""), _entry("5", 61)]
    out = soundcloud.search("q")
    assert [t["id"] for t in out] == ["1", "5"]
    assert out[0]["kind"] == "sc" and out[0]["thumb"] == "s" and out[0]["art"] == "b" and out[0]["duration"] == 246


def test_resolve_refuses_preview_stream(monkeypatch):
    monkeypatch.setattr(soundcloud.yt_dlp, "YoutubeDL", FakeYDL)
    soundcloud._cache.clear()
    FakeYDL.info = {"url": "http://cdn/x.mp3", "format_id": "http_mp3_1_0_preview"}
    with pytest.raises(RuntimeError):
        soundcloud.resolve("https://soundcloud.com/u/preview-track")
    FakeYDL.info = {"url": "http://cdn/full.m4a", "format_id": "hls_aac_96k"}
    assert soundcloud.resolve("https://soundcloud.com/u/full-track") == "http://cdn/full.m4a"
