# HTTP API

Base URL: `http://cytrondj.local` (or `http://<pi-address>:8088` when run by hand). All API routes are under
`/api`. Request and response bodies are JSON unless stated. There is **no authentication** and no CORS headers.

Errors are `{"error": "message"}` with an appropriate status code. Every `/api` request is also subject to the
[request guard](#validation-and-the-request-guard).

## Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | The web UI (`index.html`) |
| GET | `/static/<path>` | Static assets (JS, CSS, icons, station logos, manifest) |
| GET | [`/api/state`](#get-apistate) | Full current state, once |
| GET | [`/api/events`](#get-apievents) | Live state stream (server-sent events) |
| GET | [`/api/stations`](#stations) | List radio stations |
| POST | [`/api/stations`](#post-apistations) | Add a station |
| PUT | [`/api/stations/<id>`](#put-apistationsid) | Rename or re-point a station |
| DELETE | [`/api/stations/<id>`](#delete-apistationsid) | Remove a station |
| GET | [`/api/search`](#get-apisearch) | Search YouTube Music |
| GET | [`/api/trending`](#get-apitrending) | The country's YouTube Music chart |
| GET | [`/api/history`](#get-apihistory) | Recently played and mostly played tracks |
| GET | [`/api/suggested`](#get-apisuggested) | Suggested tracks (related + trending) |
| POST | [`/api/play`](#post-apiplay) | Play a station, a playlist, items or a queue position |
| POST | [`/api/queue`](#post-apiqueue) | Append items to the queue |
| POST | [`/api/queue/move`](#post-apiqueuemove) | Reorder the queue |
| POST | [`/api/queue/clear`](#post-apiqueueclear) | Clear up next, or everything |
| DELETE | [`/api/queue/<index>`](#delete-apiqueueindex) | Remove one queue item |
| POST | [`/api/control/<action>`](#post-apicontrolaction) | Transport, volume, shuffle, repeat |
| GET | [`/api/listen`](#get-apilisten) | Audio stream of what the Pi is playing |
| GET | [`/api/playlists`](#playlists) | List playlists |
| POST | [`/api/playlists`](#post-apiplaylists) | Create a playlist |
| PUT | [`/api/playlists/<id>`](#put-apiplaylistsid) | Rename a playlist |
| DELETE | [`/api/playlists/<id>`](#delete-apiplaylistsid) | Delete a playlist |
| POST | [`/api/playlists/<id>/items`](#post-apiplaylistsiditems) | Add songs to a playlist |
| DELETE | [`/api/playlists/<id>/items/<index>`](#delete-apiplaylistsiditemsindex) | Remove one song from a playlist |
| POST | [`/api/doors/announce`](#post-apidoorsannounce) | Play a saved door message on the speakers |
| POST | [`/api/doors`](#post-apidoors) | Door sensor and autoplay settings |
| POST | [`/api/system/<action>`](#post-apisystemaction) | Reboot or shut down the Pi |

---

## State

### The state object

Returned by `GET /api/state` and pushed on every change by `GET /api/events`.

```json
{
  "playing": true,
  "paused": false,
  "loading": false,
  "held": false,
  "volume": 70,
  "position": 84.3,
  "duration": null,
  "icy": "Artist - Title",
  "error": null,
  "repeat": "off",
  "shuffle": false,
  "current": { "kind": "radio", "id": "hitz-fm", "title": "Hitz FM", "url": "https://...", "thumb": "/static/logos/hitz-fm.png" },
  "queue": [ { "kind": "radio", "id": "hitz-fm", "title": "Hitz FM", "url": "https://...", "thumb": "..." } ],
  "index": 0,
  "bathrooms": [
    { "id": "male",   "occupied": false, "since": 1793853906.3, "stale": false },
    { "id": "female", "occupied": true,  "since": 1793853747.3, "stale": false }
  ],
  "doors": {
    "pins": { "male": 12, "female": 13 },
    "active": ["female", "male"],
    "error": null,
    "autoplay": false,
    "from": "08:00",
    "to": "18:00"
  }
}
```

**Player fields**

| Field | Type | Meaning |
|---|---|---|
| `playing` | bool | mpv has something loaded (also true while paused). False when idle. |
| `paused` | bool | Paused, **or** a live stream silenced by door autoplay (`held`). The UI treats both the same. |
| `loading` | bool | Resolving a URL, buffering, or reconnecting a dropped stream. |
| `held` | bool | A live radio stream is connected but silent (set by door autoplay). |
| `volume` | int 0-100 | The Pi's **system output volume** (PipeWire default sink), shared by every client. External changes (for example `wpctl`) show up here while a browser is connected. |
| `position` | float | Seconds into the current item. Live radio reports time since connecting. |
| `duration` | float or null | Item length in seconds. Null or meaningless for radio. |
| `icy` | string or null | Live radio "now playing" title when the station sends one. |
| `error` | string or null | Last playback problem, e.g. `Could not play this item`, `Resolve failed: ...` or `Audio engine restarted`. |
| `repeat` | `"off"`, `"all"` or `"one"` | Repeat mode. |
| `shuffle` | bool | Shuffle on or off. |
| `current` | object or null | The queue item at `index`. After a restart it is the restored position, not playing. |
| `queue` | array | Queue items, see [queue items](#queue-items). |
| `index` | int | Index of the current item, `-1` when nothing has played. |

**`bathrooms`** has one entry per room (`male`, `female`):

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `male` or `female` |
| `occupied` | bool or null | `true` door closed, `false` door open, `null` no sensor or no reading |
| `since` | float or null | Unix time (seconds) of the last change |
| `stale` | bool | Sensor watchdog: no change for 4 h of opening time. See [door-sensors.md](door-sensors.md#sensor-watchdog) |

**`doors`** is the saved configuration plus status:

| Field | Type | Meaning |
|---|---|---|
| `pins` | object | BCM pin per room. `{}` means sensors are switched off. |
| `active` | array | Rooms whose sensor is actually open (`[]` if none or on error). |
| `error` | string or null | Why the sensors could not start, e.g. `ModuleNotFoundError: No module named 'gpiozero'`. |
| `autoplay` | bool | Door autoplay switch |
| `from`, `to` | `"HH:MM"` | Opening hours for autoplay and the watchdog (24-hour) |

### Queue items

The same shape is used in the queue, in search results, in playlists and as input to `/api/play` and `/api/queue`.

| Field | Applies to | Meaning |
|---|---|---|
| `kind` | all | `radio`, `ytm` (YouTube Music), `yt` (YouTube) or `sc` (SoundCloud) |
| `id` | all | Station id, YouTube / YouTube Music video id (letters, digits, `-`, `_`; exactly 11 for `yt`), or the numeric SoundCloud track id |
| `title` | all | Display title |
| `url` | radio, sc | `radio`: direct stream URL, must start with `http://` or `https://`. `sc`: the track's `https://soundcloud.com/<user>/<track>` permalink (anything else is rejected). |
| `thumb` | all | Small image (station logo or 120 px cover) |
| `artist`, `duration`, `art` | ytm, yt, sc | Artist or channel, length in seconds (absent for live streams), large cover for the player panel |

Input is cleaned before use: unknown fields are dropped and text is length-limited. See
[validation](#validation-and-the-request-guard).

### GET /api/state

Returns the state object once.

```bash
curl http://cytrondj.local/api/state
```

### GET /api/events

A **server-sent events** stream (`Content-Type: text/event-stream`). The server sends the full state object as
`data: <json>` immediately, and again after every change anywhere in the system (playback, volume, queue, door
sensor, settings). While nothing changes it sends a `: keepalive` comment every 15 seconds.

```bash
curl -N http://cytrondj.local/api/events
```

```js
const es = new EventSource('/api/events');
es.onmessage = e => render(JSON.parse(e.data));   // EventSource reconnects by itself
```

Each open stream occupies one server thread. While at least one stream is open the server also polls the system
volume every 2 seconds, so changes made outside the app reach the page.

---

## Stations

A station is `{ "id": string, "title": string, "url": string, "thumb"?: string, "category"?: string }`. Ids of stations you add look
like `st1`, `st2`, ... The 71 built-in stations have readable ids such as `hitz-fm`. `category` is the heading the station is listed under
on the Radio tab; `PUT` keeps it, and stations without one are listed last as "My stations".

### GET /api/stations

Returns the array of stations.

### POST /api/stations

Add a station.

```json
{ "title": "My Station", "url": "https://example.com/stream.mp3" }
```

Returns the **full updated list**. `400` if `title` is empty or `url` does not start with `http://` or `https://`.

### PUT /api/stations/&lt;id&gt;

Change a station's `title` and `url` (same body and validation as POST). Returns the full updated list. `404` for
an unknown id.

### DELETE /api/stations/&lt;id&gt;

Remove a station. Returns the full updated list (also when the id did not exist).

---

## Music

### GET /api/search

| Query | Meaning |
|---|---|
| `q` | Search text. An empty `q` returns `[]`. |
| `type` | `songs` (default) or `videos`. Any other value is treated as `songs`. Only used for YouTube Music. |
| `source` | Omit for YouTube Music. `youtube` searches all of YouTube (items have `kind: "yt"`); `soundcloud` searches SoundCloud (items have `kind: "sc"`, a `url` permalink, and 30-second previews are dropped). |

Returns up to 20 results:

```json
[ { "kind": "ytm", "id": "fHI8X4OXluQ", "title": "Blinding Lights", "artist": "The Weeknd",
    "duration": 200, "thumb": "https://...", "art": "https://...=w544-h544" } ]
```

`502` with an error message if YouTube Music cannot be reached. Results can be passed straight back to
`/api/play` or `/api/queue` as `items`.

### GET /api/trending

The country's YouTube Music chart (`PIPLAYER_CHARTS_COUNTRY`, default `MY`), cached for an hour. Same item shape as search.
`502` with `{"error": ...}` if the chart cannot be fetched.

### GET /api/history

What has been played on this Pi (YouTube Music tracks only; radio is not counted). A track is counted when it
starts loading into the player.

```json
{ "recent": [ { "kind": "ytm", "id": "...", "title": "...", "artist": "...", "duration": 200,
                "thumb": "...", "art": "...", "plays": 3, "last": 1793927826.1 } ],
  "top":    [ ... ] }
```

`recent` is the last 8 played, newest first. `top` is up to 8 tracks played **at least twice**, most played first
(ties go to the one played last). Both arrays can be empty. History keeps the 300 most recently played tracks.

### DELETE /api/history

Forgets the whole play history (Recently played counts and the songs suggestions are based on). Returns `{"ok": true}`.
Settings > **Clear history** calls this.

### GET /api/suggested

Up to 10 tracks to suggest, never ones that were played recently:

1. **Related**: YouTube Music's "radio" for your most-played and your latest track.
2. **Trending**: the country's YouTube Music chart (`PIPLAYER_CHARTS_COUNTRY`, default `MY`).

The two lists alternate. With no play history it is trending alone. If a source fails the other is used; if both
fail it falls back to a "top hits" search, and only if that fails too is the answer `502`. Related lists are cached for 10
minutes and the chart for 1 hour.

---

## Playback

### POST /api/play

Start playing. Send **one** of:

| Body | Effect |
|---|---|
| `{"station": "hitz-fm"}` | Replace the queue with that station and play it. `404` if unknown. |
| `{"playlist": "pl1", "from": 2}` | Replace the queue with that playlist, starting at item `from` (default 0). `404` if the playlist is unknown or has nothing playable. |
| `{"items": [ ...queue items ]}` | Replace the queue with these items and play the first. `400` (`no playable items`) if none survive [validation](#validation-and-the-request-guard). |
| `{"index": 3}` | Play the item at that position of the current queue. `400` if not a number. |

`400` (`nothing to play`) if none of these is present. Returns `{"ok": true}` immediately; playback starts
asynchronously (watch `loading` in the state stream). YouTube items are resolved to a stream URL first, which
can take a few seconds the first time. A track that cannot be played is skipped; see
[failure behaviour](deployment.md#what-happens-when-something-fails).

### POST /api/queue

Append items: `{"items": [ ...queue items ]}`. If nothing is playing, the first appended item starts playing.
Returns `{"ok": true}`, or `400` (`no playable items`).

### POST /api/queue/move

Reorder the queue: `{"from": 4, "to": 1}` moves the item at index 4 to index 1. The playing item keeps playing and
its `index` follows it. Out-of-range indices are ignored. `400` if `from` or `to` is missing or not a number.

### POST /api/queue/clear

`{"scope": "upcoming"}` (default) removes everything after the current item. `{"scope": "all"}` empties the queue
and stops playback. Returns `{"ok": true}`.

### DELETE /api/queue/&lt;index&gt;

Remove the item at that position (ignored if out of range). Removing the item that is playing moves on to the
next one. Returns `{"ok": true}`.

### POST /api/control/&lt;action&gt;

| Action | Body | Effect |
|---|---|---|
| `toggle` | none | Pause or resume. Also releases a stream held silent by door autoplay. |
| `next` | none | Next queue item (random when shuffle is on). At the end of the queue, stops. |
| `prev` | none | Restart the current item if more than 5 s in (or it is the first); otherwise the previous item (the previously heard one when shuffling). |
| `stop` | none | Stop playback. The queue is kept. |
| `seek` | `{"seconds": 42}` | Seek to an absolute position (negative values become 0). |
| `volume` | `{"value": 0-100}` | Set the system output volume (clamped to 0-100). |
| `repeat` | `{"value": "off" \| "all" \| "one"}` | Set repeat mode. Anything else counts as `off`. |
| `shuffle` | `{"value": true \| false}` | Shuffle on or off. |

Returns `{"ok": true}`. An unknown action, or an action without its field, returns `400` (`bad action`); a
non-numeric `seconds` or `value` also returns `400`.

### GET /api/listen

An `audio/mpeg` stream (128 kbit/s MP3) of exactly what the Pi is playing, captured from the audio output before the
system volume is applied. The web UI plays it from the **Listen on this device** switch.

- Needs `pw-record` (PipeWire) and `ffmpeg` on the Pi; otherwise `503` with a message.
- At most 4 listeners at once; the fifth gets `503` (`too many listeners`).
- Each listener uses one server thread and two child processes; they are stopped when the client disconnects.

```bash
curl http://cytrondj.local/api/listen --output - | mpv -
```

---

## Playlists

A playlist is `{ "id": "pl1", "name": string, "items": [ ...queue items ], "created": <unix time> }`. Names are
trimmed and limited to 80 characters. Every playlist endpoint that changes data returns the **full updated list of
playlists**.

### GET /api/playlists

Returns the array of playlists.

### POST /api/playlists

Create one: `{"name": "Friday", "items": [ ...queue items ]}` (`items` optional). `400` (`name required`) if the name
is empty. Items that fail [validation](#validation-and-the-request-guard) are dropped.

### PUT /api/playlists/&lt;id&gt;

Rename: `{"name": "New name"}`. `400` if empty, `404` for an unknown id.

### DELETE /api/playlists/&lt;id&gt;

Delete a playlist (also when the id did not exist).

### POST /api/playlists/&lt;id&gt;/items

Append songs: `{"items": [ ...queue items ]}`. `404` for an unknown id.

### DELETE /api/playlists/&lt;id&gt;/items/&lt;index&gt;

Remove the song at that position (ignored if out of range). `404` for an unknown id.

To play a playlist, use `POST /api/play` with `{"playlist": "<id>"}`.

---

## Door sensors

### POST /api/doors

Change door sensor settings. Send only the fields you want to change; all are optional.

```json
{
  "pins": { "male": 12, "female": 13 },
  "autoplay": true,
  "from": "08:00",
  "to": "18:00",
  "fade": 5,
  "fadeout": 3,
  "announce": true,
  "welcome": "Thank you for choosing Cytron DJ. Enjoy the vibe!",
  "reminder": "Please remember to flush and keep it clean.",
  "duck": 30,
  "rise": 2,
  "voice": ""
}
```

| Field | Rules |
|---|---|
| `pins` | `male` and `female` BCM numbers 2-27, all different. A missing, empty or `null` room has no sensor. Sending `pins` **restarts the sensors immediately** and forgets old readings. Sending `{}` or all-empty switches the sensors off. |
| `autoplay` | Boolean. Turning it on while nobody is in and music is playing pauses it straight away. |
| `from`, `to` | `"HH:MM"`, 24-hour. `from` later than `to` means an overnight range. |
| `fade` | Whole seconds, 0-60 (default 5; 0 = off). When a door starts or resumes the music, the volume starts low and rises to its previous level over this time. |
| `fadeout` | Whole seconds, 0-60 (default 3; 0 = off). When the last door opens, the volume falls to a low level over this time, the music pauses, and the volume is put back for the next visit. The reminder is spoken after it. |
| `announce` | Boolean (default `true`). Speak the messages below at the doors, inside the active hours. |
| `duck` | Whole number 0-100 (default 30): the music's level in % while a message is spoken over it (100 = no dip). |
| `rise` | Seconds, 0-30 (default 2): how long the music takes to return to full volume after a message (0 = instantly). |
| `voice` | `""` (automatic) or one of the installed voices listed in `voices` (a Piper voice name such as `en_GB-alan-medium`, or `espeak-ng`). |
| `welcome`, `reminder` | Text, at most 160 characters (extra spaces are collapsed); an empty string means "say nothing". Said when a door closes / opens. |

Returns `{"ok": true}`; the new configuration arrives in the state stream. `400` with one of:
`Pins must be numbers`, `Pins must be BCM GPIO numbers 2-27`, `Each room needs its own pin`,
`Times must be HH:MM`, `Fade-in must be a number of seconds`, `Fade-in must be 0-60 seconds`, `Fade-out must be a number of seconds`, `Fade-out must be 0-60 seconds`, `Messages must be text`,
`Messages can be at most 160 characters`, `Music level during a message must be 0-100 %`, `Return time must be 0-30 seconds`,
`That voice is not installed`. Nothing is saved when validation fails.

There is no `GET /api/doors`: read the `doors` object from the state. It also carries `fade`, `fadeout`, `announce`, `welcome`,
`reminder`, `duck`, `rise`, `voice`, `voices` (the installed voices), `engine` (`piper`, `espeak-ng` or `null`) and `speech` (`true` when
a speech engine is installed and usable).

### POST /api/doors/announce

Play a saved door message on the speakers (the Settings ▶ buttons): `{"which": "welcome"}` or `{"which": "reminder"}`.
Returns `{"ok": true}` straight away (the message plays in the background), or `400` with `Unknown message`,
`That message is empty`, or `Speech needs a voice: pip install piper-tts (see docs/door-sensors.md) or sudo apt install espeak-ng`.

---

## System

### POST /api/system/&lt;action&gt;

`action` is `shutdown` or `reboot`. The request **must** have `Content-Type: application/json` (any body, e.g.
`{}`); otherwise it is rejected with `415`.

| Status | Meaning |
|---|---|
| `200` `{"ok": true}` | The command was accepted; the Pi is going down. |
| `403` | The service user may not run it. See [deployment](deployment.md#shutdown-and-reboot-permissions). |
| `404` | Unknown action |
| `415` | Not a JSON request |

```bash
curl -X POST http://cytrondj.local/api/system/reboot -H 'Content-Type: application/json' -d '{}'
```

The server runs `systemctl poweroff` or `systemctl reboot`, then retries with `sudo -n` if that fails.

---

## Static files

`GET /` serves `static/index.html`. `GET /static/<path>` serves files below `piplayer/static/` (`css/`, `js/`,
`brand/`, `logos/`, `manifest.webmanifest`). Path traversal outside that folder is refused by Flask.

## Validation and the request guard

These checks run before the endpoints above and are not authentication.

* **Host.** Every `/api` request needs a LAN-style `Host` header: an IP address, `localhost`, a `*.local` name or a
  bare name such as `cytrondj`. Extra names can be allowed with `PIPLAYER_ALLOWED_HOSTS`. Anything else returns **403**
  `unknown host`. This blocks DNS-rebinding from the open internet.
* **Origin.** A write (`POST`, `PUT`, `DELETE`) whose `Origin` header names another site returns **403**
  `cross-origin request refused`.
* **Items.** `/api/play`, `/api/queue` and playlists accept only playable items: `kind: "ytm"` with an id made of
  letters, digits, `-` and `_`, or `kind: "radio"` with an `http(s)` `url`. Because the URL goes straight to mpv,
  nothing else (such as `file://`) is ever accepted. If nothing is left, the answer is **400** `no playable items`.
* **Numbers.** A non-numeric `index`, `seconds` or `value` returns **400**, never 500. A JSON body that is not an
  object is treated as empty.
* **Power.** `/api/system/*` additionally requires a JSON content type (see above).
