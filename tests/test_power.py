from piplayer import api


def test_shutdown_and_reboot(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "_run_power", lambda cmd: calls.append(cmd) or True)
    assert client.post("/api/system/shutdown", json={}).get_json() == {"ok": True}
    assert client.post("/api/system/reboot", json={}).status_code == 200
    assert calls == ["poweroff", "reboot"]


def test_power_denied_and_unknown(client, monkeypatch):
    monkeypatch.setattr(api, "_run_power", lambda cmd: False)
    assert client.post("/api/system/shutdown", json={}).status_code == 403
    assert client.post("/api/system/halt", json={}).status_code == 404


def test_power_rejects_non_json(client, monkeypatch):
    monkeypatch.setattr(api, "_run_power", lambda cmd: (_ for _ in ()).throw(AssertionError("must not run")))
    assert client.post("/api/system/shutdown").status_code == 415
    assert client.post("/api/system/shutdown", data="x", content_type="text/plain").status_code == 415
