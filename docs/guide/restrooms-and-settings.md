# Restrooms and Settings

Two tabs belong to the door sensors: **Restrooms** (what is happening now) and **Settings** (how it behaves). The
wiring and the exact rules are in the [doors section](../doors/hardware.md); this page is the user's view.

## Restrooms

Two cards, **Male** and **Female**, show the state of each door live, and since when.

### What the cards mean

| Card shows | Meaning |
|---|---|
| **Occupied** | The door is closed: someone is inside. |
| **Available** | The door is open. |
| **No sensor** (grey) | That room has no working sensor: no pin is set, the sensors are switched off, or they failed to start. |
| **Check sensor** warning | The door has not changed for 4 hours of opening time, so the sensor may be unplugged or stuck. It clears the next time the door changes. A restroom that was genuinely unused for that long also triggers it. |

The cards update by themselves; there is no need to refresh.

## Settings

The Settings tab has one form for the door sensors. The badge at the top right shows `N of 2 sensors active`,
`No sensors` or `Sensor error` (the reason is written under it). Saving applies immediately; no restart is needed.

| Section | Control | What it does |
|---|---|---|
| Sensors | Male door / Female door (GPIO pin) | The BCM pin each reed switch is wired to (2 to 27, different for each room). Leave both empty to switch the sensors off. |
| Autoplay | **Play the queue while in use** | When on, the music plays while someone is inside during the active hours, and pauses when both doors are open. Off by default. |
| | **Active hours** (from, until) | Opening hours. Used by autoplay, the announcements and the sensor watchdog. |
| | **Fade in** | When a door starts the music it rises gradually to your volume: Off, or 3 to 60 seconds (default 5). |
| | **Fade out** | When the last door opens the music fades down before it pauses: Off, or 1 to 15 seconds (default 3). |
| Announcements | **Speak at the doors** | Turns the spoken messages on or off (on by default). |
| | **Voice** | *Automatic* (Piper if installed, otherwise espeak-ng) or any installed voice. |
| | **Music during a message** | How loud the music stays while a message plays over it: No dip, 70 %, 50 %, 30 % (default), 15 %, Silent. |
| | **Music comes back** | How fast the music returns to full volume after a message: Instantly, 1, 2 (default), 4 or 8 seconds. |
| | **Welcome / Reminder** | The two messages (up to 160 characters; empty = say nothing). The ▶ button plays the saved message on the Pi's speakers. |
| Data | **Clear history** | Forgets what was played on this Pi (used for suggestions) and your recent searches in this browser. |

If no speech engine is installed, Settings shows a notice. Ask the administrator to follow
[Door announcements](../doors/announcements.md#installing-a-voice).

## What happens at a door

| When | What you will notice |
|---|---|
| A door closes (someone goes in) | The welcome message is spoken. If autoplay is on, the music then starts or resumes, rising gently to your volume. |
| A door opens (someone comes out) | The reminder is spoken (over the music, which dips while it talks). If that was the last occupied room and autoplay is on, the music first fades out and pauses. |
| Closing time passes | Music fades out and pauses; a radio stream is stopped, so it does not stream all night. |
| You press Play or Pause yourself | It is respected until the next door change. |

Messages are only spoken during the active hours, and never right after the Pi starts. Details and every edge case
are in [Door autoplay](../doors/autoplay.md) and [Door announcements](../doors/announcements.md).

> **Is a radio station "paused" or "silent"?** With autoplay, a live station is *silenced* rather than really paused,
> because a paused internet stream is dropped by the server after about a minute. The page shows it as Paused, and
> it comes back instantly, live, when someone returns.
