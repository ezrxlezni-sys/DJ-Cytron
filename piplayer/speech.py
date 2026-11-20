"""Spoken announcements: text to speech, played through the same speakers as the music.

Two engines, both fully offline (nothing is sent anywhere, the voice is made on the Pi):

* **Piper** (preferred): a neural voice that sounds natural. `pip install piper-tts` plus a voice file
  (`data/voices/en_GB-alan-medium.onnx` and its `.onnx.json`, see docs/doors/announcements.md).
* **espeak-ng** (fallback): robotic but tiny: sudo apt install espeak-ng

A message is rendered ONCE and kept in a cache folder (keyed by engine, voice and text), so at the door it is just a
file being played: no waiting for the engine. `prepare()` renders ahead of time (the door code calls it at start-up
and whenever a message is edited). Every rendered file gets a little silence at both ends so a sleeping sound output
cannot clip the first syllable.

Playback needs `pw-play` or `aplay` (both ship with Raspberry Pi OS).

Environment: PIPLAYER_TTS=off disables speech (the tests do); PIPLAYER_PIPER_VOICE = path of a Piper .onnx voice;
PIPLAYER_VOICE_DIR / PIPLAYER_SPEECH_CACHE = where voices / rendered files live; PIPLAYER_TTS_VOICE = the espeak voice.
"""
import hashlib
import importlib.util
import logging
import os
import shutil
import subprocess
import threading
import time
import wave
from pathlib import Path

log = logging.getLogger("piplayer.speech")

ESPEAK = "espeak-ng"
PLAYERS = ("pw-play", "aplay")
MAX_CHARS = 180
PAD_START = 0.35                  # seconds of silence before the voice (a sleeping sink swallows the first syllable)
PAD_END = 0.15
CACHE_KEEP = 150                  # rendered files kept; the oldest are deleted
MIN_SPEED, MAX_SPEED = 0.5, 1.5   # speaking speed multiplier limits
DEFAULT_PIPER_VOICE = "en_GB-alan-medium.onnx"
_ROOT = Path(__file__).resolve().parent.parent / "data"

_chosen = {"voice": "", "speed": 1.0}                   # the voice picked in Settings: a Piper voice name, "espeak-ng", or "" = best available
_probe = {"at": 0.0, "engine": None, "voices_at": 0.0, "voices": []}      # engine detection is cached: it is asked for on every state push
_render_lock = threading.Lock()           # one render at a time (the neural model is big, the Pi is small)


def _voice_dir():
    return Path(os.environ.get("PIPLAYER_VOICE_DIR") or _ROOT / "voices")


def _cache_dir():
    return Path(os.environ.get("PIPLAYER_SPEECH_CACHE") or _ROOT / "speech-cache")


def _player():
    return next((p for p in PLAYERS if shutil.which(p)), None)


def _piper_models():
    """{name: path} of the installed Piper voices (a .onnx with its .onnx.json); empty when piper-tts is missing."""
    if not importlib.util.find_spec("piper"):
        return {}
    files = sorted(_voice_dir().glob("*.onnx"))
    if os.environ.get("PIPLAYER_PIPER_VOICE"):
        files.insert(0, Path(os.environ["PIPLAYER_PIPER_VOICE"]))
    return {f.name[:-5]: f for f in files if f.is_file() and Path(str(f) + ".json").is_file()}


def voices():
    """The voices Settings can offer: installed Piper voices, then espeak-ng. Cached for a few seconds: every state push asks."""
    if time.monotonic() - _probe["voices_at"] > 10:
        _probe["voices"] = [*_piper_models(), *([ESPEAK] if shutil.which(ESPEAK) else [])]
        _probe["voices_at"] = time.monotonic()
    return list(_probe["voices"])


def use_voice(name):
    """Pick the voice (from Settings). "" = automatic. An unknown name behaves like automatic."""
    if _chosen["voice"] != (name or ""):
        _chosen["voice"] = name or ""
        forget_probe()


def use_speed(speed):
    """Set how fast messages are spoken (from Settings): 1.0 = normal, 0.5 = half speed, 1.5 = one and a half times."""
    try:
        speed = min(MAX_SPEED, max(MIN_SPEED, float(speed)))
    except (TypeError, ValueError):
        speed = 1.0
    _chosen["speed"] = speed


def _piper_model():
    """Path of the Piper voice to use, or None (not installed, or espeak-ng was picked)."""
    if _chosen["voice"] == ESPEAK:
        return None
    models = _piper_models()
    default = DEFAULT_PIPER_VOICE[:-5]
    return models.get(_chosen["voice"]) or models.get(default) or next(iter(models.values()), None)


