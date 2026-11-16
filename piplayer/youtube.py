"""YouTube (the whole catalogue, not just music) search and audio URL resolution, both through yt-dlp.

A YouTube item is {"kind": "yt", "id": <11 character video id>, ...}. It is kept apart from the "ytm" kind (YouTube Music
songs) so play history, suggestions and the "Mostly played" shelf stay about music.
"""
import re
import threading
import time

import yt_dlp

URL_TTL = 3 * 3600
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_cache = {}                            # video id -> (expires_at, url)
_lock = threading.Lock()


def _thumb(entry, vid, big):
    """16:9 cover. The search result lists a 360px and a 720px image; fall back to YouTube's fixed-name thumbnail."""
    thumbs = [t for t in entry.get("thumbnails") or [] if t.get("url")]
    if thumbs:
        return (thumbs[-1] if big else thumbs[0])["url"]
    return f"https://i.ytimg.com/vi/{vid}/{'hq720' if big else 'mqdefault'}.jpg"


def search(query, kind="songs", limit=20):
    opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit + 5}:{query}", download=False)
    out = []
    for e in info.get("entries") or []:
        vid = str(e.get("id") or "")
        if not VIDEO_ID.match(vid) or not e.get("title"):
            continue
        out.append({
            "kind": "yt", "id": vid, "title": e["title"], "artist": e.get("channel") or e.get("uploader") or "",
            "duration": int(e["duration"]) if e.get("duration") else None,
            "thumb": _thumb(e, vid, False), "art": _thumb(e, vid, True),
        })
        if len(out) >= limit:
            break
    return out


def resolve(video_id):
    if not VIDEO_ID.match(str(video_id)):
        raise ValueError("not a YouTube video id")
    now = time.time()
    with _lock:
        hit = _cache.get(video_id)
        if hit and hit[0] > now:
            return hit[1]
        for k in [k for k, v in _cache.items() if v[0] <= now]:                      # evict expired URLs
            _cache.pop(k, None)
    opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True, "skip_download": True,
            "js_runtimes": {"deno": {}, "quickjs": {}, "node": {}}}   # first supported one is used (node must be >= 22)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    with _lock:
        _cache[video_id] = (time.time() + URL_TTL, info["url"])
    return info["url"]
