"""Hardening: input validation, request guard, mpv supervision, failure handling, persistence."""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import FAKE, SONG, wait_for
from piplayer.app import create_app
from piplayer.config import Config
from piplayer.settings import Settings
from piplayer.stations import StationStore


def post(client, path, body=None, **kw):
    return client.post(path, data=json.dumps(body if body is not None else {}), content_type="application/json", **kw)


def commands(app):
    p = app.extensions["piplayer"].cfg.socket_path + ".log"
    try:
        with open(p) as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []


def loads(app):
    return [c[1] for c in commands(app) if c[0] == "loadfile"]


def make_app(tmp_path, resolver=None, **kw):
    cfg = Config(host="127.0.0.1", port=0, data_dir=tmp_path,
                 mpv_cmd=(sys.executable, FAKE), socket_path=str(tmp_path / "mpv.sock"))
    return create_app(cfg, resolver=resolver or (lambda vid: f"http://example/{vid}.m4a"),
                      search=lambda q, kind: [SONG], trending=lambda: [], **kw)


@pytest.fixture
def mk(tmp_path):
    apps = []

    def factory(**kw):
        a = make_app(tmp_path, **kw)
        apps.append(a)
        return a
    yield factory
    for a in apps:
        a.extensions["piplayer"].player.close()


# ---------- input validation ----------
def test_radio_item_must_be_http_url(client):
    bad = {"kind": "radio", "id": "x", "title": "x", "url": "file:///etc/passwd"}
    assert post(client, "/api/play", {"items": [bad]}).status_code == 400
    assert post(client, "/api/queue", {"items": [bad]}).status_code == 400
    good = {**bad, "url": "https://example.com/stream"}
    assert post(client, "/api/play", {"items": [good]}).status_code == 200


def test_ytm_id_must_be_plain(client):
    bad = {**SONG, "id": "abc&list=x/../"}
    assert post(client, "/api/play", {"items": [bad]}).status_code == 400


@pytest.mark.parametrize("path,body", [
    ("/api/play", {"index": "x"}),
    ("/api/play", {"items": "nope"}),
    ("/api/queue", {"items": 5}),
    ("/api/control/seek", {"seconds": "soon"}),
    ("/api/control/volume", {"value": None}),
    ("/api/control/seek", {"seconds": float("nan")}),
])
def test_bad_numbers_are_400_not_500(client, path, body):
    assert post(client, path, body).status_code == 400


def test_non_object_json_body(client):
    assert client.post("/api/play", data="[1,2]", content_type="application/json").status_code == 400


# ---------- request guard ----------
def test_unknown_host_refused(client):
    assert client.get("/api/state", headers={"Host": "evil.example.com"}).status_code == 403
    for host in ("localhost", "192.168.1.20", "cytrondj.local", "cytrondj", "[::1]:8088"):
        assert client.get("/api/state", headers={"Host": host}).status_code == 200, host


def test_cross_origin_write_refused(client):
    assert post(client, "/api/control/stop", headers={"Origin": "http://evil.example.com"}).status_code == 403
    assert post(client, "/api/control/stop", headers={"Origin": "http://localhost"}).status_code == 200


def test_allowed_hosts_env(client, monkeypatch):
    monkeypatch.setenv("PIPLAYER_ALLOWED_HOSTS", "dj.example.com")
    assert client.get("/api/state", headers={"Host": "dj.example.com"}).status_code == 200


# ---------- corrupt / atomic files ----------
def test_corrupt_stations_file_recovers(tmp_path):
    path = tmp_path / "stations.json"
    store = StationStore(path)
    path.write_text("{ not json")
    items = store.all()
    assert items and any(s["id"] == "hitz-fm" for s in items)
    assert list(tmp_path.glob("stations.json.bad-*"))        # the damaged file is kept for inspection


def test_settings_flush_is_atomic_and_persists(tmp_path):
    s = Settings(tmp_path / "s.json", {"a": 1})
    s.set("a", 2)
    s.flush()
    assert json.loads((tmp_path / "s.json").read_text()) == {"a": 2}
    assert not (tmp_path / "s.tmp").exists()
    (tmp_path / "s.json").write_text("[1]")                   # wrong shape: ignored, defaults used
    assert Settings(tmp_path / "s.json", {"a": 1}).get("a") == 1


# ---------- mpv supervision ----------
def test_mpv_crash_is_restarted_and_playback_resumes(mk):
    app = mk()
    client = app.test_client()
    p = app.extensions["piplayer"].player
    post(client, "/api/play", {"items": [SONG]})
    assert wait_for(lambda: loads(app))
    old = p._proc
    old.kill()
    assert wait_for(lambda: p._proc is not None and p._proc is not old and p._proc.poll() is None, timeout=8)
    assert wait_for(lambda: loads(app), timeout=8)            # the fresh mpv was told to play the track again
    assert client.get("/api/state").json["queue"][0]["id"] == "abc"


