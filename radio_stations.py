from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import subprocess

app = Flask(__name__)
socketio = SocketIO(app)

# VLC Process Holder
radio_process = None
current_station = None

# Default Radio Stations
STATIONS = {
    "HitzFM": "https://stream-eu-a.rcs.revma.com/488kt4sbv4uvv/68_ltxzsglw513t82/playlist.m3u8",
    "EraFM": "https://n13a-eu.rcs.revma.com/crec9cmbv4uwv/19_srs6orjgrti602/playlist.m3u8",
    "FlyFM": "https://stream-eu-a.rcs.revma.com/q17aka3mtd3vv/5_1zmx9hh4r5s202/playlist.m3u8",
    "MyFM": "https://n3curtby4uwv/56_1t99soveblvwv02/playlist.m3u8"
}

def play_radio(url):
    global radio_process, current_station
    stop_radio()
    print(f"🎵 Playing {url}")
    radio_process = subprocess.Popen(["cvlc", "--no-video", url],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    current_station = url
    socketio.emit("update_station", {"station": url})

def stop_radio():
    global radio_process
    if radio_process:
        print("⏹ Stopping radio...")
        radio_process.terminate()
        radio_process = None

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/change_station', methods=['POST'])
def change_station():
    data = request.get_json()
    station_url = data.get("url")
    if station_url:
        play_radio(station_url)
        return jsonify({"status": "success", "message": "Station changed"})
    return jsonify({"status": "error", "message": "Invalid URL"})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
