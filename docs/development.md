# Development

## Setup and running

```bash
cd /home/pi/Documents/pi-player
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements-dev.txt        # flask, gunicorn, ytmusicapi, yt-dlp, pytest
.venv/bin/python -m piplayer                         # http://localhost:8088 (Flask development server)
```

Use a different data folder, socket and port to avoid touching the live service's files or its mpv:

```bash
PIPLAYER_PORT=8099 PIPLAYER_DATA=/tmp/cdj-data PIPLAYER_SOCKET=/tmp/cdj.sock PIPLAYER_BATHROOM_PINS= \
  .venv/bin/python -m piplayer
```

`PIPLAYER_BATHROOM_PINS=` (empty) keeps the dev copy off the GPIO pins the live service is using.
Static files are served from disk on every request, so editing HTML, CSS or JavaScript only needs a browser
refresh; Python changes need a restart.

To try the production server (gunicorn) without sound, point it at the fake mpv and a scratch folder:

```bash
PIPLAYER_DATA=/tmp/cdj-data PIPLAYER_SOCKET=/tmp/cdj.sock PIPLAYER_BATHROOM_PINS= \
PIPLAYER_MPV="$PWD/.venv/bin/python $PWD/tests/fake_mpv.py" \
  .venv/bin/gunicorn -w 1 -k gthread --threads 32 -b 127.0.0.1:8099 piplayer.wsgi:app
```

Always use `-w 1`: the player is in-process, and a second worker would start a second mpv.

## Tests

```bash
.venv/bin/pytest -q
```

The suite needs no mpv, no network and no GPIO.

| File | Covers |
|---|---|
| [tests/test_api.py](../tests/test_api.py) | Routes, queue behaviour, volume, stations CRUD, playlists, shuffle and repeat, the live event stream |
| [tests/test_doors.py](../tests/test_doors.py) | Sensors, pin and time validation, autoplay (pause, resume, hours, radio hold), watchdog, fade-in (ramp, cut short, slider override), spoken announcements (order, ducking, hours, start-up, failures) |
| [tests/test_power.py](../tests/test_power.py) | Shutdown and reboot, JSON-only protection |
| [tests/test_ytm.py](../tests/test_ytm.py) | YouTube Music result shaping |
| [tests/test_youtube.py](../tests/test_youtube.py) | YouTube kind: search shaping, id validation, `/api/trending`, `source=youtube` |
| [tests/test_soundcloud.py](../tests/test_soundcloud.py) | SoundCloud kind: permalink validation (look-alike hosts, http, bad ids), preview filtering, `source=soundcloud` |
| [tests/test_frontend.py](../tests/test_frontend.py) | Runs [tests/frontend/music_harness.js](../tests/frontend/music_harness.js) in Node (skipped without `node`): `music.js` against a tiny fake DOM and fake API |
| [tests/test_history.py](../tests/test_history.py) | Play history, Suggested (related + trending mix and fallbacks), clearing history |
| [tests/test_resilience.py](../tests/test_resilience.py) | Input validation, request guard, corrupt files, mpv restart, skip and retry, prefetch, queue persistence, JS syntax check (`node --check`) |
| [tests/conftest.py](../tests/conftest.py) | `app` and `client` fixtures; `wait_for()` for asynchronous assertions |
| [tests/fake_mpv.py](../tests/fake_mpv.py) | A stand-in for mpv's IPC. Logs every command to `<socket>.log` so tests can assert what was sent. A `loadfile` URL containing `unreachable` makes it emit an `end-file` error instead of loading. |

How the fixtures isolate the app: `create_app()` is given a `Config` with a temporary data folder, the fake
mpv, no sensor pins, and stub `resolver`, `search`, `suggest` and `trending` functions, so nothing touches the
network. Note that the resolver stub receives the **video id**, not the whole item. Door tests replace
`bathrooms._factory` with a fake button and `bathrooms._clock` with a fixed time, `bathrooms.speaker` / `_speech_ok` with a fake
speaker (`conftest.py` sets `PIPLAYER_TTS=off` so nothing is ever spoken for real) and shrink `Bathrooms.FADE_SCALE` so a fade runs in milliseconds. To test a crash, kill the fake
process (`player._proc.kill()`) and wait for the supervisor to replace it.

There are no real-browser tests. The Music pages' logic is covered by the Node harness above (rendering, tabs, grid / list,
partial failures, stale searches), but it cannot show how anything *looks*; `app.js` is only syntax-checked
(`node --check`). After changing the front end, load the page and click through the tabs you touched. Stubs for the
three platforms are `search`, `sc_search`, `yt_search` and the resolvers `resolver`, `sc_resolver`, `yt_resolver`.

## Conventions

- **Notify on change.** Anything that changes what the UI shows must end in `svc.notify()` (the player does this through `on_change`). The event stream then pushes the new state to every browser.
- **State goes in the snapshot.** New data the UI needs continuously belongs in `api._snapshot()`, not in a new endpoint. The page then gets it live for free. (Data the UI fetches on demand, like history and suggestions, can be its own endpoint.)
- **Never use `current_app` in a generator.** The request context is gone while streaming. Resolve the service first and pass it in (see `/api/events`).
- **Validate input server-side.** Queue items must go through `playlists.clean_items()`; read request bodies with `_body()` and numbers with `_num()` so bad input is a 400, never a 500.
- **Config is validated server-side**, then saved through `Settings.set`. The UI only displays what the server accepted.
- **Hardware and subprocess code never raises into the app.** GPIO failures are caught and surfaced as `doors.error`; `Player._send` returns `False` when mpv is down.
- **Files are written atomically** (temp file, then `os.replace`). New stores should follow `HistoryStore` or `Settings`.
- **Front end:** no framework or build step. Use the existing design tokens in `app.css` and the shared helpers in `app.js` (`api`, `el`, `toast`, `trackRow`, `enhanceSelect`). Build text with `el()` / `textContent`; only put trusted, static markup in `innerHTML`.
- **Docs:** keep them in step with the code. Diagrams are [Mermaid](https://mermaid.js.org/) (they render on GitHub and in VS Code's Markdown preview). Update [CHANGELOG.md](../CHANGELOG.md) for anything a user or operator would notice.

## Adding an endpoint

1. Add the route to [api.py](../piplayer/api.py) using the `@bp.get/post/...` decorators and `_svc()`. The request guard in `_guard()` already covers it.
2. Validate input and return `jsonify(error=...), <status>` on failure.
3. If it changes shared state, call `svc.notify()` (or go through a service method that does).
4. Add a test in `tests/`.
5. Document it in [api.md](api.md), including the summary table.

## Adding a setting

1. Add a default to the `Settings(...)` call in [app.py](../piplayer/app.py), or read it with a fallback like `Bathrooms.config()`.
2. Validate and save it in the service's `configure()` method.
3. Expose it through the snapshot, and add the control to the Settings page in `index.html` and `app.js` (`paintDoors` / the form handler show the pattern).
4. Document it in [configuration.md](configuration.md).

## Security notes for contributors

- The API is unauthenticated by design (trusted network). Do not add endpoints that run arbitrary commands or open arbitrary paths or URLs.
- State-changing endpoints with serious effects (power) require a JSON request, which blocks cross-site form posts. Every `/api` request is also checked for a LAN-style `Host`, and writes with a foreign `Origin` are refused.
- Anything that reaches mpv (queue items, station URLs) must be an `http(s)` URL or a plain YouTube video id. Station URLs are checked when they are added; queue items are checked again by `clean_items()`.
- If you add authentication later, start with the write endpoints and `/api/system/*`, and send the credential in a header (not a cookie) so cross-site requests stay impossible.
