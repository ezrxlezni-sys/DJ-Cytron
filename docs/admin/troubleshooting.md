# Troubleshooting

Find the symptom, then the fix. Start with the checks in the first section when you do not know where to look.

## First checks

```bash
systemctl status piplayer                       # is it running?
journalctl -u piplayer -n 80 --no-pager         # what did it say?
curl -s http://localhost/api/state | head -c 300   # does the API answer? (use :8088 for a hand-started copy)
curl -N http://localhost/api/events             # does the live stream send "data:" lines?
```

## The page

| Symptom | Check |
|---|---|
| Page does not load | `systemctl status piplayer`, `journalctl -u piplayer -n 50`. Is `cytrondj.local` resolving? Try the Pi's IP address. |
| `unknown host` (403) in the browser or `curl` | The `Host` header is not a LAN name. Use the IP or `cytrondj.local`, or add your domain to `PIPLAYER_ALLOWED_HOSTS`. |
| `cross-origin request refused` (403) | A page from another site (or a proxy changing `Origin`) is trying to write. Open the app directly by its address. |
| Page loads but never updates until refreshed | The event stream is failing: `curl -N http://cytrondj.local/api/events` should stream `data:` lines, not an error page. A proxy may be buffering it. |
| A banner says "Connection lost. Reconnecting…" | The browser cannot reach the Pi. It recovers by itself. Check the Pi and the network. |
| Screen is out of date after an upgrade | Hard-refresh (Ctrl+Shift+R) to load the new JavaScript. |
| Port 80 refused | The unit needs `AmbientCapabilities=CAP_NET_BIND_SERVICE`. When running by hand use the default port 8088. |
| Service keeps restarting | `journalctl -u piplayer -n 80`. A Python error at start shows there. Test by hand with `.venv/bin/python -m piplayer`. |

## Sound

