#!/bin/bash
# Upgrade yt-dlp and ytmusicapi. YouTube changes break old yt-dlp versions every few weeks, so this runs weekly.
# If anything changed it leaves data/.deps-updated; the systemd unit then restarts the service to load the new code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIP="$ROOT/.venv/bin/pip"
versions() { "$PIP" freeze --local | grep -iE '^(yt-dlp|ytmusicapi)==' | sort; }
before="$(versions)"
"$PIP" install -q -U yt-dlp ytmusicapi
after="$(versions)"
if [ "$before" != "$after" ]; then
  touch "$ROOT/data/.deps-updated"
  echo "updated:"; echo "$after"
else
  echo "already up to date"
fi
