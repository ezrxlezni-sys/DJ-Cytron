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
    assert app.extensions["piplayer"].settings.get("volume") is None      # every start begins at the default: nothing is saved


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


def test_youtube_and_soundcloud_searches_are_cached(app, client):
    from piplayer import api
    svc, calls = app.extensions["piplayer"], []
    svc.search_yt = lambda q, kind: calls.append(("yt", q)) or [{"kind": "yt", "id": "a" * 11, "title": q}]
    svc.search_sc = lambda q, kind: calls.append(("sc", q)) or []
    api._search_cache.clear()
    for _ in range(3):
        assert client.get("/api/search?q=Lo-fi&source=youtube").get_json()[0]["title"] == "Lo-fi"
    assert calls == [("yt", "Lo-fi")]                              # the slow yt-dlp search ran once
    client.get("/api/search?q=lo-fi&source=youtube")               # same words, any case
    assert calls == [("yt", "Lo-fi")]
    for _ in range(2):
        assert client.get("/api/search?q=none&source=soundcloud").get_json() == []
    assert calls.count(("sc", "none")) == 2                        # empty answers are not cached (could be a hiccup)


def test_browse_shelves_hide_explicit_content(app, client):
    from piplayer import api, safety
    items = [{"kind": "yt", "id": "a" * 11, "title": "Lo-fi beats"},
             {"kind": "ytm", "id": "b" * 11, "title": "Fine title", "explicit": True},      # flagged by the source
             {"kind": "yt", "id": "c" * 11, "title": "Uncensored party mix"},               # marker in the title
             {"kind": "sc", "id": "1", "title": "Chill", "artist": "DJ Shitposter"},         # profanity in the artist
             {"kind": "yt", "id": "d" * 11, "title": "Scunthorpe Classic Assessment"},      # innocent words stay
             {"kind": "yt", "id": "e" * 11, "title": "Some Song (E)"}]
    assert [i["title"] for i in safety.only_clean(items)] == ["Lo-fi beats", "Scunthorpe Classic Assessment"]
    svc = app.extensions["piplayer"]
    svc.search_yt = lambda q, kind: items
    svc.trending = lambda: items
    api._search_cache.clear()
    assert len(client.get("/api/search?q=x&source=youtube").get_json()) == 6               # a typed search is left alone
    assert len(client.get("/api/search?q=x&source=youtube&safe=1").get_json()) == 2        # shelves ask for the safe list
    assert len(client.get("/api/trending").get_json()) == 2


def test_filter_catches_censored_and_soundcloud_style_titles():
    from piplayer.safety import is_clean
    for bad in ("F**k the world", "sh*t happens", "Dirty Mix 2024", "Sexy Back (Remix)", "Wake & bake weed mix", "Thug Life", "b*tch please", "Big Ass Beats", "Not for kids 18+"):
        assert not is_clean({"title": bad}), bad
    for good in ("Sunset Lo-fi", "Classic Assessment", "Deep House Mix", "Ambient Rain", "Sussex Summer", "Bassline Night", "Dickens reading"):
        assert is_clean({"title": good}), good


def test_equalizer_presets_custom_gains_and_validation(app, client):
    r = post(client, "/api/eq", {"preset": "bass"})
    assert r.status_code == 200 and r.json["eq"]["preset"] == "bass"
    assert wait_for(lambda: any(c[:2] == ["set_property", "af"] and "equalizer=f=60" in c[2] for c in sent_commands(app)))
    assert client.get("/api/state").json["eq"]["gains"][0] == 6
    r = post(client, "/api/eq", {"gains": [1, 0, 0, 0, -2.2]})
    assert r.json["eq"]["preset"] == "custom" and r.json["eq"]["gains"][4] == -2.0
    r = post(client, "/api/eq", {"preset": "flat"})
    assert r.json["eq"]["preset"] == "flat"
    assert wait_for(lambda: sent_commands(app)[-1] == ["set_property", "af", ""])      # flat removes the filter
    for bad in ({"preset": "nope"}, {"gains": [0, 0, 0]}, {"gains": [0, 0, 0, 0, 99]}, {"gains": "x"}, {}):
        assert post(client, "/api/eq", bad).status_code == 400
    assert app.extensions["piplayer"].settings.get("eq") == [0.0] * 5


def test_equalizer_setting_is_saved_and_the_filter_is_safe(app, client):
    from piplayer import equalizer
    post(client, "/api/eq", {"preset": "vocal"})
    saved = app.extensions["piplayer"].settings.get("eq")
    assert saved == [-2.0, -1.0, 3.0, 3.0, 0.0] and equalizer.preset_for(saved) == "vocal"
    assert equalizer.build_filter(saved).startswith("lavfi=[volume=-2.1dB,equalizer=f=60")


