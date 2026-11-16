# Maintenance

Everything the app stores lives in `data/`. Two systemd timers back it up and keep YouTube playback working. This
page covers backups, updates, upgrades, resets and logs.

## Installing the timers

Install them once:

```bash
cd /home/pi/Documents/pi-player
sudo deploy/install-maintenance.sh      # installs and starts both timers
systemctl list-timers 'piplayer-*'
```

| Timer | When | What |
|---|---|---|
| `piplayer-backup` | every night 03:30 (catches up after a missed run) | [deploy/backup.sh](../../deploy/backup.sh) archives `data/` to `~/backups/cytron-dj/data-YYYY-MM-DD.tar.gz` and keeps the newest 14 |
| `piplayer-update` | Sundays about 04:00 (plus up to 15 min random delay) | [deploy/update-deps.sh](../../deploy/update-deps.sh) upgrades `yt-dlp` and `ytmusicapi`, and restarts the service **only if** something changed |

## Backups

**What is backed up:** the whole `data/` folder (stations, playlists, history, settings, queue, and any downloaded
voice files and speech cache). The program code is not, because it is in git.

**Manual backup:**

```bash
cd /home/pi/Documents/pi-player
deploy/backup.sh                          # to ~/backups/cytron-dj
BACKUP_DIR=/media/usb/backups deploy/backup.sh
```

A second backup on the same day replaces the first. For safety against a dead SD card, copy `~/backups/cytron-dj`
to another machine from time to time.

**Restore a backup:**

```bash
sudo systemctl stop piplayer
tar -xzf ~/backups/cytron-dj/data-YYYY-MM-DD.tar.gz -C /home/pi/Documents/pi-player
sudo systemctl start piplayer
```

Stop the service first so it does not overwrite the restored files when it shuts down.

## Updating yt-dlp

YouTube changes break old versions of `yt-dlp` every few weeks, which shows up as songs that will not play while
radio still works. The weekly timer handles it; to do it now:

```bash
cd /home/pi/Documents/pi-player
deploy/update-deps.sh && sudo systemctl restart piplayer
```

The script upgrades `yt-dlp` and `ytmusicapi` with pip. If either version changed, it touches `data/.deps-updated`
and the update service restarts the app. Do this first whenever YouTube, YouTube Music or SoundCloud stops working.

## Upgrading the app

After pulling new code:

```bash
cd /home/pi/Documents/pi-player
git pull
.venv/bin/pip install -r requirements.txt
# only if deploy/piplayer.service changed:
sudo cp deploy/piplayer.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl restart piplayer
```

Then hard-refresh open browser tabs (Ctrl+Shift+R) so they load the new JavaScript. Read the
[changelog](../../CHANGELOG.md) first for anything that needs a manual step. The project is a git repository and
`data/` is ignored, so pulling never touches your stations or playlists.

An old process answers new requests wrongly: for example, an old version answers `source=soundcloud` with
YouTube Music results. Always restart after deploying.

## Resetting data

Stop the service first (`sudo systemctl stop piplayer`), then:

| File | Contains | To reset |
|---|---|---|
| `data/stations.json` | Your station list | Delete it; the 71 defaults are restored on the next start |
| `data/playlists.json` | Saved playlists | Delete it to remove all playlists |
| `data/history.json` | Play counts | Delete it (or use Settings > Clear history) to reset Suggested for you |
| `data/settings.json` | Door sensor settings and the saved volume | Delete it; defaults (and the environment's pins) are used |
| `data/queue.json` | The saved queue | Delete it to start with an empty queue |
| `data/speech-cache/` | Rendered announcement audio | Delete the folder; messages are re-rendered |

Then `sudo systemctl start piplayer`. Details of each file are in [Data files](../reference/data-files.md).

## Logs

```bash
journalctl -u piplayer -f                       # live
journalctl -u piplayer -n 100 --no-pager
journalctl -u piplayer | grep speech            # announcement problems
journalctl -u piplayer-update                   # the last weekly update
journalctl -u piplayer-backup                   # the last backup
```

The log keeps playback errors, mpv restarts, sensor errors and speech failures. Nothing in it contains passwords or
tokens; there are none.

## Routine checklist

| How often | Task |
|---|---|
| Once | Install the timers, enable lingering, set the sudoers rule if you want the power buttons |
| Monthly | `systemctl list-timers 'piplayer-*'`: both should show a recent run. Copy a backup off the Pi. |
| After a YouTube outage | `deploy/update-deps.sh && sudo systemctl restart piplayer` |
| After pulling code | See [Upgrading the app](#upgrading-the-app) |
| After changing the sensors | Check Settings: `N of 2 sensors active` |
