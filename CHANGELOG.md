# Changelog

All notable changes. Dates are `YYYY-MM-DD`. Upgrading? After pulling, follow
[Upgrading the app](docs/admin/maintenance.md#upgrading-the-app): install requirements, re-copy the systemd unit,
restart, and hard-refresh the browser.

## 2026-11-23

### Goodbye message and quiet idle music
- New **Goodbye** message (`bye`), spoken when a door opens.
- With autoplay on, the music no longer pauses when every door is open: it keeps playing quietly at **Music when nobody is in**
  (`idle`, 30 % by default, 0 = pause as before) and comes back up when a door closes.

### Reminder after the door closes
- The reminder is now spoken a set time **after a door closes** (new **Delay after the welcome** in Settings > Announcements, minutes +
  seconds; `reminder_delay` in the API, default 60 s) instead of when it opens. It is skipped if the door opens first.
  The welcome still plays when the door closes.

## 2026-11-16

### Announcements: speed, variants, greeting
- **Speaking speed** slider (0.5x to 1.5x) for both the welcome and the reminder.
- Each message can have several lines; a different one is said each time. `{greeting}` becomes Good morning / afternoon / evening.
- Settings page regrouped: Sensors, Automation, Announcements, Voice, Music during a message.
- The spoken-file cache keeps 150 files (was 30) so every variant stays ready.

### Documentation restructured
- The docs now live in six folders under `docs/`: `guide/` (users), `admin/` (running the Pi), `doors/` (sensors, autoplay,
  announcements), `reference/` (API, configuration, data files, glossary), `architecture/` and `contributing/`.
  `docs/README.md` is the index.
- New: installation, maintenance, security, consolidated troubleshooting, FAQ, glossary, data-file reference, design
  decisions, front-end and testing guides. The README is shorter and links out.
- Corrected: the built-in station count is 71 (not 32); the API accepts `yt` and `sc` items as well as `ytm` and `radio`;
  the README Quick start now mentions the Piper voice.
- Root files: `pytest.ini` moved into `pyproject.toml`; `requirements-dev.txt` removed (install `pytest` next to `requirements.txt`).

## 2026-11-13

### Music rebuilt: a home page and a page per platform
- **Music home** searches YouTube Music, YouTube and SoundCloud together (tabs: All, each platform) and shows platform
  cards, **Trending now** and **Suggested for you**.
- New pages **YouTube Music**, **YouTube** (16:9 video grid, grid/list switch) and **SoundCloud**, in the sidebar under
  *Platforms*.
- **YouTube** (`kind: "yt"`, yt-dlp search) and **SoundCloud** (`kind: "sc"`) are new track kinds. They work in the queue,
  playlists and next-track prefetch like YouTube Music tracks. SoundCloud's 30-second major-label previews are hidden.
- New endpoint `GET /api/trending`; `GET /api/search` takes `source=youtube|soundcloud`.
- Front end: Music now lives in `static/js/music.js` + `static/css/music.css`; the pane id changed from `search` to `music`.
- The listening-history shelves (Continue listening, Mostly played) were removed from the Music pages. History is still
  recorded and still feeds the suggestions; `GET /api/history` is unchanged.

### Doors: natural voice and smoother volume
- **Fade-out:** when the last door opens the music now fades down over `bathrooms.fadeout` seconds (default 3, `0` = off) before it
  pauses, then the volume is restored and the reminder is spoken. A door closing again mid-fade cancels it and the music carries on;
  moving the volume slider ends it and pauses at once. New Settings control *Fade out*.
- **Piper neural voice** (`en_GB-alan-medium`, offline) replaces espeak-ng as the preferred engine; espeak-ng stays as an
  automatic fallback. See [Door announcements](docs/doors/announcements.md#installing-a-voice). New: `piper-tts` in requirements, a voice file in
  `data/voices/`, `PIPLAYER_PIPER_VOICE`, `PIPLAYER_VOICE_DIR`, `PIPLAYER_SPEECH_CACHE`.
- Messages are **rendered once and cached**, and pre-rendered at start-up and when edited: no wait at the door. Silence is added
  before each message so the first word is not clipped.
- **Music rises gradually after a message** (about 2 s) instead of snapping back; the dip itself takes 0.3 s.
- A message spoken during a fade-in is now at your volume (it used to be quiet); music that starts mid-message stays ducked.
- The fade-in curve starts more gently (perceptual); speech failures are logged; engine detection is cached (it was two PATH scans per state push).
- **New Settings controls** (Announcements): *Voice* (any installed voice), *Music during a message* (how far the music dips)
  and *Music comes back* (how long the return takes). API fields `voice`, `duck`, `rise`; the state also lists `voices`.
- `GET /api/state` `doors` gains `engine` (`piper`, `espeak-ng` or `null`).

### Doors
- **Fade-in:** when a door closing starts or resumes the music (autoplay), the volume begins at about 8 % of your level and
  rises smoothly to it over `bathrooms.fade` seconds (default 5, `0` = off). Cut short if the door opens again (volume restored)
  or if you move the volume slider yourself.
- **Announcements:** a spoken welcome when a door closes and a reminder when it opens, inside the active hours, editable in Settings
  (`announce`, `welcome`, `reminder`) with a ▶ preview button (`POST /api/doors/announce`). The music dips (mpv volume) while a message
  plays and a welcome is spoken before the music starts. New module `speech.py` (espeak-ng: `sudo apt install espeak-ng`);
  `PIPLAYER_TTS=off` disables it and `PIPLAYER_TTS_VOICE` picks the voice.

### Settings
- **Clear history** (Settings > Data): `DELETE /api/history` empties the play history; the browser's recent searches are cleared too.

### Radio
- Stations are grouped by category (`category` field in `stations.json`) with a search box and a grid/list switch.
- Added the RTM regional stations; removed stations that were not Malaysian or whose stream had died.

### Now playing
- On desktop the player is a floating mini player (bottom right) that morphs into a floating card and back. Phones keep
  the mini player + full-screen sheet.

### Interface
- Search boxes, tabs and menu buttons share one pill style and height; the blue focus ring was removed.

## 2026-11-11

### Music tab rebuilt
- **Search-first layout.** One always-visible search bar replaces the collapsing search icon, mood chips, the
  Songs/Videos toggle and the YouTube Music home shelves.
- **Recent searches** (last 5, kept in the browser), **Recently played**, **Mostly played** (2+ plays) and
  **Suggested**.
- **Suggested** mixes YouTube Music's related tracks for your most-played and latest songs with the country's
  trending chart (`PIPLAYER_CHARTS_COUNTRY`, default `MY`). With no history it is trending alone.
- New endpoints `GET /api/history` and `GET /api/suggested`; new data file `data/history.json`.

### Reliability
- mpv is **supervised**: if it dies it is restarted and the current track resumes.
- A track that cannot be resolved or played is **skipped**; a streak as long as the queue stops playback instead of looping.
- A dropped live radio stream is **reconnected** up to 3 times.
- The next YouTube track is **prefetched**, removing the gap between songs.
- The queue, position, repeat and shuffle **survive restarts** (`data/queue.json`); they come back paused.
- The system volume is polled only while a browser is connected (previously a `wpctl` process every 2 s, always).
- The browser shows a toast when it loses the live connection and when it reconnects, and no longer breaks when the
  server returns a non-JSON error page.

### Security and robustness
- Queue items are validated: only plain YouTube ids and `http(s)` stream URLs reach mpv (previously a radio item's
  `url` was passed through unchecked). Bad numbers return 400 instead of 500.
- Every `/api` request needs a LAN-style `Host` header; cross-site writes (foreign `Origin`) are refused.
  `PIPLAYER_ALLOWED_HOSTS` adds names.
- A corrupt `stations.json` is set aside and the defaults restored (it used to make every request fail).
- `settings.json` is written atomically and flushed on shutdown.
- Still no login: keep the app on a trusted network.

### Operations
- The service now runs under **gunicorn** (1 worker, 32 threads) instead of Flask's development server, with
  `Restart=always`. **Re-copy `deploy/piplayer.service` and run `daemon-reload` when upgrading.**
- Nightly **backup** of `data/` and a weekly **yt-dlp / ytmusicapi update**, installed with
  `sudo deploy/install-maintenance.sh`.
- Dependencies pinned in `requirements.txt`; exact tested versions in `requirements.lock`.
- The project is now a git repository.

### Removed
- `GET /api/home` and `GET /api/collection/<kind>/<id>` and the code behind them (YouTube Music home feed).

### Documentation
- Every endpoint is now documented (playlists, queue move/clear, listen, shuffle and repeat were missing).
- New [user guide](docs/guide/using-the-player.md); architecture, configuration, deployment and development rewritten to match
  the code; diagrams are Mermaid flowcharts.
- Corrected: the volume is the Pi's **system** volume and always starts at 70 (the saved `volume` setting is written
  but not read back).

### Tests
- 43 tests became 66: new `test_history.py` and `test_resilience.py`; the fake mpv gained `file-loaded` and an
  "unreachable stream" mode. A timing race in one door-autoplay test was removed.

## Earlier
Radio, Music search and playback, queue and playlists, shuffle and repeat, listen on this device, restroom door
sensors with autoplay and watchdog, settings, power buttons, light and dark theme, installable manifest.
