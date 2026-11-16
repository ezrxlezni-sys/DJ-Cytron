"""SoundCloud search and audio URL resolution (both through yt-dlp, no API key needed).

A SoundCloud track is stored as {"kind": "sc", "id": <numeric track id>, "url": <permalink>, ...}. The permalink is
what we hand to yt-dlp to get a playable stream URL; it is validated (see PERMALINK) so a queue item can never make
yt-dlp fetch an arbitrary site.
"""
import re
import threading
import time

import yt_dlp

URL_TTL = 30 * 60                      # SoundCloud stream URLs are signed and expire sooner than YouTube's
PERMALINK = re.compile(r"^https://soundcloud\.com/[A-Za-z0-9_\-.%]+/[A-Za-z0-9_\-.%]+(/[A-Za-z0-9_\-.%]+)?$")
TRACK_ID = re.compile(r"^[0-9]{1,20}$")
_cache = {}                            # permalink -> (expires_at, url)
_lock = threading.Lock()


def is_permalink(url):
    return bool(PERMALINK.match(str(url or "")))


def _thumb(entry, want):
    """Pick a cover of the wanted size id (e.g. 't500x500'); fall back to the last one listed."""
    thumbs = entry.get("thumbnails") or []
    for t in thumbs:
        if t.get("id") == want and t.get("url"):
            return t["url"]
    return thumbs[-1]["url"] if thumbs and thumbs[-1].get("url") else None


def _is_preview(entry):
    """Major-label tracks are only offered as a 30 second preview without a SoundCloud Go+ login: hide those."""
    d = entry.get("duration")
    return isinstance(d, (int, float)) and 29.5 <= d <= 30.5


def search(query, kind="songs", limit=20):
    opts = {"quiet": True, "extract_flat": True, "skip_download": True, "noplaylist": False}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"scsearch{limit + 10}:{query}", download=False)     # a few extra: previews are dropped
    out = []
    for e in info.get("entries") or []:
        url, tid = e.get("webpage_url"), str(e.get("id") or "")
        if not is_permalink(url) or not TRACK_ID.match(tid) or not e.get("title") or _is_preview(e):
            continue
        small = _thumb(e, "t200x200")
        out.append({
            "kind": "sc", "id": tid, "title": e["title"], "artist": e.get("uploader") or "",
            "duration": int(e["duration"]) if e.get("duration") else None,
            "thumb": small, "art": _thumb(e, "t500x500"), "url": url,
        })
        if len(out) >= limit:
            break
    return out


def resolve(permalink):
    if not is_permalink(permalink):
        raise ValueError("not a SoundCloud track URL")
    now = time.time()
    with _lock:
        hit = _cache.get(permalink)
        if hit and hit[0] > now:
            return hit[1]
        for k in [k for k, v in _cache.items() if v[0] <= now]:                      # evict expired URLs
            _cache.pop(k, None)
    opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(permalink, download=False)
    url = info["url"]
    if "preview" in str(info.get("format_id") or ""):
        raise RuntimeError("only a 30 second preview is available for this track")
    with _lock:
        _cache[permalink] = (time.time() + URL_TTL, url)
    return url
