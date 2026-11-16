# Using the player

Cytron DJ plays music through the speakers connected to the Pi. You control it from any phone or computer on the
same network. Open **http://cytrondj.local** in a browser (or the Pi's IP address if that name does not work).
Everyone sees the same thing live: if a colleague changes the song, your screen updates by itself.

> Anyone who opens the page can control the music. There is no login. See [Security](../admin/security.md).

The music plays **on the Pi**, not on your phone, so it keeps going when you close the page.

## The screen

| Where | What |
|---|---|
| **Sidebar** (desktop) or **bottom bar** (phone) | Radio, Music, Queue, Restrooms, Settings. The desktop sidebar also has a **Platforms** group (YouTube Music, YouTube, SoundCloud). The sun / moon button switches light and dark. |
| **Mini player** (bottom right on desktop, above the bar on a phone) | What is playing now. Click or tap it to open the full player: a floating card on desktop, a full-screen sheet on a phone. Close it with the arrow, Esc, a click outside the card (desktop) or a swipe down (phone). It is hidden while nothing is queued. |
| **Reboot / Shut down** (bottom of the sidebar) | Restarts or turns off the Pi after you confirm. |

The page can be installed to a phone's home screen (it has an app icon and manifest). It needs the network to work:
there is no offline mode.

## Radio

A grid of live internet radio stations. **Tap a station to play it.** It replaces whatever was playing.

The **⋮** menu at the top right lets you:

- **Add station**: give it a name and a stream address (a link that starts with `http://` or `https://` and ends in
  something like `.mp3`, `.aac` or `.m3u8`).
- **Edit stations**: rename, change the address, or remove a station.

Stations are grouped under headings (Popular, Chinese, English & Talk, Tamil, Islamic, RTM National, RTM Regional,
Community & Online). Stations you add yourself are listed last under **My stations**. Use the **search box** to
filter by name or group, and the **grid / list** switch to change the layout. Your layout choice is remembered in
this browser.

For live radio the player shows the station's current track title when the station sends one. There is no seek
bar, because a live stream has no length.

## Music

Music has a **home page** and **one page per platform**. On a computer the platforms are in the sidebar under
**Platforms**; on a phone, open them from the cards on the Music page (the back arrow returns to Music).

| Page | What it is for |
|---|---|
| **Music** (home) | One search box for everything. Results come from all three platforms, with tabs **All · YouTube Music · YouTube · SoundCloud**. Before you search: platform cards, **Trending now** and **Suggested for you**. |
| **YouTube Music** | Songs. Before you search: the trending chart and suggestions. |
| **YouTube** | Any YouTube video, live stream or podcast, played as audio. Shown as a grid of 16:9 pictures (switch to a list with the layout buttons). |
| **SoundCloud** | Remixes, DJ sets and independent artists. Songs from major labels are only 30-second previews on SoundCloud, so they are hidden. |

Type in the search bar and press Enter.

- **Tap a song or card** to play it. The rest of the results follow it.
- The **+ / list icon** adds it to the end of the queue. If nothing is playing, it starts.
- The **bookmark icon** (list view) adds it to a playlist.
- **Recent searches** (your last 8, kept in this browser only) appear as chips before you search. Tap one to run it
  again, or **Clear** to remove them all.
- On the home page, **Open YouTube ›** (and so on) jumps to that platform's page with the same search.
- A newer search always wins: if you type again before the first answer arrives, the old answer is ignored.
- If one platform fails or is slow, the others still show their results.

