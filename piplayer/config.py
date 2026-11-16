"""Runtime configuration, read from PIPLAYER_* environment variables."""
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BATHROOM_PINS = "male=12,female=13"      # BCM pins; override here, in the env, or in the UI


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    data_dir: Path
    mpv_cmd: tuple          # command prefix used to launch mpv
    socket_path: str
    bathroom_pins: tuple = ()   # (("male", pin), ("female", pin)); empty = no sensors

    @classmethod
    def from_env(cls, env=os.environ):
        raw = env.get("PIPLAYER_BATHROOM_PINS")
        if raw is None:
            raw = DEFAULT_BATHROOM_PINS
        rooms = tuple((n.strip(), int(p)) for n, p in (kv.split("=") for kv in raw.split(",") if kv.strip()))
        return cls(
            host=env.get("PIPLAYER_HOST", "0.0.0.0"),
            port=int(env.get("PIPLAYER_PORT", 8088)),
            data_dir=Path(env.get("PIPLAYER_DATA", ROOT / "data")),
            mpv_cmd=tuple(shlex.split(env.get("PIPLAYER_MPV", "mpv"))),
            socket_path=env.get("PIPLAYER_SOCKET", "/tmp/piplayer-mpv.sock"),
            bathroom_pins=rooms,
        )