| Symptom | Check |
|---|---|
| Press play, nothing is heard | `wpctl status` (right output? muted?), the app's volume and speaker button, and `journalctl -u piplayer` for mpv errors. Confirm `loginctl show-user pi` shows `Linger=yes`. |
| Sound comes out of the wrong output | `wpctl status`, then `wpctl set-default <sink-id>` ([Deployment](deployment.md#audio-output)). |
| `mpv did not create its IPC socket` | mpv is not installed (`sudo apt install mpv`) or `PIPLAYER_MPV` is wrong. |
| `Audio engine restarted` appears | mpv crashed and was restarted; playback resumes by itself. If it repeats, look in the log and check the audio output. After more than 3 crashes in a minute it restarts but does not resume the track. |
| Works by hand, silent as a service | The service has no PipeWire session: run `sudo loginctl enable-linger pi` and check `XDG_RUNTIME_DIR=/run/user/<uid>` in the unit matches `id -u pi`. |
| "Listen on this device" fails (503) | `pw-record` and `ffmpeg` must be installed (`sudo apt install ffmpeg`). A fifth simultaneous listener is refused with `too many listeners`. |
| Listen is silent | Listen records what the Pi plays. Start something playing, then switch it on. |

## Music and radio

| Symptom | Check |
|---|---|
| Radio plays but YouTube music does not | Update yt-dlp: `deploy/update-deps.sh && sudo systemctl restart piplayer`. Install `quickjs` and restart. `WARNING: No supported JavaScript runtime` in the log means no usable runtime. |
| Music shows no Trending / Suggested shelves | The Pi cannot reach YouTube Music. Search will fail the same way; check the Pi's internet connection. |
| The SoundCloud or YouTube section of a search is empty | Check the Pi's internet connection, then update yt-dlp. SoundCloud also hides 30-second major-label previews on purpose. After deploying new code, restart the service: an old process answers `source=soundcloud` / `source=youtube` with YouTube Music results. |
| A song fails with "Resolve failed" | yt-dlp could not get a stream (the video is blocked, removed, or yt-dlp is out of date). The player skips to the next song. |
| One radio station is silent | Its stream URL may have died. The player retries 3 times (2, 4, 6 s), then skips. Edit the station (Radio > ⋮ > Edit stations) with a working URL. |
| A station you added will not save | The URL must start with `http://` or `https://`. |
| Queue came back but nothing plays after a restart | By design: the queue is restored paused. Press play. |
| Playback stops by itself with an error | Every track in the queue failed in a row, so the player stopped instead of looping. Fix the cause (usually yt-dlp or the network) and play again. |
| Volume jumps back to 70 | The service sets the system volume to 70 every time it starts. |
| Many YouTube tracks suddenly fail | YouTube changed something. Update yt-dlp. If that does not help, wait: upstream fixes are usually released within days. |

## Doors and speech

For sensors and wiring see also [Door sensor hardware](../doors/hardware.md#troubleshooting),
[Door autoplay](../doors/autoplay.md#why-didnt-it-play-or-pause) and
[Door announcements](../doors/announcements.md#troubleshooting).

| Symptom | Likely cause and fix |
|---|---|
| Rooms always show **Available** | Nothing is wired (see the limit of a plain reed switch), or the magnet is too far from the switch. Check the switch with a jumper from the pin to GND: the room should turn **Occupied**. |
| Rooms always show **Occupied** | Switch wired to the wrong pin, or magnet fixed in place. |
| Badge says **Sensor error** | The reason is shown under the badge. `ModuleNotFoundError: gpiozero`: install `python3-gpiozero python3-lgpio` and make sure the virtual environment can see system packages. `GPIOPinInUse`: another program uses the pin. |
| Cards change but music does not | The autoplay switch is off, the time is outside the active hours, or you changed playback yourself since the last door change. |
| Music you started by hand keeps playing with both doors open | Autoplay acts when a door **changes** (or when the switch is turned on). Open or close a door, or toggle the switch, and it pauses. |
| A `.lgd-nfy0` file appears in the project | The service was started without `LG_WD=/tmp`. Use the unit in `deploy/`. It is safe to delete while the service is stopped. |
| Door messages are not spoken | Settings shows a notice if no voice is installed ([Installing a voice](../doors/announcements.md#installing-a-voice) or `sudo apt install espeak-ng`). Look in the log for `speech:` lines. Test with the ▶ buttons or by hand: `espeak-ng -w /tmp/t.wav "hello" && pw-play /tmp/t.wav`. Also check the switch is on, the time is inside the active hours, and the message is not empty. |
| Announcement is very quiet | A fade-in was in progress. Messages settle the volume first, so this should not happen in the current version; make sure you restarted after upgrading. |

## Power buttons

| Symptom | Check |
|---|---|
| "Not allowed to shutdown / reboot" | Add the sudoers rule in [Deployment](deployment.md#reboot-and-shutdown-permissions). |
| `415` from `/api/system/...` | The request was not JSON. Send `Content-Type: application/json`. |

## Updates and backups

| Symptom | Check |
|---|---|
| `systemctl list-timers 'piplayer-*'` shows nothing | Run `sudo deploy/install-maintenance.sh`. |
| No backups in `~/backups/cytron-dj` | `journalctl -u piplayer-backup`. The timers run as the user in the unit (`pi`); the backup folder is under that user's home. |
| Update did not restart the app | The restart happens only when `yt-dlp` or `ytmusicapi` actually changed. `journalctl -u piplayer-update` says `already up to date` otherwise. |

## Still stuck?

Collect these and look for the first error, not the last:

```bash
systemctl status piplayer --no-pager
journalctl -u piplayer -n 200 --no-pager
.venv/bin/pip freeze --local | grep -iE 'yt-dlp|ytmusicapi|flask|gunicorn|piper'
wpctl status
```

Run the app by hand to see errors on screen: stop the service, then `.venv/bin/python -m piplayer`
(see [Development](../contributing/development.md#running-a-scratch-copy)).
