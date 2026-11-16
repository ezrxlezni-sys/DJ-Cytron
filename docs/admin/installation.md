# Installation

How to install Cytron DJ on a Raspberry Pi and check that it works by hand. To run it on boot afterwards, continue
with [Deployment](deployment.md).

## Requirements

| Need | Details |
|---|---|
| Hardware | A Raspberry Pi (Pi 4 or newer recommended) with speakers on its audio output. For door sensors: two magnetic reed switches and wire ([hardware](../doors/hardware.md)). |
| OS | Raspberry Pi OS **Bookworm or later**, with audio working through **PipeWire** (the default). |
| Python | 3.11 or newer. |
| Network | A trusted LAN, and internet access for YouTube, YouTube Music, SoundCloud and radio streams. |
| Name | The hostname `cytrondj` gives the address `http://cytrondj.local`. Set it with `sudo raspi-config` (System Options > Hostname). Without it, use the Pi's IP address. |

## 1. System packages

```bash
sudo apt install mpv ffmpeg espeak-ng python3-gpiozero python3-lgpio quickjs
```

| Package | Why | Required? |
|---|---|---|
| `mpv` | The audio player. | Yes |
| `quickjs` | JavaScript runtime yt-dlp needs for YouTube. The Raspberry Pi OS `nodejs` (v20) is too old: yt-dlp needs Node 22+, Deno or QuickJS. | Yes, for YouTube / YouTube Music |
| `python3-gpiozero`, `python3-lgpio` | Door sensors. | Only with door sensors |
| `ffmpeg` | Encodes the "Listen on this device" stream. | Only for Listen |
| `espeak-ng` | Fallback voice for door announcements. | Optional if you install Piper |

PipeWire's `pw-record`, `pw-play` and `wpctl` come with Raspberry Pi OS Bookworm. `wpctl` sets the volume, `pw-record`
feeds Listen, and `pw-play` (or `aplay`) speaks the announcements.

## 2. Get the code and Python packages

```bash
cd /home/pi/Documents
git clone <repository-url> pi-player        # or copy the folder here
cd pi-player
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

`--system-site-packages` lets the virtual environment use the `apt` GPIO libraries. If the environment already
exists without it, set `include-system-site-packages = true` in `.venv/pyvenv.cfg`.

`requirements.txt` holds loose version ranges. `requirements.lock` lists the exact versions that were tested; to
reproduce them use `.venv/bin/pip install -r requirements.lock`.

## 3. Install a natural voice (optional, recommended)

Door announcements use **Piper**, an offline neural voice. The Python package (`piper-tts`) is already installed by
`requirements.txt`. It also needs a voice file:

```bash
cd /home/pi/Documents/pi-player && mkdir -p data/voices && cd data/voices
B=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium
curl -LO $B/en_GB-alan-medium.onnx && curl -LO $B/en_GB-alan-medium.onnx.json
```

Without it, announcements fall back to the robotic `espeak-ng`. Other voices and how they are chosen are covered in
[Door announcements](../doors/announcements.md#installing-a-voice). Skip this step if you do not use announcements.

## 4. Run it by hand

```bash
cd /home/pi/Documents/pi-player
.venv/bin/python -m piplayer          # then open http://cytrondj.local:8088
```

This uses Flask's development server, which is fine for a test. It listens on port **8088**. Stop it with Ctrl+C.

## 5. Check that it works

1. Open the page. The Radio tab should show the stations.
2. Tap a station: you should hear it. If not, see [Audio output](deployment.md#audio-output).
3. Search in Music for a song and play it. If it fails but radio works, see
   [Troubleshooting](troubleshooting.md#music-and-radio).
4. Open Settings: the badge shows `Sensor error` or `No sensors` if no switches are wired. That is normal until you
   wire them or clear the pins. See [Door sensor hardware](../doors/hardware.md).
5. Optional: open the Restrooms tab, then short a sensor pin to GND with a jumper wire. The room should turn
   **Occupied**.

## Next

Run it on boot and install the nightly backup: [Deployment](deployment.md) and [Maintenance](maintenance.md).