def engine():
    """'piper', 'espeak-ng', or None when nothing can speak."""
    if time.monotonic() - _probe["at"] > 10:
        _probe["engine"] = "piper" if _piper_model() else ESPEAK if shutil.which(ESPEAK) else None
        _probe["at"] = time.monotonic()
    return _probe["engine"]


def forget_probe():
    """Re-detect the engine on the next call (after installing a voice, and in tests)."""
    _probe["at"] = _probe["voices_at"] = 0.0


def available():
    """True when speech can work: not switched off, an engine is installed and there is something to play it with."""
    return os.environ.get("PIPLAYER_TTS", "") != "off" and engine() is not None and _player() is not None


def clean(text):
    return " ".join(str(text or "").split())[:MAX_CHARS]


# ---------- rendering ----------
def _key(eng, text):
    voice = _piper_model().name if eng == "piper" else os.environ.get("PIPLAYER_TTS_VOICE", "en-us+f3")
    return hashlib.sha1(f"{eng}|{voice}|{_chosen['speed']:.2f}|{text}".encode()).hexdigest()[:20]


def _pad(src, dst):
    """Copy a wav with silence added at both ends."""
    with wave.open(str(src), "rb") as r:
        params, frames = r.getparams(), r.readframes(r.getnframes())
    gap = lambda s: b"\0" * (int(params.framerate * s) * params.sampwidth * params.nchannels)
    with wave.open(str(dst), "wb") as w:
        w.setparams(params)
        w.writeframes(gap(PAD_START) + frames + gap(PAD_END))


def _render_piper(todo):
    """Render [(text, out_path)] with ONE model load (about 7 s on a Pi 4), then let the model go to free its memory."""
    from piper import PiperVoice
    try:
        from piper import SynthesisConfig as syn_config
    except ImportError:                       # an older piper-tts: no speed control
        syn_config = None
    voice = PiperVoice.load(str(_piper_model()))
    try:
        for text, out in todo:
            raw = out.with_suffix(".raw.wav")
            with wave.open(str(raw), "wb") as w:
                if _chosen["speed"] != 1.0 and syn_config:
                    voice.synthesize_wav(text, w, syn_config=syn_config(length_scale=1 / _chosen["speed"]))   # longer scale = slower
                else:
                    voice.synthesize_wav(text, w)
            _pad(raw, out)
            raw.unlink()
    finally:
        del voice


def _render_espeak(text, out):
    raw = out.with_suffix(".raw.wav")
    voice = os.environ.get("PIPLAYER_TTS_VOICE", "en-us+f3")
    # argv list, no shell: the text can never be run as a command. "--" stops a text starting with "-" being read as an option.
    subprocess.run([ESPEAK, "-v", voice, "-s", str(round(150 * _chosen["speed"])), "-p", "55", "-w", str(raw), "--", text],
                   check=True, capture_output=True, timeout=15)
    _pad(raw, out)
    raw.unlink()


def _prune(folder):
    files = sorted((f for f in folder.glob("*.wav")), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[CACHE_KEEP:]:
        f.unlink(missing_ok=True)


def prepare(*texts):
    """Make sure each text is rendered and cached. Returns the wav paths (None for an empty text). Blocks while
    rendering; instant for texts already in the cache. Raises RuntimeError if speech is not available."""
    texts = [clean(t) for t in texts]
    if not available():
        raise RuntimeError("speech is not available (pip install piper-tts + a voice, or sudo apt install espeak-ng)")
    folder = _cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    with _render_lock:
        for eng in dict.fromkeys((engine(), ESPEAK if shutil.which(ESPEAK) else None)):     # the engine, then the fallback
            if eng is None:
                continue
            paths = [folder / f"{_key(eng, t)}.wav" if t else None for t in texts]
            todo = [(t, p) for t, p in zip(texts, paths) if p and not p.exists()]
            try:
                if todo and eng == "piper":
                    _render_piper(todo)
                else:
                    for t, p in todo:
                        _render_espeak(t, p)
            except Exception as e:
                log.warning("speech: %s failed to render (%s: %s)", eng, type(e).__name__, str(e)[:200])
                for _, p in todo:
                    p.unlink(missing_ok=True)
                continue
            for p in paths:
                if p:
                    p.touch()                              # recently used = kept by _prune
            _prune(folder)
            return paths
    raise RuntimeError("speech could not be rendered (see the service log)")


def speak(text):
    """Say `text` out loud and return when it has finished. Raises RuntimeError if speech is not available."""
    text = clean(text)
    if not text:
        return
    wav = prepare(text)[0]
    player = _player()
    cmd = [player, str(wav)] if player == "pw-play" else [player, "-q", str(wav)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    except Exception as e:
        log.warning("speech: playing failed (%s: %s)", type(e).__name__, str(e)[:200])
        raise
