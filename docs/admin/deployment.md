# Deployment

Run Cytron DJ on boot as a systemd service, set the audio output, and allow the Reboot and Shut down buttons to
work. Install it first: [Installation](installation.md).

## Run on boot (systemd)

The unit file [deploy/piplayer.service](../../deploy/piplayer.service) runs the app under **gunicorn** as user `pi`
from `/home/pi/Documents/pi-player` on **port 80**, so the address is simply `http://cytrondj.local`.

```bash
cd /home/pi/Documents/pi-player
sudo loginctl enable-linger pi        # keeps pi's PipeWire audio session alive without a login
sudo cp deploy/piplayer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now piplayer
```

Then open `http://cytrondj.local`. Also install the [nightly backup and weekly updates](maintenance.md#installing-the-timers).

### Changing the install location or user

If you install the project somewhere else, or use another user, edit these in the unit first: `User=`,
`WorkingDirectory=`, `ExecStart=` and `XDG_RUNTIME_DIR=` (`/run/user/<uid>`). The maintenance units
(`deploy/piplayer-backup.service` and `deploy/piplayer-update.service`) also hard-code `User=pi` and
`/home/pi/Documents/pi-player/...` paths: edit them before running `deploy/install-maintenance.sh`.
The scripts themselves (`backup.sh`, `update-deps.sh`) find the project from their own location.

### What the unit sets

| Line | Purpose |
|---|---|
| `After=network-online.target sound.target user@1000.service` | Start after the network and the user's audio session |
| `ExecStart=... gunicorn --workers 1 --worker-class gthread --threads 32 --bind 0.0.0.0:80 --timeout 120 --graceful-timeout 5 piplayer.wsgi:app` | Production server on port 80. **One worker only**: the player (mpv) lives inside the process, a second worker would start a second mpv. Threads serve browsers; each live-update and Listen stream holds one. A restart waits at most 5 s for them to disconnect. |
| `AmbientCapabilities=CAP_NET_BIND_SERVICE` | Lets a non-root user bind port 80 |
| `Environment=XDG_RUNTIME_DIR=/run/user/1000` | mpv finds PipeWire |
| `Environment=LG_WD=/tmp` | Keeps the GPIO library's pipe (`.lgd-nfy*`) out of the project folder |
| `Restart=always`, `RestartSec=5`, `TimeoutStopSec=15` | Restart after a crash or any unexpected exit |

Optional `Environment=` lines (commented in the unit): `PIPLAYER_BATHROOM_PINS`, `PIPLAYER_CHARTS_COUNTRY`,
`PIPLAYER_ALLOWED_HOSTS`. All variables are in [Configuration](../reference/configuration.md). After editing the
unit run `sudo systemctl daemon-reload && sudo systemctl restart piplayer`.

### Day-to-day commands

```bash
sudo systemctl restart piplayer       # after changing code (run daemon-reload too after unit edits)
sudo systemctl status piplayer
journalctl -u piplayer -f             # live log
journalctl -u piplayer -n 100 --no-pager
```

Restarting stops the music for a few seconds; the queue comes back afterwards but is not played automatically.

## Audio output

mpv plays to PipeWire's **default output**. On a Pi 4 that is usually the 3.5 mm headphone jack, but HDMI, USB and
Bluetooth outputs also appear.

```bash
export XDG_RUNTIME_DIR=/run/user/1000
wpctl status                          # the starred sink under "Sinks" is the default
wpctl set-default <sink-id>           # e.g. the HDMI sink
wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.8
```

The volume slider in the app **is** the system output volume (the same one `wpctl` changes), so there is only one
volume to set. Each time the service starts it sets the volume to 70 %. To use a different mpv audio device instead
of the default sink, set `PIPLAYER_MPV`, for example `PIPLAYER_MPV="mpv --audio-device=alsa/plughw:2"`.

Spoken door announcements and Listen use the same default sink, so they follow it.

## Reboot and shutdown permissions

The Reboot and Shut down buttons call `systemctl poweroff` / `systemctl reboot` as the service user, and retry with
`sudo -n`. If the app answers *"Not allowed to shutdown..."*, grant `pi` permission with a sudoers rule:

```bash
echo 'pi ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl reboot' \
  | sudo tee /etc/sudoers.d/piplayer >/dev/null \
  && sudo chmod 440 /etc/sudoers.d/piplayer \
  && sudo visudo -cf /etc/sudoers.d/piplayer
```

`visudo -cf` must print `parsed OK`. If it reports an error, delete the file with `sudo rm /etc/sudoers.d/piplayer`
immediately: a broken sudoers file can lock you out of `sudo`. Check the path with `which systemctl` and use that
path in the rule if it is not `/usr/bin/systemctl`.

If you would rather not let the app power the Pi off, skip this step: the buttons then show the error and do nothing.

## Using a different port or address

- **Production port:** change `--bind 0.0.0.0:80` in the unit. Without `CAP_NET_BIND_SERVICE` only ports above 1023 work.
- **Local only:** bind to `127.0.0.1:<port>` and put a reverse proxy in front if you need one. Keep the proxy on the LAN and
  add its public name to `PIPLAYER_ALLOWED_HOSTS`. Disable proxy buffering for `/api/events` and `/api/listen`
  (the app already sends `X-Accel-Buffering: no`).
- **Real domain name:** add it to `PIPLAYER_ALLOWED_HOSTS`, otherwise the request guard answers 403. See
  [Security](security.md).

## Health checks

| Check | Command | Healthy |
|---|---|---|
| Service running | `systemctl is-active piplayer` | `active` |
| Web server answering | `curl -s http://cytrondj.local/api/state \| head -c 200` | a JSON object (queue, volume, `bathrooms`, `doors`) |
| Live stream working | `curl -N http://cytrondj.local/api/events` | `data: {...}` lines |
| Timers installed | `systemctl list-timers 'piplayer-*'` | backup and update listed |
| Audio engine | `journalctl -u piplayer -n 50` | no repeated `Audio engine restarted` |
