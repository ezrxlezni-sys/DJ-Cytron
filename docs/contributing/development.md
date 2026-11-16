# Development

How to run the app on a development machine, the conventions the code follows, and the recipes for common changes.
Read the [Architecture overview](../architecture/overview.md) first.

## Setup and running

```bash
cd /home/pi/Documents/pi-player
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt pytest       # the app packages plus pytest
.venv/bin/python -m piplayer                           # http://localhost:8088 (Flask development server)
```

`--system-site-packages` is only needed for GPIO on a Pi. On another computer omit it; the sensors then report
`Sensor error` and everything else works. You still need `mpv` installed to hear anything (or use the fake mpv below).

### Running a scratch copy

Use a different data folder, socket and port to avoid touching the live service's files or its mpv:

```bash
PIPLAYER_PORT=8099 PIPLAYER_DATA=/tmp/cdj-data PIPLAYER_SOCKET=/tmp/cdj.sock PIPLAYER_BATHROOM_PINS= \
  .venv/bin/python -m piplayer
```

`PIPLAYER_BATHROOM_PINS=` (empty) keeps the dev copy off the GPIO pins the live service is using. Static files are
served from disk on every request, so editing HTML, CSS or JavaScript only needs a browser refresh; Python changes
need a restart.

To try the production server (gunicorn) without sound, point it at the fake mpv and a scratch folder:

```bash
PIPLAYER_DATA=/tmp/cdj-data PIPLAYER_SOCKET=/tmp/cdj.sock PIPLAYER_BATHROOM_PINS= \
PIPLAYER_MPV="$PWD/.venv/bin/python $PWD/tests/fake_mpv.py" \
  .venv/bin/gunicorn -w 1 -k gthread --threads 32 -b 127.0.0.1:8099 piplayer.wsgi:app
```

Always use `-w 1`: the player is in-process, and a second worker would start a second mpv.

## Code map

| I want to change... | Look in |
|---|---|
| A route or request check | [api.py](../../piplayer/api.py) |
| Playback, queue, volume, mpv handling | [player.py](../../piplayer/player.py) |
| Door rules, fades, announcements timing, watchdog | [bathrooms.py](../../piplayer/bathrooms.py) |
| Speech engines | [speech.py](../../piplayer/speech.py) |
| A music source | [ytm.py](../../piplayer/ytm.py), [youtube.py](../../piplayer/youtube.py), [soundcloud.py](../../piplayer/soundcloud.py) |
| What counts as a valid queue item | `clean_items()` in [playlists.py](../../piplayer/playlists.py) |
| Wiring and start-up | [app.py](../../piplayer/app.py) |
| The UI | [static/](../../piplayer/static/) |

## Conventions

- **Notify on change.** Anything that changes what the UI shows must end in `svc.notify()` (the player does this
  through `on_change`). The event stream then pushes the new state to every browser.
- **State goes in the snapshot.** New data the UI needs continuously belongs in `api._snapshot()`, not in a new
  endpoint. The page then gets it live for free. (Data the UI fetches on demand, like history and suggestions, can be
  its own endpoint.)
- **Never use `current_app` in a generator.** The request context is gone while streaming. Resolve the service first
  and pass it in (see `/api/events`).
- **Validate input server-side.** Queue items must go through `playlists.clean_items()`; read request bodies with
  `_body()` and numbers with `_num()` so bad input is a 400, never a 500.
- **Config is validated server-side**, then saved through `Settings.set`. The UI only displays what the server accepted.
- **Hardware and subprocess code never raises into the app.** GPIO failures are caught and surfaced as `doors.error`;
  `Player._send` returns `False` when mpv is down.
- **No shell.** Start subprocesses with argument lists.
- **Files are written atomically** (temp file, then `os.replace`). New stores should follow `HistoryStore` or `Settings`.
- **One worker.** Do not add anything that assumes more than one process.
- **Front end:** no framework or build step. Use the existing design tokens in `app.css` and the shared helpers in
  `app.js` (`api`, `el`, `toast`, `trackRow`, `enhanceSelect`). Build text with `el()` / `textContent`; only put
  trusted, static markup in `innerHTML`.

