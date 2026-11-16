# Design decisions

The choices that shape the system and the reasons for them. Read this before changing one of them.

## One process, one worker

**Decision.** gunicorn runs **one worker with 32 threads**.
**Why.** The player owns an mpv child process and in-memory state (queue, current track, fades). A second worker would
start a second mpv, fight over the audio device and disagree about state. Threads give enough concurrency for a LAN.
**Cost.** Each open event stream and Listen stream holds a thread, so the limit is 32 simultaneous connections
(4 of them can be Listen). Restarting stops the music briefly.

## Push the full state, not diffs

**Decision.** `/api/events` sends the complete state object on every change.
**Why.** It is tiny, and a client that reconnects or just opened the page is correct from the first message. No
sequence numbers, no replay, no drift.
**Cost.** Slightly more data per change; irrelevant on a LAN.

## Server owns the truth; the browser is a view

**Decision.** The UI sends commands and renders what the stream says.
**Why.** Many people use one player. The server's state is the only state that matters, so every screen agrees.

## Volume is the system volume

**Decision.** The slider sets the PipeWire default sink volume (`wpctl`), and mpv is pinned at 100 %.
**Why.** There is then one volume to set: the same one `wpctl` and the hardware use, and announcements and Listen
follow it. The announcement dip is the one place mpv's own volume is used, so the system volume is not disturbed.
**Cost.** The saved `volume` is not read back; every start sets 70 %. Listen captures before the system volume, so it
is always at full level.

## Silence live radio, pause everything else

**Decision.** Door autoplay mutes a live stream instead of pausing it.
**Why.** A paused internet-radio stream is dropped by the server after about a minute and takes about 4 seconds to
reconnect. Muting keeps it connected and live.
**Cost.** The stream keeps using bandwidth while "paused". The page shows it as paused anyway (`held`).

## Resolve stream URLs late, cache briefly

**Decision.** Queue items store ids, not URLs; the URL is resolved by yt-dlp when playing, with short caches.
**Why.** YouTube and SoundCloud URLs expire, and the queue can survive a restart. Prefetch of the next track hides
the resolve delay.

## yt-dlp is allowed to move

**Decision.** `yt-dlp` is `>=` pinned and upgraded weekly by a timer; `requirements.lock` records what was tested.
**Why.** YouTube changes break old versions every few weeks; a frozen version would eventually stop playing music.
**Cost.** An upgrade can break something. The lock file and git give you a way back.

## Validate everything that reaches mpv

**Decision.** Every queue item passes `clean_items()`: allowed kinds only, plain ids, `http(s)` URLs, SoundCloud
permalinks only on `soundcloud.com`, length limits.
**Why.** mpv can open files and other protocols. The API has no login, so the one place untrusted input becomes a
command must be strict.

## No authentication

**Decision.** There is no login. Instead the app refuses requests with a non-LAN `Host` and cross-site writes.
**Why.** It is an appliance on a trusted network, and a shared password on a wall-mounted music player would be
shared on a sticky note. The checks stop the realistic web attacks (DNS rebinding, cross-site forms).
**Cost.** Anyone on the network has full control, including power-off. See [Security](../admin/security.md).

## Atomic JSON files, no database

**Decision.** State is a handful of JSON files written to a temp file and renamed.
**Why.** The data is small and rarely changes, it is easy to back up (`tar`) and to edit by hand with the service
stopped, and a power cut cannot corrupt it. A database would be more to install and more to break.

## Debounced settings writes

**Decision.** `Settings` writes 1 s after the last change and again on exit.
**Why.** A volume slider drag would otherwise rewrite the SD card dozens of times a second. The cost is that the
last second of changes can be lost in a power cut.

## Reed switches without a resistor

**Decision.** Use the Pi's internal pull-up and plain normally-open reed switches.
**Why.** Two wires per door, no extra parts.
**Cost.** A disconnected wire looks like an open door. The watchdog flags a sensor that never changes, which is a
partial answer; changeover sensors would be the proper one.

## Render speech once

**Decision.** Announcements are rendered to WAV ahead of time and cached.
**Why.** A neural voice takes seconds on a Pi; the visitor must hear the message the moment the door closes.

## No front-end build step

**Decision.** Plain HTML, CSS and JavaScript served from disk.
**Why.** There is nothing to install or compile on the Pi, edits show on refresh, and the code stays small enough to
read. The cost is that there is no type checking and only a Node harness for tests.

## Fades are perceptual

**Decision.** Fades start at about 8 % and use a power curve (`FADE_CURVE = 2.0`).
**Why.** Loudness is felt logarithmically; a straight volume ramp sounds like a sudden jump at the start.
