"""Persistent list of radio stations (JSON file in the data dir)."""
import json
import os
import shutil
import threading
import time
from pathlib import Path

DEFAULTS = Path(__file__).parent / "defaults" / "stations.json"


class StationStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            shutil.copy(DEFAULTS, self.path)

    def _read(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
        # unreadable or not a list: keep the bad file for inspection and start over from the defaults
        if self.path.exists():
            os.replace(self.path, self.path.with_name(f"{self.path.name}.bad-{int(time.time())}"))
        shutil.copy(DEFAULTS, self.path)
        with open(self.path) as f:
            return json.load(f)

    def _write(self, items):
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(items, f, indent=2)
        os.replace(tmp, self.path)       # atomic: never leaves a half-written file

    def all(self):
        with self._lock:
            return self._read()

    def get(self, sid):
        return next((s for s in self.all() if s["id"] == sid), None)

    def add(self, title, url):
        with self._lock:
            items = self._read()
            n = max([int(s["id"][2:]) for s in items if s["id"].startswith("st") and s["id"][2:].isdigit()] + [0])
            items.append({"id": f"st{n + 1}", "title": title, "url": url})
            self._write(items)
            return items

    def update(self, sid, title, url):
        """Rename a station / change its stream URL. Returns the new list, or None if unknown."""
        with self._lock:
            items = self._read()
            st = next((s for s in items if s["id"] == sid), None)
            if st is None:
                return None
            st["title"], st["url"] = title, url
            self._write(items)
            return items

    def remove(self, sid):
        with self._lock:
            items = [s for s in self._read() if s["id"] != sid]
            self._write(items)
            return items


def as_queue_item(station):
    return {"kind": "radio", "id": station["id"], "title": station["title"],
            "url": station["url"], "thumb": station.get("thumb")}