## Recipes

### Adding an endpoint

1. Add the route to [api.py](../../piplayer/api.py) using the `@bp.get/post/...` decorators and `_svc()`. The request
   guard in `_guard()` already covers it.
2. Validate input and return `jsonify(error=...), <status>` on failure.
3. If it changes shared state, call `svc.notify()` (or go through a service method that does).
4. Add a test in `tests/`.
5. Document it in [api.md](../reference/api.md), including the summary table.

### Adding a setting

1. Add a default to the `Settings(...)` call in [app.py](../../piplayer/app.py), or read it with a fallback like
   `Bathrooms.config()`.
2. Validate and save it in the service's `configure()` method.
3. Expose it through the snapshot, and add the control to the Settings page in `index.html` and `app.js`
   (`paintDoors` / the form handler show the pattern).
4. Document it in [configuration.md](../reference/configuration.md#settingsjson) and, if users see it,
   [Restrooms and Settings](../guide/restrooms-and-settings.md).

### Adding a music source

1. Create a module with `search(q, ...)` and `resolve(...)`, caching resolved URLs briefly (see `youtube.py`).
2. Add a `kind` to `clean_items()` with a strict id (and URL, if any) check.
3. Teach `Services._resolve` and the `/api/search` `source=` parameter about it.
4. Add the page to `music.js` (`PLATFORMS`) and the sidebar in `index.html`.
5. Add tests with a stub search and a stub resolver (see `tests/test_youtube.py`).
6. Update [Player and playback](../architecture/player.md#music-sources), [api.md](../reference/api.md), the user guide
   and the changelog.

### Adding a radio station to the defaults

Add an object to `piplayer/defaults/stations.json` (`id`, `title`, `url`, `thumb`, `category`) and a logo under
`piplayer/static/logos/`. Existing installs keep their own `data/stations.json`; only fresh installs and resets see it.

## Documentation

The docs are part of the product. In the same change as the code:

| If you change... | Update |
|---|---|
| An endpoint or the state | [reference/api.md](../reference/api.md) |
| An environment variable or `settings.json` key | [reference/configuration.md](../reference/configuration.md) |
| A data file | [reference/data-files.md](../reference/data-files.md) |
| What a user sees | [guide/](../guide/using-the-player.md) |
| Install, service or timers | [admin/](../admin/installation.md) |
| Door behaviour | [doors/](../doors/autoplay.md) |
| Structure, threads or a major choice | [architecture/](../architecture/overview.md) |
| Anything a user or operator would notice | [CHANGELOG.md](../../CHANGELOG.md) |

Style: write for the reader's job, not the code's structure; give commands that can be pasted; state defaults and
units; use sentence-case headings; diagrams are Mermaid. Keep one fact in one place and link to it. Check links by
running the link checker in [Testing](testing.md#checking-the-docs).

## Security rules

- The API is unauthenticated by design (trusted network). Do not add endpoints that run arbitrary commands or open
  arbitrary paths or URLs.
- State-changing endpoints with serious effects (power) require a JSON request, which blocks cross-site form posts.
  Every `/api` request is also checked for a LAN-style `Host`, and writes with a foreign `Origin` are refused.
- Anything that reaches mpv (queue items, station URLs) must be an `http(s)` URL or a plain id. Station URLs are
  checked when they are added; queue items are checked again by `clean_items()`.
- If you add authentication later, start with the write endpoints and `/api/system/*`, and send the credential in a
  header (not a cookie) so cross-site requests stay impossible.

## Release checklist

1. `.venv/bin/pytest -q` passes.
2. Docs updated and links check clean.
3. [CHANGELOG.md](../../CHANGELOG.md) has an entry under today's date.
4. If `deploy/` changed, the changelog says to re-copy the unit and `daemon-reload`.
5. If dependencies changed, regenerate the lock: `.venv/bin/pip freeze --local > requirements.lock`.
6. Commit; on the Pi, follow [Upgrading the app](../admin/maintenance.md#upgrading-the-app).
