# Front end

The browser app is plain HTML, CSS and JavaScript served from disk: no framework, no bundler, no build step, and
no external requests apart from station artwork, YouTube thumbnails and the streams themselves.

| File | Role |
|---|---|
| [static/index.html](../../piplayer/static/index.html) | Page skeleton: sidebar, bottom bar, panes, dialogs, the Settings form |
| [static/css/app.css](../../piplayer/static/css/app.css) | Layout, components, light and dark themes |
| [static/css/music.css](../../piplayer/static/css/music.css) | Styles for the Music pages |
| [static/js/app.js](../../piplayer/static/js/app.js) | State, rendering, Radio, Queue, Playlists, Restrooms, Settings, Now playing, the shared helpers |
| [static/js/music.js](../../piplayer/static/js/music.js) | The Music home and the three platform pages |
| `static/brand/`, `static/logos/` | App icons and radio station logos |
| `static/manifest.webmanifest` | Lets the page be installed to a home screen |

Design tokens (`--primary`, `--muted`, `--radius`, ...) follow the shadcn / ReUI convention, with a light and a dark
theme. The theme is applied by an inline script in `<head>` before the CSS loads so there is no flash.

## Data flow

- On load the page fetches `/api/stations` and `/api/state`, renders, then opens `EventSource('/api/events')`.
  Every message replaces the in-memory state `S` and calls `render()`. If the stream drops, a toast says so; the
  browser reconnects by itself and the first message re-syncs everything.
- `api()` returns `{error}` for a non-JSON reply (such as a 500 page) instead of throwing.
- Actions (play, queue, settings) are `fetch()` calls; their visible result arrives through the event stream, not the
  response. The UI never assumes a command worked.

## Navigation

Navigation is tabs: sidebar on desktop, bottom bar on mobile. The panes are `radio`, `music`, `ytm`, `yt`, `sc`,
`queue`, `rooms` and `settings`. Browser-only preferences live in `localStorage`:

| Key | Holds |
|---|---|
| `cdj-tab` | Selected tab |
| `cdj-theme` | `dark` or light |
| `cdj-recent` | Recent searches (newest 8) |
| `cdj-mview` | Grid or list per Music platform page |
| `cdj-stview` | Radio layout (grid or list) |

All reads and writes of `localStorage` are wrapped in `try/catch`: the app works without it.

## Music

Built by [js/music.js](../../piplayer/static/js/music.js); the panes `music`, `ytm`, `yt` and `sc` are empty in
`index.html` and filled on first visit.

- The home page searches all three platforms in parallel (`/api/search` with `source=` omitted, `youtube`,
  `soundcloud`) and fills each section as its source answers; the platform pages search one source.
- Idle shelves: **Trending now** (`/api/trending`) and **Suggested for you** (`/api/suggested`, loaded separately so it
  never delays the rest).
- A newer search always discards the answers of an older one (a per-pane generation counter).
- A failing source leaves its section empty without affecting the others.

## Radio

Stations are grouped by their `category` and filtered in place: cards are hidden, not rebuilt, so playback state never
flickers.

## Now playing

One fixed card. On desktop it is a floating mini player that opens into a card in the same corner: the card's width,
height and radius are CSS transitions and the cover is flown between its two sizes with the Web Animations API
(`npMorph` in `app.js`) using the same duration and easing. On mobile it is a mini player plus an expandable
full-screen sheet. **Listen on this device** plays `/api/listen` in an `Audio` element and reconnects after 2 s if it
drops.

## Settings form

The form is filled from `S.doors` (it arrives with the normal state stream) and saved with `POST /api/doors`. The
server validates and the UI shows whatever the server accepted (including an error message from a 400).

## Accessibility and input

- Icon buttons carry `aria-label`s; the popup menus support arrow keys, Home, and Escape.
- `/` focuses the Music search; Esc clears it or closes a popup.
- Touch: swipe down closes the phone's full-screen player.

## Helpers worth reusing

`api` (fetch wrapper), `el` (build elements without innerHTML), `toast`, `trackRow`, `enhanceSelect`. Build text with
`el()` or `textContent`; only put trusted, static markup in `innerHTML`.

## Testing

`app.js` is syntax-checked (`node --check`). `music.js` has a Node harness with a tiny fake DOM and fake API. There are
no real-browser tests; after changing the front end, load the page and click through the tabs you touched. See
[Testing](../contributing/testing.md#front-end).