def test_commands_do_not_raise_while_mpv_is_down(mk):
    app = mk()
    p = app.extensions["piplayer"].player
    p._proc.kill()
    p._proc.wait()
    for _ in range(3):                                        # whatever state the supervisor is in, no 500s
        assert post(app.test_client(), "/api/control/toggle").status_code == 200


# ---------- failure handling ----------
def test_unplayable_track_is_skipped(mk):
    def resolver(vid):
        if vid == "bad":
            raise RuntimeError("nope")
        return "http://example/ok.m4a"
    app = mk(resolver=resolver)
    client = app.test_client()
    post(client, "/api/play", {"items": [{**SONG, "id": "bad"}, {**SONG, "id": "good", "title": "Good"}]})
    assert wait_for(lambda: loads(app))
    st = client.get("/api/state").json
    assert st["index"] == 1 and st["current"]["id"] == "good"


def test_all_tracks_failing_stops_instead_of_looping(mk):
    calls = []

    def resolver(vid):
        calls.append(vid)
        raise RuntimeError("down")
    app = mk(resolver=resolver)
    client = app.test_client()
    client.post("/api/control/repeat", data=json.dumps({"value": "all"}), content_type="application/json")
    post(client, "/api/play", {"items": [{**SONG, "id": f"t{i}", "title": "T"} for i in range(3)]})
    assert wait_for(lambda: len(calls) >= 3 and not client.get("/api/state").json["loading"])
    time.sleep(0.5)
    assert len(calls) == 3                                    # one attempt per track, not an endless loop
    st = client.get("/api/state").json
    assert st["error"] and not st["loading"]


def test_unreachable_radio_is_retried_then_gives_up(mk, monkeypatch):
    real = time.sleep
    monkeypatch.setattr("piplayer.player.time.sleep", lambda s: real(0.02))
    app = mk()
    client = app.test_client()
    post(client, "/api/play", {"items": [{"kind": "radio", "id": "st1", "title": "R", "url": "http://r/unreachable"}]})
    assert wait_for(lambda: len(loads(app)) == 4)             # the first try + three reconnects
    real(0.4)
    assert len(loads(app)) == 4                               # then it stops trying
    st = client.get("/api/state").json
    assert st["error"] and not st["loading"]


def test_good_radio_reconnects_when_stream_drops(mk, monkeypatch):
    real = time.sleep
    monkeypatch.setattr("piplayer.player.time.sleep", lambda s: real(0.02))
    app = mk()
    p = app.extensions["piplayer"].player
    post(app.test_client(), "/api/play", {"items": [{"kind": "radio", "id": "st1", "title": "R", "url": "http://r/live"}]})
    assert wait_for(lambda: len(loads(app)) == 1)
    for n in range(2, 7):                                     # each drop that is followed by a good reconnect gets fresh retries
        p._event({"event": "end-file", "reason": "eof"})
        assert wait_for(lambda n=n: len(loads(app)) == n)


# ---------- prefetch + persistence ----------
def test_next_ytm_track_is_prefetched(mk):
    seen = []
    app = mk(resolver=lambda vid: seen.append(vid) or "http://example/x.m4a")
    post(app.test_client(), "/api/play", {"items": [SONG, {**SONG, "id": "next1", "title": "Next"}]})
    assert wait_for(lambda: "next1" in seen)                  # resolved while the first track is still playing


def test_queue_survives_restart(tmp_path):
    a = make_app(tmp_path)
    svc = a.extensions["piplayer"]
    post(a.test_client(), "/api/play", {"items": [SONG, {**SONG, "id": "two", "title": "Two"}]})
    post(a.test_client(), "/api/control/repeat", {"value": "all"})
    assert wait_for(lambda: svc.player.snapshot()["index"] == 0)
    svc.queue_state.flush()
    svc.player.close()
    b = make_app(tmp_path)
    try:
        st = b.test_client().get("/api/state").json
        assert [t["id"] for t in st["queue"]] == ["abc", "two"] and st["index"] == 0
        assert st["repeat"] == "all" and not st["playing"]          # restored, not auto-played
    finally:
        b.extensions["piplayer"].player.close()


# ---------- frontend ----------
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_frontend_js_parses():
    js = Path(__file__).parent.parent / "piplayer" / "static" / "js" / "app.js"
    r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_app_starts_without_mpv_and_recovers_when_it_appears(tmp_path):
    import sys
    from conftest import FAKE, wait_for
    from piplayer.config import Config
    from piplayer.player import Player
    cmd = tmp_path / "mpv-launcher"
    p = Player(lambda item: "x", mpv_cmd=("/nonexistent/mpv",), socket_path=str(tmp_path / "s.sock"))
    try:
        assert "unavailable" in p.snapshot()["error"]          # the app came up; the engine is retried in the background
        p.toggle()                                             # and nothing crashes meanwhile
        p.mpv_cmd = [sys.executable, FAKE]
        assert wait_for(lambda: p._sock is not None, timeout=6)
    finally:
        p.close()
