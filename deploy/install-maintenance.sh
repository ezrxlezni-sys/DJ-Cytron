#!/bin/bash
# Install the nightly data backup and the weekly yt-dlp update as systemd timers. Run once:  sudo deploy/install-maintenance.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/backup.sh" "$DIR/update-deps.sh"
cp "$DIR"/piplayer-backup.service "$DIR"/piplayer-backup.timer "$DIR"/piplayer-update.service "$DIR"/piplayer-update.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now piplayer-backup.timer piplayer-update.timer
systemctl list-timers 'piplayer-*' --no-pager
