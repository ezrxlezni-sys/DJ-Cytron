# Glossary

| Term | Meaning |
|---|---|
| **Active hours** | The From / Until times in Settings. Autoplay, announcements and the sensor watchdog only act inside them. |
| **Autoplay** | The setting that lets the door sensors play and pause the music. See [Door autoplay](../doors/autoplay.md). |
| **BCM** | Broadcom GPIO numbering (GPIO12 is "BCM 12"). Not the position on the 40-pin header. |
| **Duck / ducking** | Briefly lowering the music while a spoken message plays over it. |
| **Event stream** | The live connection (`GET /api/events`, server-sent events) that pushes the full state to every open browser. |
| **espeak-ng** | A small robotic offline text-to-speech engine. The fallback voice. |
| **Fade in / fade out** | A smooth volume rise when a door starts the music / a smooth fall before it pauses. |
| **GPIO** | General-purpose input/output pins on the Pi. The reed switches connect to them. |
| **gunicorn** | The production web server. Runs one worker with 32 threads. |
| **Held** | A live radio stream that is connected but silenced by autoplay. The page shows it as Paused. |
| **ICY title** | The "now playing" text some radio stations send. Shown in the player. |
| **IPC** | Inter-process communication: the unix socket the app uses to control mpv. |
| **Kind** | The source of a queue item: `radio`, `ytm` (YouTube Music), `yt` (YouTube) or `sc` (SoundCloud). |
| **Listen on this device** | Streams what the Pi is playing to your browser as MP3. Up to 4 listeners. |
| **mpv** | The audio player the app drives. One long-lived process, restarted if it dies. |
| **PipeWire** | The audio system on Raspberry Pi OS. `wpctl`, `pw-play` and `pw-record` are its tools. |
| **Piper** | The offline neural text-to-speech engine used for the natural voice. |
| **Prefetch** | Resolving the next track's stream URL while the current one plays, so there is no gap. |
| **Queue item** | A track or station: `{kind, id, title, ...}`. The same shape is used in the queue, playlists, search and the API. |
| **Reed switch** | A magnetic switch that is closed when a magnet is near. Used as a door contact. |
| **Resolve** | Turning a YouTube / YouTube Music / SoundCloud item into a direct audio URL with yt-dlp. |
| **Request guard** | The Host and Origin checks on every API request. Not authentication. See [Security](../admin/security.md). |
| **SSE** | Server-sent events. The technology behind the event stream. |
| **Silence (radio)** | Muting a live stream instead of pausing it, so the server does not drop it. |
| **Stale** | A room flag set when its sensor has not changed for 4 hours of opening time ("Check sensor"). |
| **State / snapshot** | The one JSON object describing player, queue, rooms and door settings. |
| **systemd** | The Linux service manager that starts the app on boot and runs the backup and update timers. |
| **Watchdog** | The check that flags a room whose sensor never changes. |
| **yt-dlp** | The tool that searches YouTube and SoundCloud and finds the audio stream. Must be kept up to date. |
