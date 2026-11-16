# FAQ

## Using it

**Do I need to install anything on my phone?**
No. Open `http://cytrondj.local` in any browser on the same network. You can add it to your home screen if you like.

**Does the music play on my phone?**
No, it plays on the speakers connected to the Pi. To hear it on your own device, use
[Listen on this device](using-the-player.md#listen-on-this-device).

**Can two people use it at once?**
Yes. Everyone controls the same player and sees the same screen live. The last command wins.

**Is there a login or a user account?**
No. Anyone on the network can use it. Run it only on a trusted network ([Security](../admin/security.md)).

**Why did my music stop when I closed the page?**
It did not: the Pi plays it. If it stopped, the queue ended, a song failed, or a door sensor paused it (autoplay).

**What is the difference between YouTube Music and YouTube?**
YouTube Music is songs with artists and covers. YouTube is any video, live stream or podcast, played as audio only.
SoundCloud has remixes, DJ sets and independent artists.

**Why can I not find a famous song on SoundCloud?**
Major-label tracks are only 30-second previews there, so they are hidden on purpose. Search on YouTube Music instead.

**Why does the volume start at 70 every time?**
The service sets the Pi's output volume to 70 when it starts. Change it with the slider; it stays until the next restart.

**Does the volume slider change the Pi's real volume?**
Yes. It is the Pi's system output volume, so it matches the volume the administrator sets with `wpctl`.

**Can I add my own radio station?**
Yes: Radio > ⋮ > Add station, with a direct stream link (`http(s)://...mp3`, `.aac`, `.m3u8`). Station pages and
playlists on a website are not streams.

**Where did "Recently played" go?**
The shelves were removed from the Music pages. The history is still recorded and still feeds Suggested for you.

## Door sensors

**Why does a restroom show Available when nothing is wired?**
A plain reed switch cannot tell "door open" from "wire disconnected". Clear both pin fields in Settings and press
Save until the sensors are wired; the rooms then show No sensor.
See [Door sensor hardware](../doors/hardware.md#the-limit-of-a-plain-reed-switch).

**Why did the music pause when the door opened?**
Autoplay is on and nobody is inside. Turn **Play the queue while in use** off in Settings to stop that.

**Why did the music not start when someone went in?**
Autoplay is off, it is outside the active hours, or you changed playback by hand since the last door change.
See [Door autoplay](../doors/autoplay.md#why-didnt-it-play-or-pause).

**Why is there no spoken message?**
The switch is off, it is outside the active hours, the message is empty, no voice is installed, or the Pi has just
started (nothing is said at start-up). See [Door announcements](../doors/announcements.md#troubleshooting).

**What does Check sensor mean?**
The door has not changed for 4 hours of opening time. Check the wiring and magnet.

## Running it

**How do I back it up?**
It already backs up `data/` every night. See [Maintenance](../admin/maintenance.md#backups).

**YouTube songs stopped working. What now?**
Update yt-dlp: `deploy/update-deps.sh && sudo systemctl restart piplayer`. It also updates itself every Sunday.
See [Troubleshooting](../admin/troubleshooting.md#music-and-radio).

**Can I run it somewhere other than `/home/pi/Documents/pi-player`?**
Yes. Edit the paths and user in `deploy/piplayer.service` first. See [Deployment](../admin/deployment.md#changing-the-install-location-or-user).

**Can I use it over the internet?**
Do not. There is no login. See [Security](../admin/security.md#do-not-expose-it-to-the-internet).

**Does it send data anywhere?**
It contacts YouTube, YouTube Music and SoundCloud to search and stream, and the radio stations you play. Spoken
messages are generated on the Pi; nothing about them leaves it. There is no analytics or telemetry.
