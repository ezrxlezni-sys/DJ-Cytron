# Cytron DJ documentation

Cytron DJ turns a Raspberry Pi into a shared network music player with restroom door sensors. This is the map of
the documentation. Pick the path that matches what you are doing.

## Start here

| I want to... | Read |
|---|---|
| Use the player from my phone or laptop | [Using the player](guide/using-the-player.md) |
| Understand the restroom cards and the door settings | [Restrooms and Settings](guide/restrooms-and-settings.md) |
| Find a quick answer | [FAQ](guide/faq.md) |
| Set up a new Pi | [Installation](admin/installation.md), then [Deployment](admin/deployment.md) |
| Wire the door sensors | [Door sensor hardware](doors/hardware.md) |
| Fix something that is broken | [Troubleshooting](admin/troubleshooting.md) |
| Change a setting or an environment variable | [Configuration](reference/configuration.md) |
| Understand how it works inside | [Architecture overview](architecture/overview.md) |
| Change the code | [Development](contributing/development.md) |

## By role

**Everyone who uses it**
1. [Using the player](guide/using-the-player.md): Radio, Music, Queue, Playlists, the player controls.
2. [Restrooms and Settings](guide/restrooms-and-settings.md): what the cards mean, what each setting does.
3. [FAQ](guide/faq.md): short answers to the usual questions.

**Whoever runs the Pi** (the administrator)
1. [Installation](admin/installation.md): packages, virtual environment, the speaking voice, first run.
2. [Deployment](admin/deployment.md): run on boot with systemd, audio output, power-button permissions.
3. [Maintenance](admin/maintenance.md): backups, restore, weekly updates, upgrading, resetting data.
4. [Security](admin/security.md): what is and is not protected, and how to run it safely.
5. [Troubleshooting](admin/troubleshooting.md): symptoms and fixes for the whole system.
6. [Configuration](reference/configuration.md) and [Data files](reference/data-files.md) when you need the details.

**Whoever wires and tunes the doors**
1. [Door sensor hardware](doors/hardware.md): reed switches, pins, the sensor watchdog.
2. [Door autoplay](doors/autoplay.md): the rule that plays and pauses the music, fade in and fade out.
3. [Door announcements](doors/announcements.md): the spoken welcome and reminder, voices, ducking.

**Developers**
1. [Architecture overview](architecture/overview.md), [Player and playback](architecture/player.md),
   [Front end](architecture/frontend.md) and [Design decisions](architecture/decisions.md).
2. [HTTP API](reference/api.md) and [Data files](reference/data-files.md).
3. [Development](contributing/development.md) and [Testing](contributing/testing.md).

## All documents

| Folder | Document | Contents |
|---|---|---|
| `guide/` | [using-the-player.md](guide/using-the-player.md) | Every tab and control |
| | [restrooms-and-settings.md](guide/restrooms-and-settings.md) | Occupancy cards and the Settings page |
| | [faq.md](guide/faq.md) | Frequently asked questions |
| `admin/` | [installation.md](admin/installation.md) | Prerequisites, install, voice download, first run |
| | [deployment.md](admin/deployment.md) | systemd service, audio, reboot and shutdown permissions |
| | [maintenance.md](admin/maintenance.md) | Backups, updates, upgrades, resets, logs |
| | [security.md](admin/security.md) | Threat model, built-in protections, hardening |
| | [troubleshooting.md](admin/troubleshooting.md) | Symptom to fix tables |
| `doors/` | [hardware.md](doors/hardware.md) | Wiring, pins, reading a switch, watchdog |
| | [autoplay.md](doors/autoplay.md) | Play and pause rules, fades |
| | [announcements.md](doors/announcements.md) | Speech, voices, ducking |
| `reference/` | [configuration.md](reference/configuration.md) | Environment variables, Settings keys, dependencies |
| | [data-files.md](reference/data-files.md) | Every file in `data/` and its format |
| | [api.md](reference/api.md) | Every HTTP endpoint and the state object |
| | [glossary.md](reference/glossary.md) | Terms used across the docs |
| `architecture/` | [overview.md](architecture/overview.md) | Process model, services, threads, file layout |
| | [player.md](architecture/player.md) | Queue, mpv, music sources, resilience |
| | [frontend.md](architecture/frontend.md) | The browser app |
| | [decisions.md](architecture/decisions.md) | Why it is built this way |
| `contributing/` | [development.md](contributing/development.md) | Setup, conventions, adding endpoints and settings |
| | [testing.md](contributing/testing.md) | The test suite and how it isolates the app |

See also the [changelog](../CHANGELOG.md) for what changed and when.

## Conventions used in these docs

- Commands assume the project lives in `/home/pi/Documents/pi-player` and the service user is `pi`. Change the paths if yours differ.
- The address `http://cytrondj.local` is the production address (port 80). A hand-started development copy listens on port 8088.
- **BCM** pin numbers are the GPIO numbers (such as GPIO12), not the physical header positions.
- Diagrams are [Mermaid](https://mermaid.js.org/). They render on GitHub and in the VS Code Markdown preview.
- A **doc is wrong if it disagrees with the code.** If you find one, fix the doc in the same change as the code. See [Development](contributing/development.md#documentation).
