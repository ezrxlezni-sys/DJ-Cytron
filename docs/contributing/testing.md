# Testing

```bash
.venv/bin/pytest -q
```

The suite needs no mpv, no network and no GPIO. Configuration is in `pyproject.toml` (`pythonpath = [".", "tests"]`,
`testpaths = ["tests"]`).

## What is covered

| File | Covers |
|---|---|
| [tests/test_api.py](../../tests/test_api.py) | Routes, queue behaviour, volume, stations CRUD, playlists, shuffle and repeat, the live event stream |
| [tests/test_doors.py](../../tests/test_doors.py) | Sensors, pin and time validation, autoplay (pause, resume, hours, radio hold), watchdog, fade-in (ramp, cut short, slider override), spoken announcements (order, ducking, hours, start-up, failures) |
| [tests/test_speech.py](../../tests/test_speech.py) | Speech engines, voice selection, rendering and the cache |
| [tests/test_power.py](../../tests/test_power.py) | Shutdown and reboot, JSON-only protection |
| [tests/test_ytm.py](../../tests/test_ytm.py) | YouTube Music result shaping |
| [tests/test_youtube.py](../../tests/test_youtube.py) | YouTube kind: search shaping, id validation, `/api/trending`, `source=youtube` |
| [tests/test_soundcloud.py](../../tests/test_soundcloud.py) | SoundCloud kind: permalink validation (look-alike hosts, http, bad ids), preview filtering, `source=soundcloud` |
| [tests/test_frontend.py](../../tests/test_frontend.py) | Runs [tests/frontend/music_harness.js](../../tests/frontend/music_harness.js) in Node (skipped without `node`): `music.js` against a tiny fake DOM and fake API |
| [tests/test_history.py](../../tests/test_history.py) | Play history, Suggested (related + trending mix and fallbacks), clearing history |
| [tests/test_resilience.py](../../tests/test_resilience.py) | Input validation, request guard, corrupt files, mpv restart, skip and retry, prefetch, queue persistence, JS syntax check (`node --check`) |
| [tests/conftest.py](../../tests/conftest.py) | `app` and `client` fixtures; `wait_for()` for asynchronous assertions |
| [tests/fake_mpv.py](../../tests/fake_mpv.py) | A stand-in for mpv's IPC (see below) |

## How the app is isolated

`create_app()` is given a `Config` with a temporary data folder, the fake mpv, no sensor pins, and stub `resolver`,
`search`, `suggest` and `trending` functions, so nothing touches the network. Notes:

- The **resolver stub receives the video id**, not the whole item.
- Stubs for the three platforms are `search`, `sc_search`, `yt_search` and the resolvers `resolver`, `sc_resolver`,
  `yt_resolver`.
- Door tests replace `bathrooms._factory` with a fake button and `bathrooms._clock` with a fixed time, and
  `bathrooms.speaker` / `_speech_ok` with a fake speaker. `conftest.py` sets `PIPLAYER_TTS=off` so nothing is ever
  spoken for real.
- Door tests shrink `Bathrooms.FADE_SCALE` so a fade runs in milliseconds (and `Player.DUCK_SCALE` for the dip).
- To test a crash, kill the fake process (`player._proc.kill()`) and wait for the supervisor to replace it.

### The fake mpv

[tests/fake_mpv.py](../../tests/fake_mpv.py) speaks mpv's IPC over a unix socket. It logs every command to
`<socket>.log` so tests can assert what was sent. A `loadfile` URL containing `unreachable` makes it emit an `end-file`
error instead of loading, to test skipping and retries. It emits `file-loaded` for normal files.

## Asynchronous assertions

Most behaviour happens on threads. Use `wait_for(lambda: condition)` from `conftest.py` rather than `time.sleep`; it
polls until the condition holds or a timeout fails the test. A sleep either slows the suite or makes it flaky.

## Front end

There are no real-browser tests. The Music pages' logic is covered by the Node harness (rendering, tabs, grid / list,
partial failures, stale searches), but it cannot show how anything *looks*; `app.js` is only syntax-checked
(`node --check`). After changing the front end, load the page and click through the tabs you touched, on a phone-width
window as well as a desktop one, in both themes.

## Writing a test

1. Use the `app` / `client` fixtures; build the app with stubs for anything that would touch the network.
2. Drive the behaviour through the HTTP API where you can; reach into services only to inject fakes.
3. For door logic, set the fake clock, flip the fake button, then `wait_for` the player's state.
4. Test the failure as well as the success: bad input (400), a failing source, a missing engine.

## Checking the docs

A quick link checker (run from the project root) reports any relative Markdown link whose file is missing:

```bash
python3 - <<'EOF'
import re, pathlib
bad = 0
for md in [*pathlib.Path('docs').rglob('*.md'), pathlib.Path('README.md'), pathlib.Path('CHANGELOG.md')]:
    for m in re.finditer(r'\]\(([^)#\s]+)(#[^)]*)?\)', md.read_text()):
        t = m.group(1)
        if '://' in t or t.startswith('mailto:'):
            continue
        if not (md.parent / t).resolve().exists():
            print(f'{md}: missing {t}'); bad += 1
print('links ok' if not bad else f'{bad} broken')
EOF
```

It does not check `#anchors`; click through a few when you rename a heading.
