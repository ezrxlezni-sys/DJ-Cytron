# Door announcements

Independent of autoplay, during the active hours the Pi can speak at the doors through the same speakers as the music.

Code: [piplayer/speech.py](../../piplayer/speech.py) (the voice) and [piplayer/bathrooms.py](../../piplayer/bathrooms.py)
(when to speak).

## What is said and when

| Event | What is said (default text) |
|---|---|
| A door **closes** | "Thank you for choosing Cytron DJ. Enjoy the vibe!" Spoken first; if autoplay is on the music starts (and fades in) afterwards. |
| A door **opens** | "Please remember to flush and keep it clean." If that was the last occupied door the music has already paused; otherwise it is spoken over the music, which dips to about 30 % while the message plays. |

Rules:

- Nothing is said at start-up or after rewiring the sensors.
- Nothing is said outside the active hours, when the switch is off, or when that message is empty.
- Only one message plays at a time (a message that arrives while another is playing is skipped).
- If the speakers or the speech engine fail, the door logic carries on silently. Failures are written to the log.

Messages are up to 160 characters (extra spaces are collapsed). Edit them in Settings; the ▶ button plays a saved
message on the Pi's speakers.

## Installing a voice

The voice is generated on the Pi, offline: nothing is sent anywhere.

| Engine | Sound | Install |
|---|---|---|
| **Piper** (preferred) | Natural, calm British male (`en_GB-alan-medium`) | `piper-tts` is in `requirements.txt`; add the voice files in `data/voices/` (below) |
| **espeak-ng** (fallback) | Robotic | `sudo apt install espeak-ng` |

Piper is used whenever its voice file is present, and espeak-ng takes over by itself if Piper fails.

```bash
cd ~/Documents/pi-player && mkdir -p data/voices && cd data/voices
B=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium
curl -LO $B/en_GB-alan-medium.onnx && curl -LO $B/en_GB-alan-medium.onnx.json
```

Playback needs `pw-play` or `aplay`; both ship with Raspberry Pi OS.

### Using another voice

Any other Piper voice works: download its `.onnx` and `.onnx.json` (browse them at
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices); check a voice's licence before using it) into
`data/voices/`. Every installed voice appears in **Settings > Announcements > Voice**. To make one the default for
*Automatic*, set `PIPLAYER_PIPER_VOICE=/path/to/voice.onnx`. Each voice needs its `.onnx.json` next to the `.onnx`.

The espeak-ng voice is chosen with `PIPLAYER_TTS_VOICE` (default `en-us+f3`; `espeak-ng --voices` lists them, and
`+f1`..`+f5` and `+m1`..`+m7` pick a variant).

To switch speech off completely, turn off **Speak at the doors** in Settings, or set `PIPLAYER_TTS=off`.

## Rendered once, played instantly

A message is turned into a WAV the first time (about 10 s for both messages on a Pi 4, mostly loading the voice) and
kept in `data/speech-cache/` (the newest 30 files are kept; the key is engine, voice and text). The app renders both
messages in the background when it starts and whenever you save a changed message, so at the door the message is
just a file being played. Each file has a third of a second of silence in front (and a little at the end) so the
speakers cannot swallow the first word.

## Volume around a message

- The music dips to the **Music during a message** level (30 % by default) in 0.3 s so the voice is clear.
- When the message ends it rises back to full over the **Music comes back** time (2 seconds by default; it only snaps
  back if you choose Instantly).
- A fade-in in progress is settled at your volume first, so a message is never spoken quietly.
- Music that starts while a message is playing stays ducked until it ends.

The dip uses mpv's own volume, so it does not change the Pi's system volume or the slider.

## Settings

| Setting | API field | Values |
|---|---|---|
| Speak at the doors | `announce` | on / off (default on) |
| Voice | `voice` | Automatic, a Piper voice name, or `espeak-ng` |
| Speaking speed | `speed` | 0.5 to 1.5 (default 1; applies to both messages; needs a recent `piper-tts` for Piper) |
| Music during a message | `duck` | 0 to 100 % (default 30; 100 = no dip) |
| Music comes back | `rise` | 0 to 30 s (default 2; 0 = instantly) |
| Welcome | `welcome` | up to 10 messages, one per line, each up to 160 characters (empty = say nothing) |
| Reminder | `reminder` | same as the welcome |

With several lines, a different message is said each time (never the same one twice in a row). `{greeting}` in a
message becomes "Good morning" (before 12:00), "Good afternoon" (before 18:00) or "Good evening". Every wording is
rendered ahead of time, so the door never waits for the voice.

## Troubleshooting

| Symptom | Check |
|---|---|
| Settings shows "no voice installed" | Install Piper's voice files or `sudo apt install espeak-ng`. |
| Nothing is spoken | The switch is on? The time is inside the active hours? The message is not empty? A door must change; nothing is said at start-up. |
| The robotic voice is used instead of Piper | The voice file is missing or `piper-tts` is not installed in the venv. `.venv/bin/pip show piper-tts`; `ls data/voices`. |
| First message is slow after saving a change | It is being rendered (about 10 s). Wait a moment, or press ▶ once to warm it. |
| First word is cut off | The speakers were asleep. The app adds silence in front; if it still happens, increase the sink's idle timeout or use the ▶ button to check. |
| Errors in the log | `journalctl -u piplayer | grep speech`. Failures never affect the doors. |
| Test by hand | `espeak-ng -w /tmp/t.wav "hello" && pw-play /tmp/t.wav` |