Tip: press **/** anywhere on the page to jump to the Music search bar, and **Esc** to clear it.

### Where the suggestions come from

- **Trending now** is the YouTube Music chart for the Pi's country (Malaysia by default, set by the administrator).
- **Suggested for you** mixes YouTube Music's "related" tracks for the songs played most and most recently on this
  Pi with the trending chart, and leaves out anything played recently. On a fresh Pi with no history it is the
  chart alone.
- Only **YouTube Music** plays are remembered for suggestions. Radio, YouTube and SoundCloud plays are not.
  **Settings > Clear history** makes the Pi forget them.

## Queue and playlists

The **Queue** tab has two views, switched with the **Up next | Playlists** tabs at the top.

### Up next

Shows the song playing now, then what comes next. Drag the handle on the left of an upcoming song to reorder it,
use ✕ to remove one, and open **Played** to see what already played. The **filter** box above the list narrows it
by title or artist (Esc or ✕ clears it).

The **⋮** menu (next to the filter) offers:

- **Save as playlist**: keeps the current queue as a playlist.
- **Clear up next**: removes everything after the current song.
- **Clear all & stop**: empties the queue and stops the music (asks first).

How the queue behaves:

- Tapping a station or a song **replaces** the queue with that item (and, for a song, the rest of its list).
  The **+** buttons **append**.
- When a song ends, the next one starts by itself. At the end of the queue, playback stops (unless repeat is on).
- A song that cannot be played is skipped. If every song in a row fails, playback stops and the error is shown.
- The queue, your position in it, repeat and shuffle **survive a restart** of the Pi or the service. They come back
  paused, not playing.

### Playlists

Your saved lists. **⋮ › New playlist** makes an empty one (the ⋮ menu shows it on this tab). Open a playlist to
play it (or start from any song in it), add songs to the queue, remove songs, rename it or delete it. Add songs
with the bookmark icon in Music. A playlist can mix songs from YouTube Music, YouTube, SoundCloud and radio stations.

Playlists are shared by everyone who uses this Pi.

## Player controls

| Control | What it does |
|---|---|
| Play / pause | Pause or resume. |
| Previous / next | Next song. Previous restarts the song if it is more than 5 seconds in, otherwise goes back one. |
| **Shuffle** | Plays the queue in random order, hearing each song once per round. |
| **Repeat** | Cycles off → repeat all → repeat one. |
| Seek bar | Jump within a song (not available for live radio). |
| Volume slider and speaker button | The Pi's output volume, shared by everyone. The speaker button sets it to 0; press it again to go back to the previous level. |
| Stop | Stops playback. The queue is kept. |
| **Up next** card | Shows the next song; tap it to skip to it now. |

When the Pi starts, the volume is always set to a default of 70 and you can change it from there.

### Listen on this device

Switch this on in the player panel to hear what the Pi is playing on **your own** phone or laptop (headphones in a
different room, for example). It takes a few seconds to start, lags the speakers slightly, and works for up to 4
people at once. It plays exactly what the Pi plays, radio and music alike, at full level regardless of the Pi's
volume slider. Switch it off when you are done. If the connection drops it reconnects after 2 seconds.

## Restrooms and Settings

These two tabs are covered in [Restrooms and Settings](restrooms-and-settings.md).

## Good to know

- **Music keeps going after you close the page.** The Pi plays it, not your phone.
- **The queue survives a restart.** After the Pi or the service restarts, the queue is back (paused, not playing).
- **A song that will not play is skipped** automatically. If every song fails, playback stops and an error is shown.
- **A radio stream that drops reconnects** by itself a few times before giving up.
- **A banner says "Connection lost. Reconnecting…"** if your browser cannot reach the Pi. It recovers by itself.
- **Door sensors can start and stop the music** if the administrator turned on autoplay. See [Door autoplay](../doors/autoplay.md).
- **Several people can use it at once.** The last command wins, and everyone sees it immediately.

## If something looks wrong

| Problem | Try |
|---|---|
| The page will not open | Use the Pi's IP address instead of `cytrondj.local`. Check you are on the same network. |
| Nothing is heard | Check the volume and the speaker button, then the speakers themselves. If it still fails, ask whoever runs the Pi. |
| Radio plays but YouTube songs do not | The YouTube helper probably needs updating. It updates itself weekly; the administrator can update it now ([Maintenance](../admin/maintenance.md#updating-yt-dlp)). |
| A SoundCloud search shows fewer results than expected | Songs from major labels are only 30-second previews on SoundCloud, so they are hidden on purpose. |
| A restroom shows No sensor / Check sensor | See [Restrooms and Settings](restrooms-and-settings.md#what-the-cards-mean). |
| The screen does not match the music | Refresh the page (Ctrl+Shift+R). |

More answers are in the [FAQ](faq.md).
