from flask import Flask, render_template, request, redirect
import subprocess

app = Flask(__name__, template_folder="templates")
app.debug = True

# Stream URLs (you can add more!)
RADIO_STREAMS = {
    "Hitz FM": "https://stream-eu-a.rcs.revma.com/488kt4sbv4uvv/68_1txzsglqw5l3t02/playlist.m3u8",
    "MIX FM": "https://stream-eu-a.rcs.revma.com/v5pq3htbv4uvv/40_wqselj3z5ieg02/playlist.m3u8",
    "MY FM": "https://astro1.rastream.com/sinar"
}
RADIO_IMAGES = {
    "HitzFM": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Hitz_%282018%29.svg/1920px-Hitz_%282018%29.svg.png",
    "MIX FM": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Mix_%282018%29.svg/1920px-Mix_%282018%29.svg.png",
    "MY FM": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/MY_%282018%29.svg/1920px-MY_%282018%29.svg.png"
}
current_stream = None
radio_process = None

def start_radio(stream_url):
    global radio_process
    stop_radio()
    radio_process = subprocess.Popen(["cvlc", "--intf", "dummy", stream_url],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def stop_radio():
    global radio_process
    if radio_process:
        radio_process.terminate()
        radio_process = None

@app.route("/", methods=["GET", "POST"])
def index():
    global current_stream

    if request.method == "POST":
        action = request.form.get("station") or request.form.get("action")
        if action == "stop":
            stop_radio()
            current_stream = None
        else:
            stream_url = RADIO_STREAMS.get(action)
            if stream_url:
                start_radio(stream_url)
                current_stream = action
        return redirect("/")  # Refresh to reflect new stream

    # Prepare logs and current stream for display
    log_html = "<ul>" + "".join(f"<li>{log}</li>" for log in motion_logs) + "</ul>" if motion_logs else "<p>No motion detected yet.</p>"

    # Pass the station name or fallback
    return render_template_string(
        open("templates/index.html").read(),
        current=current_stream if current_stream else "No stream is currently playing.",
        logs=log_html
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
