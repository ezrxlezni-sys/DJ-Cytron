# Data files

Everything the app stores lives in the `data/` folder (`PIPLAYER_DATA` changes the location). It is git-ignored,
created on first run, and archived nightly ([Maintenance](../admin/maintenance.md#backups)).

**Stop the service before editing or deleting any of these files by hand**, otherwise the running app writes its
copy back over yours.

| Path | Holds | Written by | Reset by |
|---|---|---|---|
| `stations.json` | Radio stations | Radio tab | Delete it: the 71 built-in stations return |
| `playlists.json` | Saved playlists | Queue > Playlists | Delete it |
| `history.json` | Play counts per YouTube Music track (newest 300) | Every YouTube Music play | Settings > Clear history, or delete it |
| `settings.json` | Door and announcement settings, saved volume | Settings tab, volume slider | Delete it |
| `queue.json` | The queue, position, repeat and shuffle | Automatically, when the queue changes | Delete it |
| `voices/` | Piper voice files (`.onnx` + `.onnx.json`) | You (download) | |
| `speech-cache/` | Rendered announcement audio (WAV) | Automatically | Delete the folder |
| `.deps-updated` | Marker: yt-dlp or ytmusicapi changed | `deploy/update-deps.sh` | Removed by the update service |

All JSON files are written to a temporary file and renamed, so a crash or power cut never leaves one half-written. The
last second of changes (the settings debounce) can be lost.

## `stations.json`

A list of radio stations. Copied from `piplayer/defaults/stations.json` (71 stations) the first time the app runs,
and rewritten whenever you add, edit or remove a station.

```json
[
  { "id": "hitz-fm", "title": "Hitz FM", "url": "https://stream.rcs.revma.com/488kt4sbv4uvv",
    "thumb": "/static/logos/hitz-fm.png", "category": "Popular" },
  { "id": "st1", "title": "My Station", "url": "https://example.com/stream.mp3" }
]
```

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Unique id. Stations added in the UI get `st1`, `st2`, ... |
| `title` | yes | Name shown on the card |
| `url` | yes | Direct stream URL (`mp3`, `aac`, `m3u8`). Must start with `http://` or `https://`. |
| `thumb` | no | Logo path under `/static/`. Without it the card shows the first letter of the title. |
| `category` | no | Heading the station is listed under on the Radio tab (for example `Popular`, `RTM Regional`). Stations without one appear last under **My stations**. Stations added in the UI have none; add it by editing the file. Editing a station in the UI keeps its category. |

The built-in categories are Popular, Chinese, English & Talk, Tamil, Islamic, RTM National, RTM Regional and
Community & Online. To add a logo, put a PNG in `piplayer/static/logos/` and reference it as `/static/logos/<name>.png`.

**Damaged file:** if `stations.json` is unreadable or not a list, it is renamed `stations.json.bad-<unix time>` and the
defaults are restored, so the app never fails on it.

**Restore the built-in stations:** stop the service, delete `data/stations.json`, start it.

## `playlists.json`

A list of `{id, name, items, created}`.

```json
[ { "id": "pl1", "name": "Friday", "created": 1793927826.1,
    "items": [ { "kind": "ytm", "id": "fHI8X4OXluQ", "title": "Blinding Lights", "artist": "The Weeknd",
                 "duration": 200, "thumb": "https://...", "art": "https://..." } ] } ]
```

- `id` is `pl1`, `pl2`, ...; `name` is trimmed and at most 80 characters; `created` is Unix time.
- `items` are [queue items](api.md#queue-items). Every item is passed through the same validator as the queue, so
  unknown fields are dropped and bad items never get in.

## `history.json`

An object keyed by YouTube Music video id. Only `kind: "ytm"` plays are recorded (radio, YouTube and SoundCloud are not).

```json
{ "fHI8X4OXluQ": { "kind": "ytm", "id": "fHI8X4OXluQ", "title": "Blinding Lights", "artist": "The Weeknd",
                   "duration": 200, "thumb": "...", "art": "...", "plays": 3, "last": 1793927826.1 } }
```

`plays` is how often it started; `last` is Unix time of the latest play. Only the newest 300 entries are kept. It feeds
[Suggested for you](../guide/using-the-player.md#where-the-suggestions-come-from) and `GET /api/history`.

## `queue.json`

```json
{ "queue": [ { "kind": "radio", "id": "hitz-fm", "title": "Hitz FM", "url": "https://..." } ],
  "index": 0, "repeat": "off", "shuffle": false }
```

Saved whenever the queue, position, repeat or shuffle changes; restored on start **without playing**. Items are
re-validated on load, so a hand-edited file cannot put an unsafe URL in front of mpv.

## `settings.json`

Door and announcement settings plus a saved `volume`. Every key is described in
[Configuration](configuration.md#settingsjson).

## `voices/` and `speech-cache/`

`voices/` holds Piper voice models (about 60 MB each for a medium voice); see
[Door announcements](../doors/announcements.md#installing-a-voice). `speech-cache/` holds one WAV per rendered message,
named by a hash of the engine, voice and text; the newest 30 are kept. Both are inside `data/`, so backups include them.
