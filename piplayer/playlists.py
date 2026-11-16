"""Persistent user playlists (JSON file in the data dir)."""
import json
import os
import re
import threading
import time
from pathlib import Path

from . import soundcloud

KEEP = ("kind", "id", "title", "artist", "duration", "thumb", "art", "url")
_YTM_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_SC_ID = re.compile(r"^[0-9]{1,20}$")
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _str(v, n):
    return str(v).replace("\n", " ")[:n]


def clean_items(items):
    """Keep only playable, well-formed track dicts (and only the fields we store).

    A YouTube Music track needs a plain video id; a YouTube video an 11 character id; a SoundCloud track a numeric id and a soundcloud.com permalink; a radio item needs an http(s) stream URL, because the URL goes
    straight to mpv and must never be a file path or another protocol. Everything is length-limited."""
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or not it.get("id") or not it.get("title"):
            continue
        kind = it.get("kind")
        if kind == "ytm":
            if not _YTM_ID.match(str(it["id"])):
                continue
        elif kind == "radio":
            if not str(it.get("url") or "").startswith(("http://", "https://")):
                continue
        elif kind == "yt":
            if not _YT_ID.match(str(it["id"])):
                continue
        elif kind == "sc":
            if not _SC_ID.match(str(it["id"])) or not soundcloud.is_permalink(it.get("url")):
                continue
        else:
            continue
        row = {}
        for k in KEEP:
            v = it.get(k)
            if v is None or (k == "url" and kind not in ("radio", "sc")):
                continue
            if k == "duration":
                if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 86400 * 7:
                    row[k] = v
            elif k in ("kind", "id"):
                row[k] = _str(v, 64) if k == "id" else kind
            else:
                row[k] = _str(v, 500 if k in ("thumb", "art", "url") else 200)
        out.append(row)
    return out


class PlaylistStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        try:
            with open(self.path) as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def _write(self, lists):
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(lists, f, indent=2)
        os.replace(tmp, self.path)       # atomic

    def all(self):
        with self._lock:
            return self._read()

    def get(self, pid):
        return next((p for p in self.all() if p["id"] == pid), None)

    def create(self, name, items=()):
        with self._lock:
            lists = self._read()
            n = max([int(p["id"][2:]) for p in lists if p["id"].startswith("pl") and p["id"][2:].isdigit()] + [0])
            pl = {"id": f"pl{n + 1}", "name": name, "items": clean_items(list(items)), "created": int(time.time())}
            lists.append(pl)
            self._write(lists)
            return pl

    def _edit(self, pid, fn):
        with self._lock:
            lists = self._read()
            pl = next((p for p in lists if p["id"] == pid), None)
            if pl is None:
                return None
            fn(pl)
            self._write(lists)
            return pl

    def rename(self, pid, name):
        return self._edit(pid, lambda p: p.__setitem__("name", name))

    def add_items(self, pid, items):
        return self._edit(pid, lambda p: p["items"].extend(clean_items(items)))

    def remove_item(self, pid, i):
        def fn(p):
            if 0 <= i < len(p["items"]):
                del p["items"][i]
        return self._edit(pid, fn)

    def delete(self, pid):
        with self._lock:
            self._write([p for p in self._read() if p["id"] != pid])
