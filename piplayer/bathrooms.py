"""Bathroom door sensors: live occupancy for the dashboard, plus optional "music while in use".

Wiring: reed switch between a GPIO pin and GND (internal pull-up), magnet on the door.
Door closed -> magnet near -> pin low -> room OCCUPIED. Without a working sensor a room is unknown (None).

Autoplay (off by default): between `from` and `to`, the player queue plays while at least one door is
closed; when both are open it PAUSES whatever is playing, and resumes it when a door closes again. Radio
is kept connected but silent (a paused stream is dropped by the server and would take seconds to reconnect), and
is stopped when the hours end. It reacts to changes only (a door opening/closing, the hours boundary, or the switch being turned on),
so pressing play/pause yourself in between is respected until the next change.

Fade-in: when a door closing starts or resumes the music, the volume drops to a low level and is raised gradually to what
it was (`fade` seconds, 0 = off). Moving the volume yourself during a fade ends it; the volume is put back if the door
opens again halfway.

Announcements: when a door closes a welcome message is spoken (then the music starts and fades in); when a door opens a
reminder is spoken (after the music paused, or over it, ducked). Only inside the active hours, never at start-up or when a
sensor is rewired, and each message can be edited or emptied. Speech comes from piplayer/speech.py (espeak-ng).

Watchdog: a plain reed switch can't report that it was unplugged, so a room whose sensor shows no
change for STALE_AFTER of opening time is flagged `stale` ("check sensor") in the snapshot.

Configuration lives in the shared settings store (key "bathrooms"), is pushed to the UI inside the
normal state stream, and is edited through POST /api/doors, like volume.
"""
import datetime
import logging
import threading
import time

from . import speech
from .stations import as_queue_item

log = logging.getLogger("piplayer.bathrooms")
ROOMS = ("male", "female")
BCM_PINS = range(2, 28)                       # usable GPIOs on the 40-pin header
STALE_AFTER = 4 * 3600                        # seconds of opening time without a change before "check sensor"
DEFAULTS = {"autoplay": False, "from": "08:00", "to": "18:00", "fade": 5, "fadeout": 3, "announce": True,
            "welcome": "Thank you for choosing Cytron DJ. Enjoy the vibe!",
            "reminder": "Please remember to flush and keep it clean.",
            "duck": 30, "rise": 2, "voice": ""}
MESSAGE_MAX = 160                             # characters per announcement
FADE_START = 0.08                             # a fade begins at this fraction of the normal volume
FADE_STEPS = 20                               # volume updates per fade
FADE_CURVE = 2.0                              # >1: starts gently; loudness is felt logarithmically, so a straight line sounds like a jump


def _gpio_button(pin):
    from gpiozero import Button               # imported lazily: only needed with sensors
    return Button(pin, pull_up=True, bounce_time=0.05)


def _hhmm(s):
    return datetime.datetime.strptime(s, "%H:%M").time()


