"""HTTP API (JSON + server-sent events)."""
import ipaddress
import json
import math
import os
import shutil
import subprocess
import threading
from urllib.parse import urlparse

from flask import Blueprint, Response, current_app, jsonify, request

from .playlists import clean_items
from .stations import as_queue_item

bp = Blueprint("api", __name__, url_prefix="/api")


def _svc():
    return current_app.extensions["piplayer"]


def _body():
    """The JSON request body as a dict (anything else counts as empty)."""
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


def _num(v):
    """A finite float, or None."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def _local_name(host):
    """Is this Host header a name a person on the LAN would type? Blocks DNS-rebinding from the open internet."""
    try:
        name = urlparse("//" + host).hostname or ""
    except ValueError:
        return False
    if not name:
        return False
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    extra = {h.strip().lower() for h in os.environ.get("PIPLAYER_ALLOWED_HOSTS", "").split(",") if h.strip()}
    name = name.lower()
    return name == "localhost" or name.endswith(".local") or "." not in name or name in extra


@bp.before_request
def _guard():
    if not _local_name(request.host):
        return jsonify(error="unknown host"), 403
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("Origin")           # browsers send it on cross-site writes
        if origin and urlparse(origin).netloc != request.host:
            return jsonify(error="cross-origin request refused"), 403


def _snapshot(svc=None):
    svc = svc or _svc()          # the SSE generator passes it in: no request context exists while streaming
    return {**svc.player.snapshot(), "bathrooms": svc.bathrooms.snapshot(),
            "doors": svc.bathrooms.config()}


@bp.get("/state")
def state():
    return jsonify(_snapshot())


@bp.get("/events")
def events():
    svc = _svc()

    def stream():
        seen = -1
        with svc.player.lock:
            svc.player.watchers += 1                     # while someone is watching, outside volume changes are polled
        try:
            while True:
                with svc.changed:
                    svc.changed.wait_for(lambda: svc.version != seen, timeout=15)
                    fresh = svc.version != seen
                    seen = svc.version
                yield f"data: {json.dumps(_snapshot(svc))}\n\n" if fresh else ": keepalive\n\n"
        finally:
            with svc.player.lock:
                svc.player.watchers -= 1

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- stations ----
@bp.get("/stations")
def stations():
    return jsonify(_svc().stations.all())


@bp.post("/stations")
def add_station():
    d = _body()
    title, url = (d.get("title") or "").strip(), (d.get("url") or "").strip()
    if not title or not url.startswith(("http://", "https://")):
        return jsonify(error="title and http(s) url required"), 400
    return jsonify(_svc().stations.add(title, url))


@bp.put("/stations/<sid>")
def update_station(sid):
    d = _body()
    title, url = (d.get("title") or "").strip(), (d.get("url") or "").strip()
    if not title or not url.startswith(("http://", "https://")):
        return jsonify(error="title and http(s) url required"), 400
    items = _svc().stations.update(sid, title, url)
    return (jsonify(items), 200) if items is not None else (jsonify(error="unknown station"), 404)


@bp.delete("/stations/<sid>")
def delete_station(sid):
    return jsonify(_svc().stations.remove(sid))


# ---- listen on another device (phone / laptop) ----
# Taps the Pi's audio output (a PipeWire sink monitor, captured before the system volume) and sends it as MP3,
# so the browser plays exactly what the Pi plays, for radio and music alike.
MAX_LISTENERS = 4
_listeners = threading.BoundedSemaphore(MAX_LISTENERS)
_REC = ["pw-record", "--rate", "44100", "--channels", "2", "--format", "s16", "--raw",
        "-P", "{ stream.capture.sink=true }", "-"]
_ENC = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-fflags", "nobuffer", "-probesize", "32", "-analyzeduration", "0", "-f", "s16le", "-ar", "44100",
        "-ac", "2", "-i", "-", "-c:a", "libmp3lame", "-b:a", "128k", "-flush_packets", "1", "-f", "mp3", "-"]


@bp.get("/listen")
def listen():
    if not (shutil.which("pw-record") and shutil.which("ffmpeg")):
        return jsonify(error="pw-record and ffmpeg are required for listening on another device"), 503
    if not _listeners.acquire(blocking=False):
        return jsonify(error="too many listeners"), 503

    def stream():
        rec = enc = None
        try:
            rec = subprocess.Popen(_REC, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            enc = subprocess.Popen(_ENC, stdin=rec.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            rec.stdout.close()
            while True:
                chunk = os.read(enc.stdout.fileno(), 4096)
                if not chunk:
                    break
                yield chunk
        finally:                          # runs when the browser disconnects (GeneratorExit)
            for p in (enc, rec):
                if p:
                    p.kill()
                    p.wait()
            _listeners.release()

    return Response(stream(), mimetype="audio/mpeg",
                    headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


# ---- playlists ----
def _pl_name(d):
    return str(d.get("name") or "").strip()[:80]


@bp.get("/playlists")
def playlists():
    return jsonify(_svc().playlists.all())


@bp.post("/playlists")
def playlist_create():
    d = _body()
    name = _pl_name(d)
    if not name:
        return jsonify(error="name required"), 400
    _svc().playlists.create(name, d.get("items") or [])
    return jsonify(_svc().playlists.all())


@bp.put("/playlists/<pid>")
def playlist_rename(pid):
    name = _pl_name(_body())
    if not name:
        return jsonify(error="name required"), 400
    if _svc().playlists.rename(pid, name) is None:
        return jsonify(error="unknown playlist"), 404
    return jsonify(_svc().playlists.all())


@bp.delete("/playlists/<pid>")
def playlist_delete(pid):
    _svc().playlists.delete(pid)
    return jsonify(_svc().playlists.all())


@bp.post("/playlists/<pid>/items")
def playlist_add(pid):
    if _svc().playlists.add_items(pid, (_body()).get("items", [])) is None:
        return jsonify(error="unknown playlist"), 404
    return jsonify(_svc().playlists.all())


@bp.delete("/playlists/<pid>/items/<int:i>")
def playlist_remove_item(pid, i):
    if _svc().playlists.remove_item(pid, i) is None:
        return jsonify(error="unknown playlist"), 404
    return jsonify(_svc().playlists.all())


# ---- search ----
@bp.get("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    kind = request.args.get("type", "songs")
    try:
        source = request.args.get("source")
        if source == "soundcloud":
            return jsonify(_svc().search_sc(q, "songs"))
        if source == "youtube":
            return jsonify(_svc().search_yt(q, "songs"))
        return jsonify(_svc().search(q, kind if kind in ("songs", "videos") else "songs"))
    except Exception as e:
        return jsonify(error=str(e)), 502


@bp.get("/trending")
def trending():
    """The country's YouTube Music chart (cached for an hour)."""
    try:
        return jsonify(_svc().trending())
    except Exception as e:
        return jsonify(error=str(e)), 502


