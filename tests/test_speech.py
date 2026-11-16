"""The speech module: engine choice, the render cache, padding, fallback. No sound is ever played."""
import wave

import pytest

from piplayer import speech


def make_wav(path, seconds=0.5, rate=22050):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x01\x01" * int(rate * seconds))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPLAYER_TTS", "")
    monkeypatch.setenv("PIPLAYER_SPEECH_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("PIPLAYER_VOICE_DIR", str(tmp_path / "voices"))
    monkeypatch.setattr(speech, "_player", lambda: "pw-play")
    monkeypatch.setattr(speech.shutil, "which", lambda n: "/usr/bin/" + n if n == "espeak-ng" else None)
    speech.forget_probe()
    yield tmp_path
    speech.forget_probe()


def fake_espeak(monkeypatch, calls):
    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "espeak-ng":
            make_wav(cmd[cmd.index("-w") + 1], 0.5)
    monkeypatch.setattr(speech.subprocess, "run", run)


def test_switched_off_and_nothing_installed(env, monkeypatch):
    assert speech.engine() == "espeak-ng" and speech.available()
    monkeypatch.setenv("PIPLAYER_TTS", "off")
    assert not speech.available()
    monkeypatch.setenv("PIPLAYER_TTS", "")
    monkeypatch.setattr(speech.shutil, "which", lambda n: None)
    speech.forget_probe()
    assert speech.engine() is None and not speech.available()
    with pytest.raises(RuntimeError):
        speech.speak("hello")


def test_piper_is_preferred_when_its_voice_is_installed(env, monkeypatch):
    voices = env / "voices"; voices.mkdir()
    (voices / speech.DEFAULT_PIPER_VOICE).write_bytes(b"x")
    assert speech.engine() == "espeak-ng"                      # a model without its .json is not usable
    (voices / (speech.DEFAULT_PIPER_VOICE + ".json")).write_text("{}")
    monkeypatch.setattr(speech.importlib.util, "find_spec", lambda n: object())
    speech.forget_probe()
    assert speech.engine() == "piper"


def test_a_message_is_rendered_once_then_played_from_the_cache(env, monkeypatch):
    calls = []
    fake_espeak(monkeypatch, calls)
    speech.speak("Hello there")
    speech.speak("Hello there")
    assert [c[0] for c in calls].count("espeak-ng") == 1       # second time: straight from the cache
    assert [c[0] for c in calls].count("pw-play") == 2
    assert "--" in calls[0] and calls[0][-1] == "Hello there"
    speech.speak("-rf something")                              # a text that looks like an option stays text
    assert calls[-2][-2:] == ["--", "-rf something"]


def test_silence_is_added_at_both_ends(env, monkeypatch):
    fake_espeak(monkeypatch, [])
    path = speech.prepare("Hello")[0]
    with wave.open(str(path)) as w:
        assert w.getnframes() == int(22050 * 0.5) + int(22050 * speech.PAD_START) + int(22050 * speech.PAD_END)
        data = w.readframes(w.getnframes())
    assert data[:100] == b"\0" * 100 and data[-100:] == b"\0" * 100


def test_prepare_renders_several_texts_and_skips_empty_ones(env, monkeypatch):
    fake_espeak(monkeypatch, [])
    a, none, b = speech.prepare("One", "", " Two  words ")
    assert a.exists() and none is None and b.exists() and a != b


def test_falls_back_to_espeak_when_piper_breaks(env, monkeypatch):
    calls = []
    fake_espeak(monkeypatch, calls)
    monkeypatch.setattr(speech, "_piper_model", lambda: env / "voices" / "m.onnx")
    monkeypatch.setattr(speech, "_render_piper", lambda todo: (_ for _ in ()).throw(OSError("model is corrupt")))
    speech.forget_probe()
    assert speech.engine() == "piper"
    path = speech.prepare("Hello")[0]
    assert path.exists() and calls[0][0] == "espeak-ng"


def test_failure_everywhere_raises_and_leaves_no_half_files(env, monkeypatch):
    def boom(cmd, **kw):
        raise OSError("no audio")
    monkeypatch.setattr(speech.subprocess, "run", boom)
    with pytest.raises(RuntimeError):
        speech.prepare("Hello")
    assert list((env / "cache").glob("*.wav")) == []


def test_old_renders_are_pruned(env, monkeypatch):
    fake_espeak(monkeypatch, [])
    monkeypatch.setattr(speech, "CACHE_KEEP", 3)
    for i in range(6):
        speech.prepare(f"message {i}")
    assert len(list((env / "cache").glob("*.wav"))) == 3


def test_text_is_cleaned_and_capped():
    assert speech.clean("  a \n b\t") == "a b"
    assert len(speech.clean("x" * 500)) == speech.MAX_CHARS
