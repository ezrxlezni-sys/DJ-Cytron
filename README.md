# Cytron DJ

A web app that turns a Raspberry Pi into a network music player. Open it from any phone or computer on the
network to play **internet radio**, **YouTube Music**, **YouTube** and **SoundCloud** through the Pi's speakers, and to see whether the
**restrooms are occupied** from magnetic door sensors. The door sensors can also drive the music: play while
someone is inside, pause when everyone has left, and speak a welcome and a reminder at the door.

```mermaid
flowchart LR
    B["Phone / laptop<br/>browser UI"]
    NET(["Internet<br/>YouTube, YouTube Music, SoundCloud<br/>+ radio streams"])

    subgraph PI["Raspberry Pi"]
        direction LR
        APP["Cytron DJ<br/>Flask + gunicorn"]
        YT["ytmusicapi + yt-dlp<br/>search, stream URLs<br/>(YouTube, YouTube Music, SoundCloud)"]
        MPV["mpv"]
        PW["PipeWire"]
        SPK(["Speakers"])
        GPIO["gpiozero<br/>2 reed switches"]
    end

    B -- "HTTP / JSON" --> APP
    APP -. "SSE: live state" .-> B
    APP -. "MP3: listen on this device" .-> B
    APP -- "IPC socket" --> MPV
    APP -- "search, resolve" --> YT
    YT --> NET
    NET -- "audio streams" --> MPV
    MPV --> PW --> SPK
    GPIO -- "door open / closed" --> APP
```

## Where to start

| You are... | Start with |
|---|---|
| **Using it** | [Using the player](docs/guide/using-the-player.md), then the [FAQ](docs/guide/faq.md) |
| **Setting up a Pi** | [Installation](docs/admin/installation.md), then [Deployment](docs/admin/deployment.md) and [Maintenance](docs/admin/maintenance.md) |
| **Wiring the doors** | [Door sensor hardware](docs/doors/hardware.md) |
| **Fixing a problem** | [Troubleshooting](docs/admin/troubleshooting.md) |
| **Changing the code** | [Architecture overview](docs/architecture/overview.md) and [Development](docs/contributing/development.md) |

Everything is indexed in the [documentation hub](docs/README.md).

## Features

| Area | What it does |
|---|---|
| **Radio** | 71 built-in Malaysian and regional stations grouped by category, with logos, search and a grid / list layout. Add, rename, re-point or remove stations. |
| **Music** | One search across YouTube Music, YouTube and SoundCloud, a page per platform, **Trending now** and **Suggested for you**. |
| **Queue and playlists** | Drag to reorder, filter, shuffle, repeat, save as playlists. The queue survives restarts. |
| **Player** | Mini player that opens into a full player, seek, volume, up-next, live radio titles. |
| **Listen on this device** | Streams what the Pi plays to your own phone or laptop (up to 4 listeners). |
| **Restrooms** | Live Available / Occupied cards and a "check sensor" watchdog. |
| **Door autoplay** | Play while someone is inside, pause when nobody is, with gentle fade in and fade out. |
| **Door announcements** | A natural offline voice says a welcome and a reminder; the music dips under it. Messages are editable. |
| **Live UI** | Every open browser updates instantly and recovers by itself after a lost connection. |
| **Resilient** | Restarts mpv if it dies, skips broken tracks, reconnects dropped radio streams, backs up its data nightly, updates yt-dlp weekly. |
| **Installable** | Web-app manifest and icons, light and dark theme. |

## Quick start

On a Raspberry Pi running Raspberry Pi OS Bookworm or later:

```bash
sudo apt install mpv ffmpeg espeak-ng python3-gpiozero python3-lgpio quickjs
cd /home/pi/Documents/pi-player
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m piplayer                 # http://cytrondj.local:8088 (development server)
```

That plays radio and music. Optional extras:

- **Natural announcement voice:** download a Piper voice, see [Installing a voice](docs/doors/announcements.md#installing-a-voice).
  Without it announcements use the robotic `espeak-ng`.
- **Door sensors:** wire two reed switches, see [Door sensor hardware](docs/doors/hardware.md).
- **Run on boot** (gunicorn on port 80, `http://cytrondj.local`), plus the nightly backup and weekly yt-dlp update:
  [Deployment](docs/admin/deployment.md) and [Maintenance](docs/admin/maintenance.md).

Full details and a checklist to confirm it works: [Installation](docs/admin/installation.md).

## Requirements

- Raspberry Pi with Raspberry Pi OS (Bookworm or later), audio working through PipeWire, and Python 3.11+
- `mpv` and `quickjs` (yt-dlp needs a JavaScript runtime for YouTube)
- The Python packages in [requirements.txt](requirements.txt) (`requirements.lock` lists the exact versions that were tested)
- `ffmpeg` and `pw-record` (PipeWire) for Listen on this device
- For the door sensors: `python3-gpiozero`, `python3-lgpio` and two reed switches
- For announcements: a Piper voice file (recommended) or `espeak-ng`

## Project layout

| Path | Contents |
|---|---|
| `piplayer/` | The application: Flask app, player, door service, music sources, speech, and the static web UI |
| `deploy/` | systemd unit and timers, backup and update scripts |
| `data/` | Runtime state (git-ignored): stations, playlists, history, settings, queue, voices |
| `docs/` | Documentation |
| `tests/` | The pytest suite (needs no mpv, network or GPIO) |

## Security note

The app has **no login**. Anyone who can reach the Pi on the network can play music, change settings and reboot
or shut down the Pi. Run it only on a trusted network, never forwarded to the internet.

Protections that are in place (they are not authentication): every `/api` request must use a LAN-style hostname
or IP in its `Host` header (blocks DNS-rebinding), writes from another website are refused, queue items are
validated so mpv only ever opens `http(s)` streams and plain ids, and the power endpoints refuse non-JSON
requests. Details in [Security](docs/admin/security.md).

## Tests

```bash
.venv/bin/pip install pytest
.venv/bin/pytest -q
```

## More

[Changelog](CHANGELOG.md) · [License](LICENSE) · [HTTP API](docs/reference/api.md) · [Configuration](docs/reference/configuration.md)
