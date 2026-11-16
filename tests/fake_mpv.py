"""Minimal stand-in for mpv's JSON IPC, used by the tests (mpv itself not required)."""
import json
import socket
import sys

path = next(a.split("=", 1)[1] for a in sys.argv if a.startswith("--input-ipc-server="))
srv = socket.socket(socket.AF_UNIX)
srv.bind(path)
srv.listen(1)
conn, _ = srv.accept()
log = open(path + ".log", "w")


def emit(**kw):
    conn.sendall((json.dumps(kw) + "\n").encode())


buf = b""
while True:
    data = conn.recv(4096)
    if not data:
        break
    buf += data
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        cmd = json.loads(line)["command"]
        log.write(json.dumps(cmd) + "\n")
        log.flush()
        if cmd[0] == "loadfile" and "unreachable" in cmd[1]:
            emit(event="end-file", reason="error")        # stream cannot be reached
        elif cmd[0] == "loadfile":
            emit(event="property-change", name="idle-active", data=False)
            emit(event="property-change", name="core-idle", data=False)
            emit(event="property-change", name="duration", data=200.0)
            emit(event="file-loaded")
        elif cmd[0] == "stop":
            emit(event="property-change", name="idle-active", data=True)
        elif cmd[0] == "set_property" and cmd[1] == "mute":
            pass
        elif cmd[0] == "set_property" and cmd[1] == "pause":
            emit(event="property-change", name="pause", data=cmd[2])
        elif cmd[0] == "set_property" and cmd[1] == "volume":
            emit(event="property-change", name="volume", data=cmd[2])
        elif cmd[0] == "quit":
            break
