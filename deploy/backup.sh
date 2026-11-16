#!/bin/bash
# Archive the app's data (stations, playlists, history, settings, queue) and keep the newest 14 archives.
# Usage: deploy/backup.sh            (default destination: ~/backups/cytron-dj, override with BACKUP_DIR)
# Restore: stop the service, then  tar -xzf <archive> -C /home/pi/Documents/pi-player
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${BACKUP_DIR:-$HOME/backups/cytron-dj}"
mkdir -p "$DEST"
OUT="$DEST/data-$(date +%F).tar.gz"
tar -czf "$OUT.tmp" -C "$ROOT" --exclude='*.tmp' --exclude='.deps-updated' data
mv "$OUT.tmp" "$OUT"
ls -1t "$DEST"/data-*.tar.gz | tail -n +15 | xargs -r rm --
echo "backup written: $OUT"
