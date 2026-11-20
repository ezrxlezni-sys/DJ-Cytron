"""YouTube Music search (ytmusicapi) and audio URL resolution (yt-dlp)."""
import os
import re
import threading
import time

import yt_dlp
from ytmusicapi import YTMusic

URL_TTL = 3 * 3600
_client = None
_cache = {}                  # video_id -> (expires_at, url)
_lock = threading.Lock()


def _yt():
    global _client
    with _lock:
        if _client is None:
            _client = YTMusic()          # unauthenticated: search only
        return _client


_SIZE = re.compile(r"=w\d+-h\d+")


def hires(url, size=544):
    """YouTube Music only lists ~120px covers, but Google's image host serves any size on request."""
    if url and "googleusercontent.com" in url or url and "ggpht.com" in url:
        return _SIZE.sub(f"=w{size}-h{size}", url, count=1)
    return url


def search(query, kind="songs", limit=20):
    out = []
    for r in _yt().search(query, filter=kind, limit=limit)[:limit]:
        if not r.get("videoId"):
            continue
        thumbs = r.get("thumbnails") or []
        out.append({
            "kind": "ytm", "id": r["videoId"], "title": r.get("title"),
            "artist": ", ".join(a["name"] for a in r.get("artists") or []),
            "duration": r.get("duration_seconds"), "explicit": bool(r.get("isExplicit")),
            "thumb": thumbs[-1]["url"] if thumbs else None,                 # small: list rows
            "art": hires(thumbs[-1]["url"]) if thumbs else None,            # large: now-playing panel
        })
    return out


def resolve(video_id):
    now = time.time()
    hit = _cache.get(video_id)
    if hit and hit[0] > now:
        return hit[1]
    for k in [k for k, v in list(_cache.items()) if v[0] <= now]:      # evict expired URLs
        _cache.pop(k, None)
    opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True, "skip_download": True,
            "js_runtimes": {"deno": {}, "quickjs": {}, "node": {}}}   # first supported one is used (node must be >= 22)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://music.youtube.com/watch?v={video_id}", download=False)
    _cache[video_id] = (time.time() + URL_TTL, info["url"])
    return info["url"]


# ---- playlists/albums (unauthenticated) ----
def _thumb(r):
    t = r.get("thumbnails") or []
    return t[-1]["url"] if t else None


def _artists(r):
    return ", ".join(a["name"] for a in r.get("artists") or [] if a.get("name"))


def _song(r, fallback_thumb=None):
    th = _thumb(r) or fallback_thumb
    return {"kind": "ytm", "id": r["videoId"], "title": r.get("title"), "artist": _artists(r),
            "duration": r.get("duration_seconds"), "explicit": bool(r.get("isExplicit")), "thumb": th, "art": hires(th)}


def tracks(kind, cid, limit=100):
    """Playable tracks of a playlist or album."""
    y = _yt()
    data = y.get_playlist(cid, limit=limit) if kind == "playlist" else y.get_album(cid)
    cover = _thumb(data)
    return [_song(t, cover) for t in data.get("tracks") or [] if t.get("videoId")]


# ---- suggestions: YouTube Music "radio" for a seed track (unauthenticated) ----
SUGGEST_TTL = 600
_suggest = {}                # tuple(seeds) -> (expires_at, tracks)


def _seconds(length):
    try:
        secs = 0
        for part in str(length).split(":"):
            secs = secs * 60 + int(part)
        return secs
    except ValueError:
        return None


def suggest(seeds, per_seed=12):
    """Related tracks for the given seed video ids, interleaved and de-duplicated. Cached for 10 minutes."""
    key = tuple(seeds)
    hit = _suggest.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    lists = []
    for vid in seeds:
        try:
            tr = _yt().get_watch_playlist(videoId=vid, limit=per_seed + 1).get("tracks") or []
        except Exception:
            continue
        lists.append([t for t in tr if t.get("videoId") and t["videoId"] != vid])
    out, seen = [], set(seeds)
    for i in range(max((len(x) for x in lists), default=0)):          # round-robin across the seeds
        for lst in lists:
            if i < len(lst) and lst[i]["videoId"] not in seen:
                t = lst[i]
                seen.add(t["videoId"])
                th = (t.get("thumbnail") or t.get("thumbnails") or [{}])[-1].get("url")
                out.append({"kind": "ytm", "id": t["videoId"], "title": t.get("title"), "artist": _artists(t),
                            "duration": _seconds(t.get("length")), "explicit": bool(t.get("isExplicit")), "thumb": th, "art": hires(th)})
    if not out:
        raise RuntimeError("no suggestions available")
    _suggest[key] = (time.time() + SUGGEST_TTL, out)
    return out


# ---- trending: the country's YouTube Music chart (first chart playlist, e.g. "Trending 20 Malaysia") ----
TRENDING_TTL = 3600
_trending = (0, None)


def trending(country=None):
    global _trending
    if _trending[1] is not None and _trending[0] > time.time():
        return _trending[1]
    country = country or os.environ.get("PIPLAYER_CHARTS_COUNTRY", "MY")
    charts = _yt().get_charts(country=country).get("videos") or []
    pid = next((c["playlistId"] for c in charts if c.get("playlistId")), None)
    out = tracks("playlist", pid, limit=20) if pid else []
    if not out:
        raise RuntimeError("no trending chart available")
    _trending = (time.time() + TRENDING_TTL, out)
    return out
