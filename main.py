import subprocess
import time
import threading
from flask import Flask, render_template, request, redirect, jsonify
import datetime
import pytz
import os
import json
import socket
import psutil  # New import

# ========== Radio Stream Config ==========
RADIO_STREAMS = {
    "Hitz FM": "https://stream-eu-a.rcs.revma.com/488kt4sbv4uvv/68_1txzsglqw5l3t02/playlist.m3u8",
    "MIX FM": "https://stream-eu-a.rcs.revma.com/v5pq3htbv4uvv/40_wqselj3z5ieg02/playlist.m3u8",
    "MY FM": "https://stream-eu-a.rcs.revma.com/hc3unrtbv4uvv/56_1t996oveblvvv02/playlist.m3u8"
}

CONFIG_FILE = "config.json"
current_stream = "Hitz FM"
radio_process = None
is_playing = False
user_stopped = False

# ========== Config Persistence ==========
def save_config(volume):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"volume": volume}, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"volume": 80}

# ========== Playback Functions ==========
def stop_radio():
    global is_playing, radio_process, user_stopped
    print("⏹ Stopping radio.")

    if radio_process and radio_process.poll() is None:
        try:
            radio_process.terminate()
            radio_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            radio_process.kill()

    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] and 'vlc' in proc.info['name'].lower():
                proc.kill()
            elif proc.info['cmdline'] and 'cvlc' in proc.info['cmdline'][0]:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
            continue

    radio_process = None
    is_playing = False
    user_stopped = True

def play_radio():
    global is_playing, radio_process, user_stopped
    stop_radio()

    print(f"🎵 Playing {current_stream}")
    try:
        with open("/home/pi/radio_project/radio.log", "a") as log:
            log.write(f"[{datetime.datetime.now()}] Starting VLC for: {current_stream}\n")
            log.flush()
            radio_process = subprocess.Popen(
                ["cvlc", "--intf", "dummy", "--no-video", RADIO_STREAMS[current_stream]],
                stdout=log,
                stderr=log
            )
        is_playing = True
        user_stopped = False
    except Exception as e:
        with open("/home/pi/radio_project/radio.log", "a") as log:
            log.write(f"[ERROR] Failed to start radio: {str(e)}\n")

# ========== Flask Web Interface ==========
app = Flask(__name__, template_folder="web/templates")

@app.route('/')
def index():
    return render_template("index.html", streams=RADIO_STREAMS, current=current_stream, status=is_playing)

@app.route('/play', methods=['POST'])
def play():
    global current_stream
    stream_name = request.form.get("station")
    if stream_name in RADIO_STREAMS:
        current_stream = stream_name
        play_radio()
    return redirect('/')

@app.route('/stop')
def stop():
    stop_radio()
    return redirect('/')

@app.route('/status')
def status_check():
    return jsonify({
        "status": is_playing,
        "current": current_stream
    })

@app.route('/ping')
def ping():
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '1', '8.8.8.8'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        )
        output = result.stdout
        if "time=" in output:
            ms = output.split("time=")[1].split(" ")[0]
            return jsonify({"ping": float(ms)})
        else:
            return jsonify({"ping": None})
    except Exception as e:
        print(f"Ping error: {e}")
        return jsonify({"ping": None})

# ========== Helper: Wait for Network ==========
def wait_for_network(max_wait=30):
    for i in range(max_wait):
        try:
            socket.gethostbyname("google.com")
            print("🌐 Network is ready.")
            return True
        except socket.gaierror:
            print(f"⏳ Waiting for network... {i+1}/{max_wait}")
            time.sleep(1)
    print("❌ Network not ready after waiting.")
    return False

# ========== Run App on Boot ==========
if __name__ == '__main__':
    print("🚀 Smart Radio started")

    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False)).start()

    if wait_for_network():
        print("🔊 Attempting to auto-play radio...")
        play_radio()
    else:
        print("⚠️ Skipping auto-play due to no network.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🔻 Exiting...")
        stop_radio()
os._exit(0)