def test_wrong_typed_fields_are_rejected_not_500(client):
    assert post(client, "/api/stations", {"title": 5, "url": "http://a"}).status_code == 400
    assert post(client, "/api/stations", {"title": "x", "url": ["http://a"]}).status_code == 400
    sid = post(client, "/api/stations", {"title": "x", "url": "http://a"}).json[-1]["id"]
    assert client.put(f"/api/stations/{sid}", json={"title": ["x"], "url": "http://a"}).status_code == 400
    assert post(client, "/api/playlists", {"name": "n", "items": 5}).status_code == 200      # a bad items value counts as empty


def test_shuffle_needs_a_real_boolean(client):
    assert post(client, "/api/control/shuffle", {"value": "false"}).status_code == 400
    assert post(client, "/api/control/shuffle", {"value": True}).status_code == 200
    assert client.get("/api/state").json["shuffle"] is True


def test_station_ids_are_never_reused_and_unknown_delete_is_404(client):
    first = post(client, "/api/stations", {"title": "A", "url": "http://a"}).json[-1]["id"]
    assert client.delete(f"/api/stations/{first}").status_code == 200
    second = post(client, "/api/stations", {"title": "B", "url": "http://b"}).json[-1]["id"]
    assert second != first
    assert client.delete("/api/stations/nope").status_code == 404


def test_listener_permit_is_returned_when_the_stream_never_starts(client, monkeypatch):
    from piplayer import api
    monkeypatch.setattr(api.shutil, "which", lambda name: "/bin/true")
    monkeypatch.setattr(api, "_listeners", api.threading.BoundedSemaphore(1))
    resp = client.get("/api/listen", buffered=False)         # not iterated: the generator never runs
    assert resp.status_code == 200
    assert not api._listeners.acquire(blocking=False)         # held while the response is open
    resp.close()
    assert api._listeners.acquire(blocking=False)             # and given back on close


def test_upstream_errors_are_not_leaked(app, client):
    svc = app.extensions["piplayer"]
    def boom(*a):
        raise RuntimeError("secret internal detail /home/pi/.venv")
    svc.search = boom
    r = client.get("/api/search?q=x")
    assert r.status_code == 502 and "secret" not in r.get_data(as_text=True)
    svc.trending = boom
    r = client.get("/api/trending")
    assert r.status_code == 502 and "secret" not in r.get_data(as_text=True)


def test_search_cache_survives_concurrent_use(app, client):
    import threading
    from piplayer import api
    svc = app.extensions["piplayer"]
    svc.search_yt = lambda q, kind: [{"kind": "yt", "id": "abcdefghijk", "title": q}]
    errors = []
    def hammer(n):
        try:
            with app.test_request_context():
                for i in range(150):
                    api._cached_search("youtube", f"q{n}-{i}")
        except Exception as e:                                 # "dictionary changed size during iteration"
            errors.append(e)
    ts = [threading.Thread(target=hammer, args=(n,)) for n in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not errors and len(api._search_cache) <= api.SEARCH_KEEP + 6


def test_event_streams_are_capped(client, monkeypatch):
    from piplayer import api
    monkeypatch.setattr(api, "_streams", api.threading.BoundedSemaphore(1))
    first = client.get("/api/events", buffered=False)
    assert first.status_code == 200
    assert client.get("/api/events").status_code == 503
    first.close()
    second = client.get("/api/events", buffered=False)
    assert second.status_code == 200
    second.close()


def test_corrupt_playlists_file_is_kept_not_overwritten(app, client):
    store = app.extensions["piplayer"].playlists
    store.path.write_text("{ not json")
    assert client.get("/api/playlists").json == []
    assert post(client, "/api/playlists", {"name": "New"}).status_code == 200
    assert len(list(store.path.parent.glob("playlists.json.bad-*"))) == 1       # the unreadable file is still there to recover from
    store.path.write_text('{"not": "a list"}')
    assert client.get("/api/playlists").json == []
    assert len(list(store.path.parent.glob("playlists.json.bad-*"))) >= 1


def test_unreadable_playlists_file_is_an_error_not_an_empty_list(app, client, monkeypatch):
    store = app.extensions["piplayer"].playlists
    post(client, "/api/playlists", {"name": "Keep me"})
    real_open = open
    def flaky(path, *a, **k):
        if str(path) == str(store.path):
            raise PermissionError("transient")
        return real_open(path, *a, **k)
    monkeypatch.setattr("builtins.open", flaky)
    try:
        store.all()
        assert False, "a failed read must raise"
    except PermissionError:
        pass
    monkeypatch.undo()
    assert [p["name"] for p in client.get("/api/playlists").json] == ["Keep me"]
