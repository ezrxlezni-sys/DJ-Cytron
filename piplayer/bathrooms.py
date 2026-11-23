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

Announcements: when a door closes a welcome message is spoken (then the music starts and fades in); `reminder_delay`
seconds after a door closed (minutes + seconds in Settings) the reminder is spoken over the music, ducked, provided that
door is still closed. Only inside the active hours, never at start-up or when a sensor is rewired, and each message can
be edited or emptied. Speech comes from piplayer/speech.py (espeak-ng).

Idle music: when nobody is inside (inside the active hours, autoplay on) the music does not stop: it keeps playing quietly
at the `idle` level (30 % by default, mpv's own volume, 0 = pause as before) and comes back up when a door closes.

Goodbye: when a door opens a `bye` message is spoken (over the music).

Watchdog: a plain reed switch can't report that it was unplugged, so a room whose sensor shows no
change for STALE_AFTER of opening time is flagged `stale` ("check sensor") in the snapshot.

Configuration lives in the shared settings store (key "bathrooms"), is pushed to the UI inside the
normal state stream, and is edited through POST /api/doors, like volume.
"""
import datetime
import logging
import random
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
            "reminder": "Please remember to flush and keep it clean.", "reminder_delay": 60,
            "bye": "Thank you for visiting. See you again soon!", "idle": 30,
            "duck": 30, "rise": 2, "voice": "", "speed": 1.0}
REMINDER_DELAY_MAX = 3600                     # seconds: the longest wait between a door closing and the reminder
MESSAGE_MAX = 160                             # characters per announcement (each variant)
MESSAGE_VARIANTS = 10                         # variants per message, one per line: a different one is said each time
GREETINGS = {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening"}   # for {greeting}
FADE_START = 0.08                             # a fade begins at this fraction of the normal volume
FADE_STEPS = 20                               # volume updates per fade
RETRY_AFTER = 30                              # seconds: a failed autoplay start (stream down, track unplayable) is retried this often
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
        self._start_lock = threading.Lock()   # two saves at once must not both rewire the sensors
        self._eval_lock = threading.Lock()    # serialises autoplay decisions
        self._rooms = {r: {"occupied": None, "since": None} for r in ROOMS}
        self._buttons = []                    # keep gpiozero objects alive
        self._pins, self.error = {}, None
        self._playing = None                  # autoplay edge state: None = unknown / switched off
        self._paused = None                   # (kind, id) of the item autoplay paused, to resume it
        self._tried = 0.0                     # when autoplay last started something (for the retry after a failure)
        self._last = {}                       # the variant said last, per message kind
        self.speaker = speech.speak           # text -> speech (replaced in tests)
        self.preparer = speech.prepare        # texts -> rendered ahead of time (replaced in tests)
        self._ducked = False                  # the music is dipped for a message (guarded by _speech_lock)
        self._speech_ok = speech.available
        self._speech_lock = threading.Lock()  # one announcement at a time; a second one is skipped, not queued
        self._fade_lock = threading.Lock()    # guards the running fade
        self._fade_stop = None                # Event that ends the running fade
        self._fade_target = None              # the volume a running fade is heading for (to restore it if cut short)
        self._idle_set = None                 # the idle level last applied
        self._idling = False                  # nobody is in and the music is playing quietly at the idle level
        self._reminders = {}                  # room -> Event that cancels its pending reminder (the door opened / closed again)
        self._out_idle = threading.Event()    # set whenever NO fade-out is running (used by the music logic)
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
        old_pins = self.config()["pins"]
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
        if "idle" in patch:
            try:
                idle = int(patch["idle"])
            except (TypeError, ValueError):
                return "Idle music level must be a number"
            if not 0 <= idle <= 100:
                return "Idle music level must be 0-100 %"
            saved["idle"] = idle
        for key in ("welcome", "reminder", "bye"):
            if key in patch:
                if not isinstance(patch[key], str):
                    return "Messages must be text"
                lines = [" ".join(line.split()) for line in patch[key].splitlines()]
                lines = [line for line in lines if line]              # one variant per line, blank lines ignored
                if any(len(line) > MESSAGE_MAX for line in lines):
                    return f"Each message can be at most {MESSAGE_MAX} characters"
                if len(lines) > MESSAGE_VARIANTS:
                    return f"At most {MESSAGE_VARIANTS} messages (one per line)"
                saved[key] = "\n".join(lines)
        if "reminder_delay" in patch:
            try:
                delay = int(patch["reminder_delay"])
            except (TypeError, ValueError):
                return "Reminder delay must be a number of seconds"
            if not 0 <= delay <= REMINDER_DELAY_MAX:
                return f"Reminder delay must be 0 seconds to {REMINDER_DELAY_MAX // 60} minutes"
            saved["reminder_delay"] = delay
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
        if "speed" in patch:
            try:
                speed = float(patch["speed"])
            except (TypeError, ValueError):
                return "Speaking speed must be a number"
            if not speech.MIN_SPEED <= speed <= speech.MAX_SPEED:
                return f"Speaking speed must be between {speech.MIN_SPEED:g}x and {speech.MAX_SPEED:g}x"
            saved["speed"] = speed
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
        speech.use_speed(saved.get("speed", 1.0))
        if "pins" in patch and (saved["pins"] != old_pins or self.error):
            self.start()                      # only on a real rewire (or to retry a failure): start() blanks the readings, which would pause the music
        if "welcome" in patch or "reminder" in patch or "bye" in patch or "voice" in patch or "speed" in patch:
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
        self._cancel_reminder(room)           # a door that opens or closes again restarts the wait
        welcomed = threading.Event()                  # set once the welcome has been spoken (or skipped): the delay counts from then
        speaks = bool(self._announcement(before, occupied))
        if before is not None and occupied:           # a real door closing (not a start-up reading): the reminder follows later
            self._schedule_reminder(room, welcomed if speaks else None)
        if speaks:                                    # a door closed: say hello first, then the music starts (and fades in)
            threading.Thread(target=self._welcome, args=(welcomed,), daemon=True, name="announce").start()
            return
        self.evaluate()
        if before is not None and occupied is False and self._bye_ok():     # a door opened: say goodbye over the (quieter) music
            threading.Thread(target=self._bye, daemon=True, name="announce").start()

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
        with self._start_lock:
            self._start()

    def _start(self):
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
                if self._idling:
                    self._idling = False
                    self.svc.player.duck(False, up=0)     # back to the normal level straight away
                self._playing = self._paused = None       # switched off: forget state, touch nothing else
                self._fade_cancel()
                return
            occupied = self._wanted()
            idle = not occupied and self._idle_ok()       # nobody in: keep the music going, quietly
            want = occupied or idle
            if want and self._playing and self._failed():
                self._playing = None                      # the music we started died (stream down, unplayable track): try again
            if want == self._playing and idle == self._idling:
                if idle and self._idle_level() != self._idle_set:
                    self._idle_duck(0.5)                  # the level was changed in Settings
                return
            was_idling, was_playing = self._idling, self._playing
            self._playing = want
            if want and not self._out_idle.is_set():
                self._fade_cancel()                       # someone is back mid fade-out: the music carries on at your volume
            try:
                if idle:
                    self._idling = True
                    if was_playing:                       # the last visitor left: lower the music gradually, no pause
                        self._fade_cancel()
                        self._idle_duck(self.config()["fadeout"] * self.FADE_SCALE)
                        return
                    self._idle_duck(0)                    # start-up / start of the hours: begin quietly, no fade-in
                    ok = self._play(fade=False)
                    if ok is False:
                        self._playing = None
                    return
                if was_idling:
                    self._idling = False                  # a door closed: back up to the normal level
                    self.svc.player.duck(False, up=self.config()["fade"] * self.FADE_SCALE)
                ok = (self._play if want else self._halt)()
                if not want and was_idling:
                    self.svc.player.duck(False, up=0)     # the hours ended: the next start must not be quiet
            except Exception:
                self._playing = None                      # never remember a start that did not happen: the next tick retries
                raise
            if want and ok is False:
                self._playing = None                      # nothing could be started (empty queue, no stations): retry later

    def _idle_level(self):
        return max(0, min(100, int(self.config()["idle"])))

    def _idle_ok(self):
        return bool(self.config()["autoplay"] and self._idle_level() > 0 and self._in_hours())

    def _idle_duck(self, secs):
        level = self._idle_set = self._idle_level()
        self.svc.player.duck(True, level=level, down=secs)

    def _failed(self):
        """True when the player gave up (error shown, nothing playing or loading) some time after autoplay started it.
        A manual stop leaves no error, so it is still respected."""
        snap = self.svc.player.snapshot()
        return bool(snap["error"]) and not (snap["playing"] or snap["loading"]) and time.time() - self._tried >= RETRY_AFTER

    def _key(self, snap):
        cur = snap["current"]
        return (cur["kind"], cur["id"]) if cur else None

    def _play(self, fade=True):
        try:
            return self._start_music(fade)
        finally:
            if self._speech_lock.locked() and not self._ducked:
                self._duck_music(True)             # music that starts while a message is being spoken stays under the voice

    def _start_music(self, fade=True):
        """Start or resume the music. Returns False when there was nothing to start."""
        p = self.svc.player
        snap = p.snapshot()
        self._tried = time.time()
        if snap["playing"] and snap["paused"]:             # paused or muted (by us, or by hand): carry on where it was
            self._paused = None
            if fade:
                self._fade_begin()
            (p.hold if snap["held"] else p.pause)(False)   # instant either way
            return True
        self._paused = None
        if snap["playing"] or snap["loading"]:
            return True                                    # already playing something
        if snap["queue"]:
            if fade:
                self._fade_begin()
            p.play_index(snap["index"] if 0 <= snap["index"] < len(snap["queue"]) else 0)
            return True
        if (st := next(iter(self.svc.stations.all()), None)):          # empty queue: first station
            if fade:
                self._fade_begin()
            p.play_now([as_queue_item(st)])
            return True
        return False

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
    def _variants(self, kind):
        """The saved messages of this kind, one per line (a plain one-line message is a single variant)."""
        return [" ".join(line.split()) for line in str(self.config().get(kind) or "").splitlines() if line.split()]

    def _daypart(self):
        h = self._clock().hour
        return "morning" if h < 12 else "afternoon" if h < 18 else "evening"

    @staticmethod
    def _expand(text, part):
        return text.replace("{greeting}", GREETINGS[part])

    def _text(self, kind):
        """One message to say now: a random variant (never the same twice in a row), with {greeting} filled in."""
        variants = self._variants(kind)
        if not variants:
            return ""
        if len(variants) > 1 and self._last.get(kind) in variants:
            variants = [v for v in variants if v != self._last[kind]]
        pick = random.choice(variants)
        self._last[kind] = pick
        return self._expand(pick, self._daypart())

    def _all_texts(self):
        """Every wording that could be said (each variant, each greeting): all rendered ahead of time."""
        out = []
        for kind in ("welcome", "reminder", "bye"):
            for v in self._variants(kind):
                out += [self._expand(v, part) for part in (GREETINGS if "{greeting}" in v else ("morning",))]
        return list(dict.fromkeys(out))

    def _announcement(self, before, occupied):
        """'welcome' when a door closed and it should be said, else None. Never for the first reading after start-up or
        a rewire (before / after is None), never outside the hours."""
        if before is None or not occupied:
            return None
        if not self.config()["announce"] or not self._variants("welcome") or not self._in_hours() or not self._speech_ok():
            return None
        return "welcome"

    def _bye_ok(self):
        return bool(self.config()["announce"] and self._variants("bye") and self._in_hours() and self._speech_ok())

    def _bye(self):
        self._say(self._text("bye"))

    def _cancel_reminder(self, room):
        gone = self._reminders.pop(room, None)
        if gone:
            gone.set()

    def _schedule_reminder(self, room, welcomed=None):
        """After a door closed: speak the reminder `reminder_delay` seconds after the welcome ended (after the door
        closed when there is no welcome), if the door is still closed."""
        c = self.config()
        if not c["announce"] or not self._variants("reminder") or not self._in_hours() or not self._speech_ok():
            return
        cancel = self._reminders[room] = threading.Event()
        delay = c["reminder_delay"] * self.FADE_SCALE
        threading.Thread(target=self._remind, args=(room, cancel, delay, welcomed), daemon=True, name="reminder").start()

    def _remind(self, room, cancel, delay, welcomed=None):
        if welcomed is not None:
            welcomed.wait(60)                 # the countdown starts when the welcome has finished
        if cancel.is_set() or cancel.wait(delay) or self._reminders.get(room) is not cancel:
            return                            # the door opened (or closed again) meanwhile
        self._reminders.pop(room, None)
        for _ in range(60):                   # the welcome may still be playing (short delay): wait for it, up to a minute
            if not self._speech_lock.locked():
                break
            time.sleep(1 * self.FADE_SCALE)
        if self.config()["announce"] and self._in_hours():
            self._say(self._text("reminder"))

    def _welcome(self, done=None):
        try:
            self._say(self._text("welcome"))
        finally:
            if done:
                done.set()
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
        rest = self._idle_level() if self._idling else 100             # the level the music returns to
        self.svc.player.duck(on, level=min(c["duck"], rest), up=c["rise"], rest=rest)

    def prewarm(self):
        """Render both messages in the background so the door never waits for the voice."""
        def work():
            try:
                if self._speech_ok():
                    self.preparer(*self._all_texts())
            except Exception as e:
                log.warning("could not prepare the announcements: %s: %s", type(e).__name__, str(e)[:200])
        threading.Thread(target=work, daemon=True, name="speech-prep").start()

    def announce_now(self, which):
        """Play one saved message now (the Settings preview buttons). Returns an error message, or None."""
        if which not in ("welcome", "reminder", "bye"):
            return "Unknown message"
        if not self._speech_ok():
            return "Speech needs a voice: pip install piper-tts (see docs/doors/announcements.md) or sudo apt install espeak-ng"
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
        speech.use_speed(self.config()["speed"])
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
