"""Small persisted settings (volume, door config, saved queue), with debounced atomic writes."""
import json
import os
import threading
from pathlib import Path


class Settings:
    def __init__(self, path, defaults):
        self.path = Path(path)
        self.data = dict(defaults)
        try:
            saved = json.loads(self.path.read_text())
            if isinstance(saved, dict):
                self.data.update(saved)
        except (OSError, ValueError):
            pass
        self._lock = threading.Lock()
        self._timer = None

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.update({key: value})

    def update(self, values):
        with self._lock:
            self.data.update(values)
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(1.0, self.flush)   # avoid SD-card writes on slider drags
            self._timer.daemon = True
            self._timer.start()

    def flush(self):
        """Write now (atomically: a power cut leaves the old file, never a half-written one)."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.data))
                os.replace(tmp, self.path)
            except OSError:
                pass                                          # read-only disk etc.: keep running
