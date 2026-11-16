"""mpv-backed player with a queue. Talks to mpv over its JSON IPC socket.

Resilience:
  * mpv is supervised: if it dies it is restarted (with backoff) and the current track is resumed.
  * a track that fails to resolve or play is skipped; if every track in the queue fails in a row, playback stops.
  * a live radio stream that drops is retried a few times before giving up.
  * the next YouTube Music track is resolved in the background so songs follow each other without a gap.
"""
import json
import os
import random
import socket
import subprocess
import threading
import time

SINK = "@DEFAULT_AUDIO_SINK@"
DEFAULT_VOLUME = 70
RADIO_RETRIES = 3                  # reconnect attempts for a dropped live stream
RESTART_LIMIT = (3, 60)            # more than 3 mpv crashes in 60 s: restart it, but don't auto-resume playback


def _wpctl(*args):
    """Run wpctl; return stdout or None if unavailable/failed."""
    try:
        r = subprocess.run(["wpctl", *args], capture_output=True, text=True, timeout=3)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def get_system_volume():
    """Current system (PipeWire default sink) volume, 0-100, or None."""
    out = _wpctl("get-volume", SINK)
    try:
        return round(float(out.split()[1]) * 100)
    except (AttributeError, IndexError, ValueError):
        return None


class Player:
    def __init__(self, resolver, mpv_cmd=("mpv",), socket_path="/tmp/piplayer-mpv.sock",
                 volume=DEFAULT_VOLUME, on_change=None, on_play=None):
        self.resolver = resolver              # queue item -> playable URL (may block)
        self.mpv_cmd = list(mpv_cmd)
        self.socket_path = socket_path
        self.on_change = on_change or (lambda: None)
        self.on_play = on_play or (lambda item: None)     # called when a track starts loading into mpv
        self.lock = threading.RLock()
        self.queue = []
        self.index = -1
        self.state = {
            "playing": False, "paused": False, "loading": False,
            "volume": volume, "position": 0, "duration": None,
            "icy": None, "error": None, "held": False,
            "repeat": "off", "shuffle": False,
        }
        self._gen = 0                         # bumps on every play; stale loads are dropped
        self._played = set()                  # shuffle: indices already heard this round
        self._history = []                    # shuffle: where Previous goes back to
        self._fails = 0                       # consecutive tracks that failed to play
        self._retries = 0                     # reconnect attempts for the current live stream
        self._crashes = []                    # timestamps of recent mpv crashes
        self._closing = False
        self.watchers = 0                     # open browser tabs; external volume changes are only polled while > 0
        self._proc = None
        self._sock = None
        self._start_mpv()
        self._sys_target = None               # latest requested system volume, applied by one worker
        self._sys_event = threading.Event()
        threading.Thread(target=self._volume_worker, daemon=True, name="sys-volume").start()
        self.set_volume(volume)               # every start begins at the default; the user can raise it to 100

    # ---------- mpv process / IPC ----------
    def _start_mpv(self):
        old, self._proc = self._proc, None
        if old and old.poll() is None:
            old.kill()
        if old:
            old.wait()
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
        proc = subprocess.Popen(
            self.mpv_cmd + ["--idle=yes", "--no-video", "--no-terminal", "--force-window=no",
                            f"--input-ipc-server={self.socket_path}",
                            "--volume=100", "--volume-max=100",   # player stays at 100%; loudness is the system volume
                            "--cache=yes", "--demuxer-max-bytes=8MiB",
                            "--stream-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_delay_max=5"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if os.path.exists(self.socket_path):
                break
            time.sleep(0.1)
        else:
            proc.kill()
            proc.wait()
            raise RuntimeError("mpv did not create its IPC socket (is mpv installed?)")
        sock = socket.socket(socket.AF_UNIX)
        sock.connect(self.socket_path)
        with self.lock:
            self._proc, self._sock = proc, sock
        for i, prop in enumerate(["pause", "volume", "time-pos", "duration",
                                  "metadata", "idle-active", "core-idle"], 1):
            self._send(["observe_property", i, prop])
        threading.Thread(target=self._reader, args=(sock,), daemon=True, name="mpv-reader").start()

    def _send(self, cmd):
        """Send a command to mpv. Returns False (instead of raising) when mpv is gone; the supervisor restarts it."""
        with self.lock:
            try:
                self._sock.sendall((json.dumps({"command": cmd}) + "\n").encode())
                return True
            except (OSError, AttributeError):
                return False

    def _reader(self, sock):
        buf = b""
        while True:
            try:
                data = sock.recv(65536)
            except OSError:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    self._event(json.loads(line))
                except ValueError:
                    pass
                except Exception:             # a bad event must not kill the reader
                    pass
        self._mpv_died(sock)

    def _mpv_died(self, sock):
        with self.lock:
            if self._closing or sock is not self._sock:
                return
            was = self.state["playing"] or self.state["loading"]
            self._gen += 1
            self.state.update(playing=False, loading=False, paused=False, held=False, position=0,
                              duration=None, icy=None, error="Audio engine restarted")
            now = time.time()
            self._crashes = [t for t in self._crashes if now - t < RESTART_LIMIT[1]] + [now]
            resume = was and len(self._crashes) <= RESTART_LIMIT[0]
        self.on_change()
        threading.Thread(target=self._respawn, args=(resume,), daemon=True, name="mpv-respawn").start()

    def _respawn(self, resume):
        delay = 1
        while not self._closing:
            try:
                self._start_mpv()
                break
            except Exception:
                time.sleep(delay)
                delay = min(delay * 2, 30)
        else:
            return
        if resume and 0 <= self.index < len(self.queue):
            self.play_index(self.index)
        else:
            self.on_change()

    def _event(self, ev):
        s, name = self.state, ev.get("event")
        if name == "property-change":
            prop, val = ev.get("name"), ev.get("data")
            with self.lock:
                if prop == "pause":
                    s["paused"] = bool(val)
                elif prop == "volume":
                    return                    # mpv is pinned at 100; "volume" in state is the system volume
                elif prop == "time-pos":
                    s["position"] = val or 0
                    return                    # high frequency; clients tick locally
                elif prop == "duration":
                    s["duration"] = val
                elif prop == "metadata":
                    s["icy"] = (val or {}).get("icy-title")
                elif prop == "idle-active":
                    s["playing"] = not val
                elif prop == "core-idle":
                    s["loading"] = bool(val) and s["playing"] and not s["paused"]
            self.on_change()
        elif name == "file-loaded":
            with self.lock:
                self._fails = self._retries = 0           # something played: the streak is over
        elif name == "end-file":
            reason = ev.get("reason")
            if reason == "eof":
                if not self._retry_stream():
                    self.next(auto=True)
            elif reason == "error":
                if not self._retry_stream():
                    self._track_failed("Could not play this item")

    def _retry_stream(self):
        """A live radio stream ended on its own, which means the connection dropped: reconnect a few times."""
        with self.lock:
            cur = self.queue[self.index] if 0 <= self.index < len(self.queue) else None
            if not cur or cur.get("kind") != "radio" or self._retries >= RADIO_RETRIES:
                return False
            self._retries += 1
            wait, gen, i = 2 * self._retries, self._gen, self.index
            self.state.update(loading=True, error=None)

        def again():
            time.sleep(wait)
            if gen == self._gen and self.index == i and not self._closing:
                self.play_index(i, keep_retries=True)
        threading.Thread(target=again, daemon=True, name="radio-retry").start()
        self.on_change()
        return True

    def _track_failed(self, msg):
        """Skip a track that cannot be played; give up once the whole queue has failed in a row."""
        with self.lock:
            self._fails += 1
            exhausted = self._fails >= max(len(self.queue), 1)
            self.state.update(loading=False, error=msg)
        if exhausted:
            with self.lock:
                self._gen += 1
                self._fails = 0
            self._send(["stop"])
            self.on_change()
        else:
            self.next()

    # ---------- queue / transport ----------
    def play_index(self, i, back=False, keep_retries=False):
        with self.lock:
            if not 0 <= i < len(self.queue):
                return
            if not back and 0 <= self.index != i:
                self._history = (self._history + [self.index])[-100:]
            self._played.add(i)
            self.index = i
            self._gen += 1
            if not keep_retries:
                self._retries = 0
            gen, item = self._gen, self.queue[i]
            held = self.state["held"]
            self.state.update(loading=True, error=None, icy=None, position=0, duration=None, held=False)
        if held:
            self._send(["set_property", "mute", False])
        self.on_change()
        threading.Thread(target=self._load, args=(gen, item), daemon=True).start()

    def _load(self, gen, item):
        try:
            url = self.resolver(item)
        except Exception as e:
            if gen == self._gen:
                self._track_failed(f"Resolve failed: {e}"[:200])
            return
        if gen != self._gen:
            return                            # user moved on while we were resolving
        self._send(["loadfile", url, "replace"])
        self._send(["set_property", "pause", False])
        try:
            self.on_play(item)
        except Exception:
            pass                              # history must never break playback
        self._prefetch(gen)

    def _prefetch(self, gen):
        """Resolve the next YouTube Music / SoundCloud track now (the resolver caches it) so the change-over has no gap."""
        with self.lock:
            if self.state["shuffle"] or self.state["repeat"] == "one":
                return
            nxt = self.queue[self.index + 1] if 0 <= self.index + 1 < len(self.queue) else None
        if not nxt or nxt.get("kind") not in ("ytm", "yt", "sc"):
            return

        def warm():
            try:
                if gen == self._gen:
                    self.resolver(nxt)
            except Exception:
                pass                          # a failure here shows up properly when the track is actually played
        threading.Thread(target=warm, daemon=True, name="prefetch").start()

    def play_now(self, items):
        with self.lock:
            self.queue = list(items)
            self.index, self._played, self._history, self._fails = -1, set(), [], 0
        self.play_index(0)

    def add(self, items):
        with self.lock:
            start = len(self.queue)
            self.queue.extend(items)
            idle = not self.state["playing"] and not self.state["loading"]
        if idle:
            self.play_index(start)
        else:
            self.on_change()

    def remove(self, i):
        with self.lock:
            if not 0 <= i < len(self.queue):
                return
            del self.queue[i]
            self._played, self._history = set(), []      # indices shifted; start the shuffle round afresh
            if i < self.index:
                self.index -= 1
            elif i == self.index:
                self.index -= 1               # next() then lands on the follower
                self._gen += 1
                self._send(["stop"])
                self.next()
                return
        self.on_change()

    def _pick_next(self, auto):
        """Index to play after the current one, or None when the queue is finished."""
        n, cur, mode = len(self.queue), self.index, self.state["repeat"]
        if n == 0:
            return None
        if auto and mode == "one" and 0 <= cur < n:
            return cur
        if self.state["shuffle"]:
            fresh = [i for i in range(n) if i not in self._played and i != cur]
            if not fresh and mode == "all":
                self._played = {cur}              # everything heard: reshuffle a new round
                fresh = [i for i in range(n) if i != cur] or [cur]
            return random.choice(fresh) if fresh else None
        if cur + 1 < n:
            return cur + 1
        return 0 if mode == "all" else None

    def move(self, frm, to):
        """Reorder the queue (drag and drop). The playing track keeps playing; only its index follows it."""
        with self.lock:
            n = len(self.queue)
            if not (0 <= frm < n and 0 <= to < n) or frm == to:
                return
            self.queue.insert(to, self.queue.pop(frm))
            cur = self.index
            if cur == frm:
                self.index = to
            elif frm < cur <= to:
                self.index -= 1
            elif to <= cur < frm:
                self.index += 1
            self._played = {self.index} if self.index >= 0 else set()
            self._history = []
        self.on_change()

    def clear(self, upcoming_only=True):
        """Drop everything after the current track, or (upcoming_only=False) empty the queue and stop."""
        with self.lock:
            if upcoming_only:
                del self.queue[self.index + 1:]
            else:
                self.queue, self.index = [], -1
                self._gen += 1
                self.state.update(loading=False, icy=None, error=None)
                self._send(["stop"])
            self._played = {self.index} if self.index >= 0 else set()
            self._history = []
        self.on_change()

    def next(self, auto=False):
        with self.lock:
            nxt = self._pick_next(auto)
            if nxt is not None:
                self.play_index(nxt)
            else:
                self._gen += 1
                self.state.update(loading=False, icy=None)
                self._send(["stop"])
                self.on_change()

    def prev(self):
        with self.lock:
            if self.state["position"] > 5 or self.index <= 0 and not self._history:
                self._send(["seek", 0, "absolute"])
            elif self.state["shuffle"] and self._history:
                self.play_index(self._history.pop(), back=True)
            elif self.index > 0:
                self.play_index(self.index - 1)
            else:
                self._send(["seek", 0, "absolute"])

    def set_repeat(self, mode):
        mode = mode if mode in ("off", "all", "one") else "off"
        with self.lock:
            self.state["repeat"] = mode
        self.on_change()
        return mode

    def set_shuffle(self, on):
        with self.lock:
            self.state["shuffle"] = bool(on)
            self._played = {self.index} if self.index >= 0 else set()
        self.on_change()
        return bool(on)

    def toggle(self):
        if self.state["held"]:
            self.hold(False)
        else:
            self._send(["cycle", "pause"])

    def stop(self):
        with self.lock:
            self._gen += 1
            held, self.state["loading"], self.state["held"] = self.state["held"], False, False
        if held:
            self._send(["set_property", "mute", False])
        self._send(["stop"])

    def pause(self, paused=True):
        self._send(["set_property", "pause", bool(paused)])

    def hold(self, on=True):
        """Silence a LIVE stream without pausing it. A paused radio stream is dropped by the server
        after ~1 min and would need a ~4 s reconnect; a silent one resumes instantly and is still live."""
        self._send(["set_property", "mute", bool(on)])    # command first: state must never claim more than mpv was told
        with self.lock:
            self.state["held"] = bool(on)
        self.on_change()

    DUCK_LEVEL = 30                           # mpv's own volume (%) while an announcement is spoken over the music
    DUCK_DOWN, DUCK_UP = 0.3, 1.8             # seconds: dip quickly so the voice is clear, come back up slowly
    DUCK_STEPS = 12
    DUCK_SCALE = 1.0                          # tests shrink this

    def duck(self, on=True, level=None, up=None):
        """Lower the music (mpv's own volume, not the system volume) so a spoken message is clear, then raise it back
        GRADUALLY. The system volume stays untouched, so this never fights the volume slider or the door fade-in.
        A new duck() call takes over from wherever the previous one had got to."""
        with self.lock:
            self._duck_gen = getattr(self, "_duck_gen", 0) + 1
            gen, start = self._duck_gen, getattr(self, "_duck_now", 100)
        level = self.DUCK_LEVEL if level is None else max(0, min(100, int(level)))     # how far the music dips (%)
        goal, secs = (level, self.DUCK_DOWN) if on else (100, self.DUCK_UP if up is None else up)    # up: seconds to come back
        threading.Thread(target=self._duck_ramp, args=(gen, start, goal, secs * self.DUCK_SCALE),
                         daemon=True, name="duck").start()

    def _duck_ramp(self, gen, start, goal, secs):
        n = self.DUCK_STEPS
        for i in range(1, n + 1):
            frac = i / n
            level = round(start + (goal - start) * (frac if goal < start else frac * frac))   # up: slow start, perceptually even
            with self.lock:
                if gen != self._duck_gen:
                    return                    # superseded by a newer duck()
                self._duck_now = level
            self._send(["set_property", "volume", level])
            if i < n:
                time.sleep(secs / n)

    def seek(self, seconds):
        self._send(["seek", float(seconds), "absolute"])

    def set_volume(self, v):
        """Set the SYSTEM volume. Requests coalesce: a slider drag results in ordered, latest-wins updates."""
        v = max(0, min(100, int(v)))
        with self.lock:
            self.state["volume"] = v
            self._sys_target = v
        self._sys_event.set()
        self.on_change()
        return v

    def _volume_worker(self):
        while not self._closing:
            # wake on a request, or every 2s to pick up volume changed outside the app
            self._sys_event.wait(2.0)
            self._sys_event.clear()
            with self.lock:
                target, self._sys_target = self._sys_target, None
            if target is not None:
                _wpctl("set-volume", SINK, f"{target}%")
                time.sleep(0.05)              # cap at ~20 updates/s
                continue
            if self.watchers <= 0:
                continue                      # nobody is looking: don't spawn wpctl for nothing
            cur = get_system_volume()
            with self.lock:
                if cur is None or cur == self.state["volume"] or self._sys_target is not None:
                    continue
                self.state["volume"] = cur
            self.on_change()

    # ---------- persistence ----------
    def persisted(self):
        """What survives a restart: the queue, where we were in it, and the repeat/shuffle modes."""
        with self.lock:
            return {"queue": list(self.queue), "index": self.index,
                    "repeat": self.state["repeat"], "shuffle": self.state["shuffle"]}

    def restore(self, queue, index, repeat="off", shuffle=False):
        """Load a saved queue without playing it."""
        with self.lock:
            self.queue = list(queue)
            self.index = index if isinstance(index, int) and 0 <= index < len(self.queue) else -1
            self.state["repeat"] = repeat if repeat in ("off", "all", "one") else "off"
            self.state["shuffle"] = bool(shuffle)
            self._played = {self.index} if self.index >= 0 else set()

    def snapshot(self):
        with self.lock:
            cur = self.queue[self.index] if 0 <= self.index < len(self.queue) else None
            return {**self.state, "paused": self.state["paused"] or self.state["held"], "current": cur, "queue": list(self.queue), "index": self.index}

    def close(self):
        self._closing = True
        self._send(["quit"])
        if self._proc:
            self._proc.terminate()
