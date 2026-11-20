#!/bin/bash
# Upgrade yt-dlp and ytmusicapi. YouTube changes break old yt-dlp versions every few weeks, so this runs weekly.
# The upgrade stays inside the version ranges in requirements.txt (a new major release of ytmusicapi is never pulled in
# unattended), is smoke-tested, and is rolled back to the previous versions if the new ones do not import.
# If anything changed it leaves data/.deps-updated; the systemd unit then restarts the service to load the new code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIP="$ROOT/.venv/bin/pip"
PY="$ROOT/.venv/bin/python"
versions() { "$PIP" freeze --local | grep -iE '^(yt-dlp|ytmusicapi)==' | sort; }
# the requirement lines for these two packages, e.g. "ytmusicapi~=1.12" and "yt-dlp>=2026.10"
specs() { grep -iE '^(yt-dlp|ytmusicapi)[<>=~!]' "$ROOT/requirements.txt"; }

before="$(versions)"
mapfile -t SPECS < <(specs)
[ "${#SPECS[@]}" -gt 0 ] || { echo "no yt-dlp / ytmusicapi lines in requirements.txt"; exit 1; }
"$PIP" install -q -U "${SPECS[@]}"
after="$(versions)"

if [ "$before" = "$after" ]; then
  echo "already up to date"
  exit 0
fi

if ! "$PY" -c "import yt_dlp, ytmusicapi, piplayer.ytm, piplayer.youtube, piplayer.soundcloud" 2>/dev/null; then
  echo "the new versions do not load; rolling back to:"; echo "$before"
  # shellcheck disable=SC2086
  "$PIP" install -q $(echo "$before" | tr '\n' ' ')
  exit 1
fi

# keep the lock file in step with what is installed
for line in $after; do
  name="${line%%==*}"
  sed -i -E "s/^${name}==.*/${line}/I" "$ROOT/requirements.lock"
done
touch "$ROOT/data/.deps-updated"
echo "updated:"; echo "$after"
