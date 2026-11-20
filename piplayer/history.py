"""Play history: what was played, how often and when (JSON file in the data dir)."""
import json
import os
import threading
import time
from pathlib import Path

KEEP = ("kind", "id", "title", "artist", "duration", "thumb", "art")
MAX_ENTRIES = 300


class HistoryStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data):
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)       # atomic

    def record(self, item):
        """Count one play of a YouTube Music track. Radio stations are not tracked."""
        if not isinstance(item, dict) or item.get("kind") != "ytm" or not item.get("id") or not item.get("title"):
            return
        with self._lock:
            data = self._read()
            e = data.get(item["id"], {})
            e.update({k: item[k] for k in KEEP if item.get(k) is not None})
            e["plays"] = e.get("plays", 0) + 1
            e["last"] = time.time()
            data[item["id"]] = e
            if len(data) > MAX_ENTRIES:   # forget the least recently played
                for k in sorted(data, key=lambda k: data[k].get("last", 0))[:len(data) - MAX_ENTRIES]:
                    del data[k]
            self._write(data)

    def clear(self):
        """Forget everything that was played."""
        with self._lock:
            self._write({})

    def _entries(self):
        with self._lock:
            return [e for e in self._read().values() if isinstance(e, dict) and e.get("id")]

    def recent(self, n=8):
        return sorted(self._entries(), key=lambda e: e.get("last", 0), reverse=True)[:n]

    def top(self, n=8):
        """Most played first; ties go to whichever was played last. Needs at least two plays to count."""
        es = [e for e in self._entries() if e.get("plays", 0) >= 2]
        return sorted(es, key=lambda e: (e["plays"], e.get("last", 0)), reverse=True)[:n]

    def seeds(self, n=2):
        """Track ids to base suggestions on: the favourite plus the latest."""
        ids = []
        for e in (self.top(1) + self.recent(n)):
            if e["id"] not in ids:
                ids.append(e["id"])
        return ids[:n]
