import json

from conftest import SONG, wait_for


def post(client, path, body=None):
    return client.post(path, data=json.dumps(body or {}), content_type="application/json")


def sent_commands(app):
    p = app.extensions["piplayer"].cfg.socket_path + ".log"
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def test_index_and_assets(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200
    assert client.get("/static/css/app.css").status_code == 200
    for f in ("manifest.webmanifest", "logo-128.png", "logo-512.png", "favicon-32.png", "favicon-64.png", "apple-touch-icon.png"):
        assert client.get(f"/static/{f}" if f.endswith("webmanifest") else f"/static/brand/{f}").status_code == 200, f


def test_station_crud(client):
    base = [s["id"] for s in client.get("/api/stations").json]
    assert "hitz-fm" in base
    r = post(client, "/api/stations", {"title": "X", "url": "https://x.test/live"})
    assert r.json[-1]["id"] == "st1" and len(r.json) == len(base) + 1
    assert post(client, "/api/stations", {"title": "Bad", "url": "ftp://x"}).status_code == 400
    r = client.put("/api/stations/st1", data=json.dumps({"title": "Y", "url": "https://y.test/live"}), content_type="application/json")
    assert r.json[-1]["title"] == "Y" and r.json[-1]["url"] == "https://y.test/live"
    assert client.put("/api/stations/st1", data=json.dumps({"title": "", "url": "https://y.test"}), content_type="application/json").status_code == 400
    assert client.put("/api/stations/nope", data=json.dumps({"title": "Z", "url": "https://z.test"}), content_type="application/json").status_code == 404
    assert [s["id"] for s in client.delete("/api/stations/st1").json] == base


def test_play_station_loads_url(app, client):
    assert post(client, "/api/play", {"station": "hitz-fm"}).status_code == 200
    assert wait_for(lambda: client.get("/api/state").json["playing"])
    assert any(c[0] == "loadfile" and "revma" in c[1] for c in sent_commands(app))
    assert post(client, "/api/play", {"station": "nope"}).status_code == 404


def test_ytm_item_is_resolved(app, client):
    post(client, "/api/play", {"items": [SONG]})
    assert wait_for(lambda: any(c[0] == "loadfile" for c in sent_commands(app)))
    assert ["loadfile", "http://example/abc.m4a", "replace"] in sent_commands(app)


def test_queue_advances_and_remove(client):
    post(client, "/api/play", {"items": [SONG, {**SONG, "id": "b"}, {**SONG, "id": "c"}]})
    wait_for(lambda: client.get("/api/state").json["playing"])
    post(client, "/api/control/next")
    assert wait_for(lambda: client.get("/api/state").json["index"] == 1)
    client.delete("/api/queue/2")
    assert len(client.get("/api/state").json["queue"]) == 2


def test_volume_clamped_and_persisted(app, client):
    post(client, "/api/control/volume", {"value": 250})
    assert wait_for(lambda: client.get("/api/state").json["volume"] == 100)
    assert app.extensions["piplayer"].settings.get("volume") == 100


def test_search(client):
    assert client.get("/api/search?q=hello").json == [SONG]
    assert client.get("/api/search?q=").json == []


def test_bad_control(client):
    assert post(client, "/api/control/explode").status_code == 400


def test_bathrooms_default_unknown(client):
    rooms = client.get("/api/state").get_json()["bathrooms"]
    assert [(r["id"], r["occupied"]) for r in rooms] == [("male", None), ("female", None)]


def test_bathrooms_occupancy_updates(app, client):
    svc = app.extensions["piplayer"]
    v = svc.version
    svc.bathrooms.set("female", True)
    rooms = {r["id"]: r for r in client.get("/api/state").get_json()["bathrooms"]}
    assert rooms["female"]["occupied"] is True and rooms["female"]["since"]
    assert rooms["male"]["occupied"] is None
    assert svc.version > v                      # SSE subscribers are notified
    svc.bathrooms.set("female", False)
    assert client.get("/api/state").get_json()["bathrooms"][1]["occupied"] is False


def test_bathroom_pins_from_env():
    from piplayer.config import Config
    cfg = Config.from_env({"PIPLAYER_BATHROOM_PINS": "male=5, female=6"})
    assert cfg.bathroom_pins == (("male", 5), ("female", 6))


def test_event_stream_pushes_state_changes(app):
    """Regression: the SSE generator must not depend on the (already closed) request context."""
    import threading
    svc = app.extensions["piplayer"]
    resp = app.test_client().get("/api/events", buffered=False)
    chunks = iter(resp.response)
    first = next(chunks).decode()                      # initial snapshot
    assert first.startswith("data: ") and '"bathrooms"' in first
    threading.Timer(0.2, lambda: svc.bathrooms.set("male", True)).start()
    nxt = next(chunks).decode()
    assert nxt.startswith("data: ") and '"occupied": true' in nxt.replace('"occupied":true', '"occupied": true')
    resp.close()


def test_playlist_crud_and_play(client):
    assert client.get("/api/playlists").json == []
    assert post(client, "/api/playlists", {"name": " "}).status_code == 400
    r = post(client, "/api/playlists", {"name": "Morning", "items": [SONG, {"bad": 1}]})
    assert r.json[0]["id"] == "pl1" and r.json[0]["items"] == [SONG]
    assert post(client, "/api/playlists/pl1/items", {"items": [{**SONG, "id": "def", "title": "Two"}]}).json[0]["items"][1]["id"] == "def"
    assert post(client, "/api/playlists/nope/items", {"items": [SONG]}).status_code == 404
    assert client.put("/api/playlists/pl1", data=json.dumps({"name": "AM"}), content_type="application/json").json[0]["name"] == "AM"
    assert post(client, "/api/play", {"playlist": "pl1", "from": 1}).status_code == 200
    assert wait_for(lambda: client.get("/api/state").json["current"]["id"] == "def")
    assert len(client.get("/api/state").json["queue"]) == 1
    assert len(client.delete("/api/playlists/pl1/items/0").json[0]["items"]) == 1
    assert client.delete("/api/playlists/pl1").json == []
    assert post(client, "/api/play", {"playlist": "pl1"}).status_code == 404


def test_shuffle_visits_every_track_once_and_repeat_state(client):
    items = [{**SONG, "id": f"s{i}", "title": f"T{i}"} for i in range(4)]
    post(client, "/api/play", {"items": items})
    assert wait_for(lambda: client.get("/api/state").json["index"] == 0)
    post(client, "/api/control/shuffle", {"value": True})
    seen = {0}
    for _ in range(3):
        cur = client.get("/api/state").json["index"]
        post(client, "/api/control/next")
        assert wait_for(lambda: client.get("/api/state").json["index"] != cur)
        seen.add(client.get("/api/state").json["index"])
    assert seen == {0, 1, 2, 3}
    assert client.get("/api/state").json["shuffle"] is True
    post(client, "/api/control/repeat", {"value": "one"})
    assert client.get("/api/state").json["repeat"] == "one"
    post(client, "/api/control/repeat", {"value": "bogus"})
    assert client.get("/api/state").json["repeat"] == "off"


def test_listen_needs_capture_tools(client, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    r = client.get("/api/listen")
    assert r.status_code == 503 and "ffmpeg" in r.json["error"]


def test_queue_move_and_clear(client):
    items = [{**SONG, "id": f"q{i}", "title": f"T{i}"} for i in range(5)]
    post(client, "/api/play", {"items": items})
    assert wait_for(lambda: client.get("/api/state").json["index"] == 0)
    ids = lambda: [t["id"] for t in client.get("/api/state").json["queue"]]
    post(client, "/api/queue/move", {"from": 3, "to": 1})
    assert ids() == ["q0", "q3", "q1", "q2", "q4"]
    post(client, "/api/queue/move", {"from": 0, "to": 2})                    # move the playing track: index follows it
    st = client.get("/api/state").json
    assert [t["id"] for t in st["queue"]][st["index"]] == "q0" and st["index"] == 2
    assert post(client, "/api/queue/move", {"from": "x"}).status_code == 400
    post(client, "/api/queue/clear", {})                                     # clears only what is after the current track
    assert ids() == ["q3", "q1", "q0"]
    post(client, "/api/queue/clear", {"scope": "all"})
    assert ids() == [] and client.get("/api/state").json["index"] == -1
