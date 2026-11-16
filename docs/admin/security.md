# Security

Cytron DJ is built for a **trusted local network**, such as an office. It has no login. This page says what that
means, what the app does to limit the damage, and how to run it safely.

## The model

| Fact | Consequence |
|---|---|
| There is **no authentication**. | Anyone who can reach the Pi's address can play music, change the stations and settings, and **reboot or shut down the Pi**. |
| There is no HTTPS. | Traffic on the LAN is plain HTTP and can be read by anyone on it. |
| The service runs as the user `pi`. | A bug that ran commands would run as `pi`. The app never builds shell commands from user input (it passes argument lists). |

### Do not expose it to the internet

Never forward its port on the router, and do not publish it through a tunnel without adding your own authentication in
front. If you need remote access, use a VPN to the LAN.

## Protections that are built in

These are **not** authentication. They stop a web page the user happens to visit, or a hostile network name, from
driving the app.

| Protection | What it does | Where |
|---|---|---|
| **Host check** | Every `/api` request needs a LAN-style `Host`: an IP, `localhost`, `*.local` or a bare name like `cytrondj`. Anything else gets 403 `unknown host`. This blocks **DNS rebinding**, where a public domain is pointed at the Pi's address to make a browser talk to it. | `api._guard` |
| **Origin check** | A write (POST, PUT, DELETE) whose `Origin` header names another site gets 403 `cross-origin request refused`. This blocks other web sites from changing settings. | `api._guard` |
| **JSON-only power** | `/api/system/*` needs a JSON content type, which a cross-site form cannot send without a CORS preflight, and the app grants none. | `api.system_power` |
| **Item validation** | Everything that reaches mpv is validated first: radio items must be `http(s)` URLs (never `file://` or paths), YouTube ids are plain id strings, SoundCloud items need a `https://soundcloud.com/...` permalink. | `playlists.clean_items`, `soundcloud.is_permalink` |
| **Station URLs** | A station URL must start with `http://` or `https://` when added. | `api.add_station` |
| **Bounded inputs** | Text is length-limited, numbers are checked, bodies that are not JSON objects count as empty, so bad input is a 400, not a crash. | `api._body`, `api._num` |
| **No shell** | Subprocesses (mpv, wpctl, pw-record, ffmpeg, pw-play, systemctl) are started with argument lists. mpv is started from `PIPLAYER_MPV` which is administrator-controlled. | |
| **Listener limit** | At most 4 Listen streams at once. | `api.MAX_LISTENERS` |
| **Atomic files** | Data files are written to a temporary file then renamed, so a crash cannot leave one half-written. | |

The front end builds text with `textContent`, never with untrusted HTML.

## Hardening checklist

1. Keep the Pi on a private network segment. Do not port-forward it.
2. Leave `PIPLAYER_ALLOWED_HOSTS` empty unless you must use a real domain name.
3. Skip the sudoers rule ([Deployment](deployment.md#reboot-and-shutdown-permissions)) if people should not be able to power the Pi off. The
   buttons then answer "Not allowed" and the Pi stays on.
4. Keep the OS updated (`sudo apt update && sudo apt full-upgrade`) and `yt-dlp` updated ([Maintenance](maintenance.md)).
5. Do not run the service as root. Port 80 works without root through `CAP_NET_BIND_SERVICE`.
6. If you must reach it from outside, put it behind a VPN or an authenticating reverse proxy and keep the proxy on HTTPS.

## What the app sends and receives

| To | What | Why |
|---|---|---|
| YouTube Music, YouTube, SoundCloud | Search words, track ids | Searching and finding the audio stream. Requests come from the Pi's IP address. |
| Radio stations | A normal stream request | Playing. |
| Nowhere else | | Speech is generated on the Pi. There is no analytics, update ping or telemetry. (`pip` contacts PyPI when you install or update packages.) |

The app uses **no account** on any platform; ytmusicapi is used unauthenticated. Play history is stored on the Pi in
`data/history.json`; **Settings > Clear history** removes it.

## Adding authentication later

If you add a login, start with the write endpoints and `/api/system/*`, and send the credential in a header (not a
cookie) so cross-site requests stay impossible. Details for contributors are in
[Development](../contributing/development.md#security-rules).

## Reporting a problem

If you find a security issue, tell the project owner privately rather than posting it publicly.
