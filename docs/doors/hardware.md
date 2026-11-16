# Door sensor hardware

The Pi can watch two restroom doors with magnetic **reed switches**. This page covers wiring, pins, how a reading is
interpreted, and the sensor watchdog. What the sensors *do* with the music is in [Door autoplay](autoplay.md) and
[Door announcements](announcements.md).

The sensors give you:

1. **Occupancy**: live Available / Occupied cards on the Restrooms tab.
2. **Autoplay** (optional): music plays while someone is inside and pauses when nobody is.
3. **Announcements** (optional): a spoken welcome and reminder at the doors.
4. **A sensor watchdog**: a "check sensor" warning if a switch seems stuck or unplugged.

Code: [piplayer/bathrooms.py](../../piplayer/bathrooms.py).

## Parts

| Part | Quantity | Notes |
|---|---|---|
| Magnetic reed switch + magnet (door contact) | 2 | Normally-open type: closed when the magnet is next to it. |
| Wire | | Two conductors per door. |
| Pi with a 40-pin header | 1 | Any model with GPIO. |

No resistor is needed: the app turns on the Pi's internal pull-up.

## Wiring

One reed switch per door, each between a GPIO pin and a ground pin. A magnet on the door keeps the switch closed
while the door is shut.

```
 Pi GPIO pin ──── reed switch ──── GND         (one switch per door)
                       ▲
                  magnet on the door
```

| Room | Default BCM pin | Physical header pin | Nearby ground |
|---|---|---|---|
| male | 12 | 32 | 34 |
| female | 13 | 33 | 34 |

Pins are **BCM** (GPIO) numbers, 2 to 27, and must differ. Change them in Settings; no restart is needed. A pin can
also be set at start-up with `PIPLAYER_BATHROOM_PINS` ([Configuration](../reference/configuration.md#how-pins-are-chosen)).

Mount the magnet so the switch is **closed only when the door is shut**. Keep the cable run short and away from
mains wiring; debounce is 50 ms, which handles normal contact bounce.

## How a reading is interpreted

| Door | Magnet | Switch | Pin | Shown as |
|---|---|---|---|---|
| closed | next to switch | closed | low | **Occupied** |
| open | away | open | high | **Available** |
| sensor not configured / not started | | | | No sensor (grey) |

### The limit of a plain reed switch

A disconnected wire reads exactly like an open door, because the pull-up makes an unconnected pin read "high". Until
a sensor is wired, clear both pin fields in Settings and press Save; the rooms then show **No sensor** instead of
**Available**.

For reliable fault detection you would need changeover (SPDT) reed sensors using two pins per door, where both pins
reading high means "disconnected". That is not implemented. The watchdog below is the partial answer.

## Testing the wiring

1. Open the Restrooms tab on a phone.
2. Bring the magnet to the switch (or touch the pin to GND with a jumper): the card turns **Occupied**.
3. Take it away: the card turns **Available**.
4. If it does not change, see [Troubleshooting](#troubleshooting).

## Software requirements

| Need | Why |
|---|---|
| `python3-gpiozero`, `python3-lgpio` (apt) | GPIO access. The virtual environment must see system packages (`--system-site-packages`). |
| `LG_WD=/tmp` in the service unit | `lgpio` creates a notification pipe (`.lgd-nfy*`) in its working directory; this keeps it out of the project. |
| Pins free | Another program using a pin gives `GPIOPinInUse`. |

If GPIO cannot start, the app keeps running: the sensor badge shows `Sensor error` with the reason and the rooms show
No sensor. Music is unaffected.

## Sensor watchdog

A reed switch cannot report that it has failed, so the app watches for silence. A room is flagged `stale` when it has
a configured sensor and a reading but **no change for 4 hours of opening time**. The room card then shows
"No change for 5 h 20 min. Check the sensor."

- Only time inside the active hours counts, and only on the same day, so a quiet night never triggers it.
- It is checked every 20 seconds and pushed to open pages automatically.
- It clears the next time the door changes state.
- Overnight opening ranges (from later than until) are not watched.
- A bathroom that was genuinely not used for 4 hours also triggers it. That is a limit of the method.

## Settings that affect the sensors

| Setting | Effect |
|---|---|
| Male / Female door pin | BCM pin of each switch. Saving restarts the sensors immediately and forgets old readings. Leave both empty to switch them off. |
| Active hours | Used by the watchdog (and by autoplay and announcements). |

All door settings are listed in [Restrooms and Settings](../guide/restrooms-and-settings.md#settings) and stored in
[`data/settings.json`](../reference/configuration.md#settingsjson). The API is
[`POST /api/doors`](../reference/api.md#post-apidoors).

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Rooms always show **Available** | Nothing is wired (see the limit above), or the magnet is too far from the switch. Check the switch with a jumper from the pin to GND: the room should turn **Occupied**. |
| Rooms always show **Occupied** | Switch wired to the wrong pin, or magnet fixed in place. |
| Rooms show **No sensor** | No pin is set for that room, or the sensors failed to start (look at the badge in Settings). |
| Badge says **Sensor error** | The reason is shown under the badge. `ModuleNotFoundError: gpiozero`: install `python3-gpiozero python3-lgpio` and make sure the virtual environment can see system packages. `GPIOPinInUse`: another program uses the pin. |
| Reading flickers | A loose wire or a magnet at the edge of the switch's range. Re-seat the wire, move the magnet closer. |
| A `.lgd-nfy0` file appears in the project | The service was started without `LG_WD=/tmp`. Use the unit in `deploy/`. It is safe to delete while the service is stopped. |
| **Check sensor** warning | No change for 4 opening hours. Check the wiring; it also appears if the room genuinely was not used. It clears at the next change. |
| Changes only appear after a refresh | The live event stream is failing. Open `/api/events` and check `journalctl -u piplayer -n 50`. |
