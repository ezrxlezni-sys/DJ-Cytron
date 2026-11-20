"""Application factory: wires config, services and routes together."""
import atexit
import json
import threading
from pathlib import Path

from flask import Flask, send_from_directory

from . import api, soundcloud, youtube, ytm
from .bathrooms import Bathrooms
from .config import Config
from .history import HistoryStore
from .player import DEFAULT_VOLUME, Player
from .playlists import PlaylistStore, clean_items
from .settings import Settings
from .stations import StationStore

STATIC = Path(__file__).parent / "static"


class Services:
    """Holds the long-lived objects and the change-notification used by SSE."""

    def __init__(self, cfg, resolver=None, search=None, suggest=None, trending=None, sc_search=None, sc_resolver=None, yt_search=None, yt_resolver=None):
        self.cfg = cfg
        self.stations = StationStore(cfg.data_dir / "stations.json")
        self.playlists = PlaylistStore(cfg.data_dir / "playlists.json")
        self.history = HistoryStore(cfg.data_dir / "history.json")
        self.settings = Settings(cfg.data_dir / "settings.json", {"bathrooms": {}})
        self.search = search or ytm.search
        self.trending = trending or (lambda: ytm.trending())
        self.suggest = suggest or (lambda seeds: ytm.suggest(seeds))
        self._resolve_ytm = resolver or ytm.resolve
        self.search_sc = sc_search or soundcloud.search
        self._resolve_sc = sc_resolver or soundcloud.resolve
        self.search_yt = yt_search or youtube.search
        self._resolve_yt = yt_resolver or youtube.resolve
        self.queue_state = Settings(cfg.data_dir / "queue.json", {})     # the queue survives restarts
        self._queue_sig = None
        self.changed = threading.Condition()
        self.version = 0
        self.bathrooms = Bathrooms(self)
        self.player = Player(self._resolve, cfg.mpv_cmd, cfg.socket_path,
                             DEFAULT_VOLUME, on_change=self.notify, on_play=self.history.record)
        saved_eq = self.settings.get("eq")
        if saved_eq:
            self.player.set_eq(gains=saved_eq)            # the equalizer setting survives restarts
        q = self.queue_state.data
        self.player.restore(clean_items(q.get("queue")), q.get("index", -1), q.get("repeat", "off"), q.get("shuffle", False))

    def _resolve(self, item):
        if item["kind"] == "radio":
            return item["url"]
        if item["kind"] == "sc":
            return self._resolve_sc(item["url"])
        if item["kind"] == "yt":
            return self._resolve_yt(item["id"])
        return self._resolve_ytm(item["id"])

    def notify(self):
        with self.changed:
            self.version += 1
            self.changed.notify_all()
        self._persist_queue()

    def _persist_queue(self):
        player = getattr(self, "player", None)          # notify() also fires while the player is still being built
        if player is None:
            return
        snap = player.persisted()
        sig = json.dumps(snap, sort_keys=True)
        if sig != self._queue_sig:
            self._queue_sig = sig
            self.queue_state.update(snap)


def create_app(cfg=None, resolver=None, search=None, suggest=None, trending=None, sc_search=None, sc_resolver=None,
               yt_search=None, yt_resolver=None):
    cfg = cfg or Config.from_env()
    app = Flask(__name__, static_folder=None)
    svc = Services(cfg, resolver, search, suggest, trending, sc_search, sc_resolver, yt_search, yt_resolver)
    app.extensions["piplayer"] = svc
    atexit.register(svc.player.close)
    atexit.register(svc.settings.flush)
    atexit.register(svc.queue_state.flush)
    app.register_blueprint(api.bp)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(STATIC, name)

    svc.bathrooms.run()
    return app
