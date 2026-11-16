from piplayer.history import HistoryStore

from conftest import SONG, wait_for


def test_store_counts_plays_and_ignores_radio(tmp_path):
    h = HistoryStore(tmp_path / "h.json")
    h.record({"kind": "radio", "id": "r1", "title": "Station"})
    h.record(SONG)
    assert [e["id"] for e in h.recent()] == ["abc"]
    assert h.top() == []                                   # one play is not "mostly played"
    h.record(SONG)
    h.record({**SONG, "id": "def", "title": "Other"})
    assert [(e["id"], e["plays"]) for e in h.top()] == [("abc", 2)]
    assert [e["id"] for e in h.recent()] == ["def", "abc"]
    assert h.seeds() == ["abc", "def"]


def test_playing_records_history(app, client):
    client.post("/api/play", json={"items": [SONG]})
    assert wait_for(lambda: client.get("/api/history").json["recent"])
    assert client.get("/api/history").json["recent"][0]["id"] == "abc"


def test_suggested_falls_back_then_uses_history(app, client):
    assert client.get("/api/suggested").json == [SONG]     # fresh install: generic search
    svc = app.extensions["piplayer"]
    svc.suggest = lambda seeds: [{**SONG, "id": "abc"}, {**SONG, "id": "new", "title": "New"}]
    svc.history.record(SONG)
    assert [t["id"] for t in client.get("/api/suggested").json] == ["new"]   # already-played tracks are hidden


def test_suggested_mixes_related_and_trending(app, client):
    svc = app.extensions["piplayer"]
    t = lambda i: {**SONG, "id": i, "title": i}
    svc.history.record(SONG)
    svc.suggest = lambda seeds: [t("r1"), t("r2"), t("abc")]
    svc.trending = lambda: [t("t1"), t("r1"), t("t2")]
    assert [x["id"] for x in client.get("/api/suggested").json] == ["r1", "t1", "r2", "t2"]   # alternating, deduped, no played
    svc.suggest = lambda seeds: (_ for _ in ()).throw(RuntimeError("down"))
    assert [x["id"] for x in client.get("/api/suggested").json] == ["t1", "r1", "t2"]         # related fails: trending alone


def test_suggested_fresh_install_uses_trending(app, client):
    app.extensions["piplayer"].trending = lambda: [{**SONG, "id": "t1", "title": "T"}]
    assert [x["id"] for x in client.get("/api/suggested").json] == ["t1"]


def test_clear_history(app, client):
    client.post("/api/play", json={"items": [SONG]})
    assert wait_for(lambda: client.get("/api/history").json["recent"])
    assert client.delete("/api/history").json == {"ok": True}
    assert client.get("/api/history").json == {"recent": [], "top": []}
    assert app.extensions["piplayer"].history.seeds() == []        # suggestions no longer lean on what was cleared
    assert client.delete("/api/history").status_code == 200        # clearing an empty history is fine


def test_clear_history_refuses_cross_site_requests(client):
    r = client.delete("/api/history", headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
