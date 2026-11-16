"""WSGI entry point (gunicorn): `gunicorn piplayer.wsgi:app`. Needs a single worker: the player is in-process."""
from .app import create_app

app = create_app()