@bp.get("/history")
def history():
    h = _svc().history
    return jsonify(recent=h.recent(8), top=h.top(8))


@bp.delete("/history")
def clear_history():
    """Forget the play history (suggestions start again from the trending chart)."""
    _svc().history.clear()
    return jsonify(ok=True)


@bp.get("/suggested")
def suggested():
    """Related-to-what-was-played tracks mixed with the country's trending chart, minus tracks already played.
    A fresh install (no history) gets trending alone; if that fails too, a generic search."""
    svc = _svc()

    def attempt(fn, *a):
        try:
            return fn(*a)
        except Exception:
            return []

    seeds = svc.history.seeds()
    related = attempt(svc.suggest, seeds) if seeds else []
    trend = attempt(svc.trending)
    played = {e["id"] for e in svc.history.recent(50)}
    out, seen = [], set()
    for i in range(max(len(related), len(trend))):            # alternate related / trending
        for lst in (related, trend):
            if i < len(lst) and lst[i]["id"] not in seen and lst[i]["id"] not in played:
                seen.add(lst[i]["id"])
                out.append(lst[i])
    if not out:
        try:
            out = svc.search("top hits", "songs")
        except Exception as e:
            return jsonify(error=str(e)), 502
    return jsonify(out[:10])


# ---- playback ----
@bp.post("/play")
def play():
    svc, d = _svc(), _body()
    if d.get("station"):
        st = svc.stations.get(d["station"])
        if not st:
            return jsonify(error="unknown station"), 404
        svc.player.play_now([as_queue_item(st)])
    elif d.get("playlist"):
        pl = svc.playlists.get(d["playlist"])
        if not pl or not pl["items"]:
            return jsonify(error="playlist is empty or unknown"), 404
        n = _num(d.get("from", 0))
        start = max(0, min(int(n or 0), len(pl["items"]) - 1))
        items = clean_items(pl["items"][start:])
        if not items:
            return jsonify(error="playlist has no playable items"), 404
        svc.player.play_now(items)
    elif d.get("items"):
        items = clean_items(d["items"])
        if not items:
            return jsonify(error="no playable items"), 400
        svc.player.play_now(items)
    elif "index" in d:
        n = _num(d["index"])
        if n is None:
            return jsonify(error="index must be a number"), 400
        svc.player.play_index(int(n))
    else:
        return jsonify(error="nothing to play"), 400
    return jsonify(ok=True)


