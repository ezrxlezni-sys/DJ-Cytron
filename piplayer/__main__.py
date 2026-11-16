"""Run with:  python -m piplayer"""
from .app import create_app
from .config import Config

cfg = Config.from_env()
create_app(cfg).run(host=cfg.host, port=cfg.port, threaded=True, debug=False)