class Bathrooms:
    FADE_SCALE = 1.0                      # tests shrink this to run a fade in milliseconds

    def __init__(self, svc, button_factory=_gpio_button, clock=datetime.datetime.now):
        self.svc, self._factory, self._clock = svc, button_factory, clock
        self._lock = threading.Lock()         # guards room readings
        self._eval_lock = threading.Lock()    # serialises autoplay decisions
        self._rooms = {r: {"occupied": None, "since": None} for r in ROOMS}
        self._buttons = []                    # keep gpiozero objects alive
        self._pins, self.error = {}, None
        self._playing = None                  # autoplay edge state: None = unknown / switched off
        self._paused = None                   # (kind, id) of the item autoplay paused, to resume it
        self.speaker = speech.speak           # text -> speech (replaced in tests)
        self.preparer = speech.prepare        # texts -> rendered ahead of time (replaced in tests)
        self._ducked = False                  # the music is dipped for a message (guarded by _speech_lock)
        self._speech_ok = speech.available
        self._speech_lock = threading.Lock()  # one announcement at a time; a second one is skipped, not queued
        self._fade_lock = threading.Lock()    # guards the running fade
        self._fade_stop = None                # Event that ends the running fade
        self._fade_target = None              # the volume a running fade is heading for (to restore it if cut short)
        self._out_idle = threading.Event()    # set whenever NO fade-out is running (the reminder waits for it)
        self._out_idle.set()

    # ---------- configuration ----------
    def config(self):
        saved = self.svc.settings.get("bathrooms") or {}
        pins = saved["pins"] if "pins" in saved else dict(self.svc.cfg.bathroom_pins)   # saved {} = deliberately none
        return {"pins": pins, "active": sorted(self._pins), "error": self.error, "speech": bool(self._speech_ok()), "engine": speech.engine(), "voices": speech.voices(),
                **{k: saved.get(k, v) for k, v in DEFAULTS.items()}}

    def configure(self, patch):
        """Validate and apply a partial update. Returns an error message, or None."""
        saved = dict(self.svc.settings.get("bathrooms") or {})
        if "pins" in patch:
            try:
                pins = {r: int(patch["pins"][r]) for r in ROOMS if patch["pins"].get(r) not in (None, "")}
            except (TypeError, ValueError, AttributeError):
                return "Pins must be numbers"
            if any(p not in BCM_PINS for p in pins.values()):
                return "Pins must be BCM GPIO numbers 2-27"
            if len(set(pins.values())) != len(pins):
                return "Each room needs its own pin"
            saved["pins"] = pins
        for key in ("from", "to"):
            if key in patch:
                try:
                    _hhmm(patch[key])
                except (TypeError, ValueError):
                    return "Times must be HH:MM"
                saved[key] = patch[key]
        if "autoplay" in patch:
            saved["autoplay"] = bool(patch["autoplay"])
        if "announce" in patch:
            saved["announce"] = bool(patch["announce"])
        for key in ("welcome", "reminder"):
            if key in patch:
                if not isinstance(patch[key], str):
                    return "Messages must be text"
                text = " ".join(patch[key].split())
                if len(text) > MESSAGE_MAX:
                    return f"Messages can be at most {MESSAGE_MAX} characters"
                saved[key] = text
        if "duck" in patch:
            try:
                duck = int(patch["duck"])
            except (TypeError, ValueError):
                return "Music level during a message must be a number"
            if not 0 <= duck <= 100:
                return "Music level during a message must be 0-100 %"
            saved["duck"] = duck
        if "rise" in patch:
            try:
                rise = float(patch["rise"])
            except (TypeError, ValueError):
                return "Return time must be a number of seconds"
            if not 0 <= rise <= 30:
                return "Return time must be 0-30 seconds"
            saved["rise"] = rise
        if "voice" in patch:
            if not isinstance(patch["voice"], str) or (patch["voice"] and patch["voice"] not in speech.voices()):
                return "That voice is not installed"
            saved["voice"] = patch["voice"]
        if "fadeout" in patch:
            try:
                fadeout = int(patch["fadeout"])
            except (TypeError, ValueError):
                return "Fade-out must be a number of seconds"
            if not 0 <= fadeout <= 60:
                return "Fade-out must be 0-60 seconds"
            saved["fadeout"] = fadeout
        if "fade" in patch:
            try:
                fade = int(patch["fade"])
            except (TypeError, ValueError):
                return "Fade-in must be a number of seconds"
            if not 0 <= fade <= 60:
                return "Fade-in must be 0-60 seconds"
            saved["fade"] = fade
        self.svc.settings.set("bathrooms", saved)
        speech.use_voice(saved.get("voice", ""))
        if "pins" in patch:
            self.start()
        if "welcome" in patch or "reminder" in patch or "voice" in patch:
            self.prewarm()                    # render the edited message now, not at the door
        self.evaluate()
        self.svc.notify()
        return None

    # ---------- occupancy ----------
    def set(self, room, occupied):
        with self._lock:
            cur = self._rooms[room]
            if cur["occupied"] == occupied:
                return
            before = cur["occupied"]
            cur["occupied"], cur["since"] = occupied, time.time()
        self.svc.notify()
        kind = self._announcement(before, occupied)
        if kind == "welcome":                 # a door closed: say hello first, then the music starts (and fades in)
            threading.Thread(target=self._welcome, daemon=True, name="announce").start()
            return
        self.evaluate()
        if kind:                              # a door opened: the music has paused by now, then the reminder is spoken
            threading.Thread(target=self._remind, daemon=True, name="announce").start()

    def snapshot(self):
        with self._lock:
            rooms = [{"id": r, "occupied": v["occupied"], "since": v["since"]} for r, v in self._rooms.items()]
        for r in rooms:
            r["stale"] = r["id"] in self._pins and r["occupied"] is not None and self._stale(r["since"])
        return rooms

    def _stale(self, since):
        """True when no change was seen for STALE_AFTER of opening time (never outside the hours)."""
        c, now = self.config(), self._clock()
        a, b = _hhmm(c["from"]), _hhmm(c["to"])
        if since is None or not a <= now.time() <= b:      # (overnight ranges are not watched)
            return False
        opened = now.replace(hour=a.hour, minute=a.minute, second=0, microsecond=0).timestamp()
        return now.timestamp() - max(since, opened) > STALE_AFTER

    def start(self):
        """(Re)open the sensors from the current config. Never raises: failures land in .error."""
        self._release()
        self.error = None
        for room in ROOMS:                    # drop readings of the previous wiring
            self.set(room, None)
        try:
            for room, pin in self.config()["pins"].items():
                b = self._factory(pin)
                b.when_pressed = lambda r=room: self.set(r, True)      # door closed
                b.when_released = lambda r=room: self.set(r, False)    # door open
                self._buttons.append(b)
                self._pins[room] = pin
                self.set(room, bool(b.is_pressed))
        except Exception as e:                # no gpiozero, pin busy, no permission...
            self._release()
            self.error = f"{type(e).__name__}: {e}"[:200]
        self.svc.notify()

    def _release(self):
        buttons, self._buttons, self._pins = self._buttons, [], {}
        for b in buttons:
            try:
                b.close()
            except Exception:
                pass

    # ---------- autoplay ----------
    def _in_hours(self):
        c = self.config()
        now, a, b = self._clock().time(), _hhmm(c["from"]), _hhmm(c["to"])
        return a <= now <= b if a <= b else (now >= a or now <= b)       # allows overnight

    def _wanted(self):
        return (self.config()["autoplay"] and self._in_hours()
                and any(r["occupied"] is True for r in self.snapshot()))

    def evaluate(self):
        with self._eval_lock:
            if not self.config()["autoplay"]:
                if self._paused and self.svc.player.snapshot()["held"]:
                    self.svc.player.hold(False)           # don't leave a radio stream silent with nobody to wake it
                self._playing = self._paused = None       # switched off: forget state, touch nothing else
                self._fade_cancel()
                return
            want = self._wanted()
            if want == self._playing:
                return
            self._playing = want
            if want and not self._out_idle.is_set():
                self._fade_cancel()                       # someone is back mid fade-out: the music carries on at your volume
            (self._play if want else self._halt)()

    def _key(self, snap):
        cur = snap["current"]
        return (cur["kind"], cur["id"]) if cur else None

    def _play(self):
        try:
            self._start_music()
        finally:
            if self._speech_lock.locked() and not self._ducked:
                self._duck_music(True)             # music that starts while a message is being spoken stays under the voice

    def _start_music(self):
        p = self.svc.player
        snap = p.snapshot()
        if self._paused and snap["paused"] and self._key(snap) == self._paused:    # we silenced/paused it: carry on
            self._paused = None
            self._fade_begin()
            (p.hold if snap["current"]["kind"] == "radio" else p.pause)(False)     # instant either way
            return
        self._paused = None
        if snap["playing"] or snap["loading"]:
            return                                         # already playing something
        if snap["queue"]:
            self._fade_begin()
            p.play_index(snap["index"] if 0 <= snap["index"] < len(snap["queue"]) else 0)
        elif (st := next(iter(self.svc.stations.all()), None)):        # empty queue: first station
            self._fade_begin()
            p.play_now([as_queue_item(st)])

    def _halt(self):
        if self._fade_out():
            return                                         # the fade-out pauses it when it is done
        try:
            self._silence()
        finally:
            self._fade_cancel()                            # after the pause/mute went out: no loud blip

    def _silence(self):
        p = self.svc.player
        snap = p.snapshot()
        if not ((snap["playing"] or snap["loading"]) and not snap["paused"]):
            return
        live = snap["current"] and snap["current"]["kind"] == "radio"
        if live and not self._in_hours():
            p.stop()                                       # closed for the night: don't stream for nothing
        else:
            self._paused = self._key(snap)
            (p.hold if live else p.pause)(True)            # radio: keep the stream, silent -> instant + live

    # ---------- announcements ----------
    def _text(self, kind):
        return " ".join(str(self.config().get(kind) or "").split())

    def _announcement(self, before, occupied):
        """'welcome' (a door closed) or 'reminder' (a door opened) when something should be said, else None.
        Never for the first reading after start-up or a rewire (before / after is None), never outside the hours."""
        if before is None or occupied is None:
            return None
        kind = "welcome" if occupied else "reminder"
        if not self.config()["announce"] or not self._text(kind) or not self._in_hours() or not self._speech_ok():
            return None
        return kind

    def _remind(self):
        self._out_idle.wait(self.config()["fadeout"] * self.FADE_SCALE + 2)     # let the music fade out and pause first
        self._say(self._text("reminder"))

    def _welcome(self):
        try:
            self._say(self._text("welcome"))
        finally:
            self.evaluate()                   # start / resume the music (with the fade-in) once the welcome is done

    def _say(self, text):
        """Speak `text` over the speakers, ducking the music while it plays. Returns False if it was skipped."""
        if not text or not self._speech_ok() or not self._speech_lock.acquire(blocking=False):
            return False
        p = self.svc.player
        try:
            self._fade_cancel()               # a fade in progress would make the voice quiet: settle at your volume first
            snap = p.snapshot()
            if snap["playing"] and not snap["paused"]:
                self._duck_music(True)
            self.speaker(text)
            return True
        except Exception as e:
            log.warning("announcement not spoken: %s: %s", type(e).__name__, str(e)[:200])
            return False                      # no speakers / engine hiccup: the door logic must never care
        finally:
            if self._ducked:
                self._duck_music(False)       # the music comes back up gradually
            self._speech_lock.release()

    def _duck_music(self, on):
        self._ducked = on
        c = self.config()
        self.svc.player.duck(on, level=c["duck"], up=c["rise"])

    def prewarm(self):
        """Render both messages in the background so the door never waits for the voice."""
        def work():
            try:
                if self._speech_ok():
                    self.preparer(*[t for t in (self._text("welcome"), self._text("reminder")) if t])
            except Exception as e:
                log.warning("could not prepare the announcements: %s: %s", type(e).__name__, str(e)[:200])
        threading.Thread(target=work, daemon=True, name="speech-prep").start()

    def announce_now(self, which):
        """Play one saved message now (the Settings preview buttons). Returns an error message, or None."""
        if which not in ("welcome", "reminder"):
            return "Unknown message"
        if not self._speech_ok():
            return "Speech needs a voice: pip install piper-tts (see docs/door-sensors.md) or sudo apt install espeak-ng"
        text = self._text(which)
        if not text:
            return "That message is empty"
        threading.Thread(target=self._say, args=(text,), daemon=True, name="announce").start()
        return None

    # ---------- fade-in ----------
    def _fade_begin(self):
        """Just before a door starts or resumes the music: drop the volume to a low level, then raise it gradually to
        what it was. A volume change you make yourself during the fade ends it and is respected."""
        secs = self.config()["fade"]
        if secs <= 0:
            return
        p = self.svc.player
        with self._fade_lock:
            if self._fade_stop:
                self._fade_stop.set()                      # a fade is already running: restart it towards the real target
            target = self._fade_target if self._fade_target is not None else p.snapshot()["volume"]
            if target <= 1:
                self._fade_stop = self._fade_target = None
                return                                     # already (nearly) silent: nothing to fade
            start = max(1, round(target * FADE_START))
            self._fade_target = target
            stop = self._fade_stop = threading.Event()
        p.set_volume(start)
        time.sleep(0.15 * self.FADE_SCALE)                 # let the system volume change land before the audio starts
        threading.Thread(target=self._ramp, args=(stop, start, target, secs * self.FADE_SCALE),
                         daemon=True, name="fade-in").start()

    def _ramp(self, stop, start, target, secs):
        p, last = self.svc.player, start
        for i in range(1, FADE_STEPS + 1):
            if stop.wait(secs / FADE_STEPS):
                return                                     # cancelled: the door opened, autoplay was switched off, or a newer fade took over
            with self._fade_lock:                          # the check and the volume change are one step: cancel() cannot slip in between
                if stop.is_set():
                    return
                if abs(p.snapshot()["volume"] - last) > 1:     # you moved the slider: the volume is yours now
                    self._fade_stop = self._fade_target = None
                    return
                last = round(start + (target - start) * (i / FADE_STEPS) ** FADE_CURVE)
                p.set_volume(last)
        with self._fade_lock:
            if self._fade_stop is stop:
                self._fade_stop = self._fade_target = None

    def _fade_out(self):
        """The last door opened: lower the volume gradually, then pause. Returns False when there is nothing to fade
        (fade-out off, nothing audible, or already silent): the caller then pauses at once."""
        secs, p = self.config()["fadeout"], self.svc.player
        snap = p.snapshot()
        if secs <= 0 or not (snap["playing"] or snap["loading"]) or snap["paused"]:
            return False
        with self._fade_lock:
            if self._fade_stop:
                self._fade_stop.set()                      # a fade-in is still running: turn it round from where it is
            target = self._fade_target if self._fade_target is not None else snap["volume"]
            if target <= 1:
                self._fade_stop = self._fade_target = None
                return False
            self._fade_target = target
            stop = self._fade_stop = threading.Event()
            self._out_idle.clear()
        threading.Thread(target=self._ramp_out, args=(stop, snap["volume"], max(1, round(target * FADE_START)),
                                                      secs * self.FADE_SCALE), daemon=True, name="fade-out").start()
        return True

    def _ramp_out(self, stop, start, low, secs):
        p, last, moved = self.svc.player, start, False
        for i in range(1, FADE_STEPS + 1):
            if stop.wait(secs / FADE_STEPS):
                return                                     # cancelled (someone came back): _fade_cancel restored the volume
            with self._fade_lock:
                if stop.is_set():
                    return
                if abs(p.snapshot()["volume"] - last) > 1:     # you moved the slider: keep your value, just pause now
                    moved = True
                    break
                last = round(low + (start - low) * (1 - i / FADE_STEPS) ** FADE_CURVE)    # the fade-in reversed
                p.set_volume(last)
        with self._eval_lock:
            if stop.is_set() or self._playing is not False:
                if not stop.is_set():
                    self._fade_cancel()                    # autoplay state changed under us: leave the volume as it was
                return                                     # a door closed in the meantime: nothing to pause
            try:
                self._silence()
            finally:
                if moved:
                    with self._fade_lock:
                        if self._fade_stop is stop:
                            self._fade_stop = self._fade_target = None
                    self._out_idle.set()
                else:
                    self._fade_cancel()                    # after the pause went out: put the volume back, no loud blip

    def _fade_cancel(self):
        """End a running fade and put the volume back to what it was (the music is being silenced again)."""
        with self._fade_lock:
            stop, target = self._fade_stop, self._fade_target
            self._fade_stop = self._fade_target = None
            self._out_idle.set()
            if stop:
                stop.set()
        if target is not None:
            self.svc.player.set_volume(target)

    def run(self, interval=20):
        """Start sensors and a light ticker that catches the opening/closing time boundaries."""
        speech.use_voice(self.config()["voice"])
        self.start()
        self.prewarm()

        def tick():
            seen = ()
            while True:
                time.sleep(interval)
                try:
                    self.evaluate()
                    now = tuple(r["stale"] for r in self.snapshot())
                    if now != seen:                  # staleness is time-driven: push it to the UI
                        seen = now
                        self.svc.notify()
                except Exception:
                    pass
        threading.Thread(target=tick, daemon=True, name="bathrooms").start()