@bp.post("/queue")
def queue_add():
    items = clean_items(_body().get("items"))
    if not items:
        return jsonify(error="no playable items"), 400
    _svc().player.add(items)
    return jsonify(ok=True)


@bp.post("/queue/move")
def queue_move():
    d = _body()
    try:
        _svc().player.move(int(d["from"]), int(d["to"]))
    except (KeyError, TypeError, ValueError):
        return jsonify(error="from and to required"), 400
    return jsonify(ok=True)


@bp.post("/queue/clear")
def queue_clear():
    d = _body()
    _svc().player.clear(upcoming_only=d.get("scope", "upcoming") != "all")
    return jsonify(ok=True)


@bp.delete("/queue/<int:i>")
def queue_remove(i):
    _svc().player.remove(i)
    return jsonify(ok=True)


@bp.post("/control/<action>")
def control(action):
    svc, d = _svc(), _body()
    p = svc.player
    simple = {"toggle": p.toggle, "next": p.next, "prev": p.prev, "stop": p.stop}
    if action in simple:
        simple[action]()
    elif action == "seek" and _num(d.get("seconds")) is not None:
        p.seek(max(0.0, _num(d["seconds"])))
    elif action == "volume" and _num(d.get("value")) is not None:
        svc.settings.set("volume", p.set_volume(int(_num(d["value"]))))
    elif action == "repeat" and "value" in d:
        p.set_repeat(d["value"])
    elif action == "shuffle" and "value" in d:
        p.set_shuffle(d["value"])
    else:
        return jsonify(error="bad action"), 400
    return jsonify(ok=True)


# ---- system power ----
def _run_power(action):
    """Run `systemctl poweroff|reboot`, falling back to passwordless sudo. True on success."""
    for cmd in (["systemctl", action], ["sudo", "-n", "systemctl", action]):
        try:
            if subprocess.run(cmd, capture_output=True, timeout=15).returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


@bp.post("/system/<action>")
def system_power(action):
    if not request.is_json:        # cross-site forms/fetches can't send JSON without a CORS preflight, which we never grant
        return jsonify(error="JSON required"), 415
    if action not in ("shutdown", "reboot"):
        return jsonify(error="unknown action"), 404
    cmd = "poweroff" if action == "shutdown" else "reboot"
    if not _run_power(cmd):
        return jsonify(error=f"Not allowed to {action}: let the service user run "
                             f"`systemctl {cmd}` (polkit or sudoers)."), 403
    return jsonify(ok=True)


# ---- bathroom door sensors ----
@bp.post("/doors")
def doors():
    err = _svc().bathrooms.configure(_body())
    return (jsonify(error=err), 400) if err else jsonify(ok=True)


@bp.post("/doors/announce")
def doors_announce():
    """Preview a saved door message on the speakers: {"which": "welcome" | "reminder"}."""
    err = _svc().bathrooms.announce_now(_body().get("which"))
    return (jsonify(error=err), 400) if err else jsonify(ok=True)
