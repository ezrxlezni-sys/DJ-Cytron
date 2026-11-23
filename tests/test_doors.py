import time
import datetime
import json
import threading

from conftest import wait_for
from test_api import sent_commands


class FakeButton:
    def __init__(self, pin, pressed=False):
        self.pin, self.is_pressed, self.closed = pin, pressed, False
        self.when_pressed = self.when_released = None

    def close(self):
        self.closed = True


def post(client, body):
    return client.post("/api/doors", data=json.dumps(body), content_type="application/json")


def doors(client):
    return client.get("/api/state").get_json()["doors"]


def setup_doors(app, hour=10, autoplay=True, pins=None):
    svc = app.extensions["piplayer"]
    made = {}
    svc.bathrooms._factory = lambda pin: made.setdefault(pin, FakeButton(pin))
    svc.bathrooms._clock = lambda: datetime.datetime(2026, 1, 1, hour, 0)
    svc.settings.set("bathrooms", {"autoplay": autoplay, "pins": pins or {}, "fade": 0, "fadeout": 0})
    return svc, made


def test_defaults_in_state(client):
    d = doors(client)
    assert d["autoplay"] is False and d["from"] == "08:00" and d["to"] == "18:00"
    assert d["pins"] == {} and d["active"] == [] and d["error"] is None


def test_sensors_follow_the_pins(app, client):
    svc, made = setup_doors(app, pins={"male": 12, "female": 13})
    made[12] = FakeButton(12, pressed=True)
    svc.bathrooms.start()
    assert [(r["id"], r["occupied"]) for r in svc.bathrooms.snapshot()] == [("male", True), ("female", False)]
    made[13].when_pressed()
    made[12].when_released()
    assert [r["occupied"] for r in svc.bathrooms.snapshot()] == [False, True]
    assert doors(client)["active"] == ["female", "male"]


def test_rewiring_closes_old_sensors_and_resets_readings(app, client):
    svc, made = setup_doors(app, pins={"male": 12, "female": 13})
    svc.bathrooms.start()
    assert post(client, {"pins": {"male": 5, "female": None}}).status_code == 200
    assert made[12].closed and made[13].closed
    assert doors(client)["pins"] == {"male": 5} and svc.bathrooms.snapshot()[1]["occupied"] is None


def test_gpio_failure_is_reported_not_raised(app, client):
    svc, _ = setup_doors(app, pins={"male": 12})
    def boom(pin):
        raise ModuleNotFoundError("No module named 'gpiozero'")
    svc.bathrooms._factory = boom
    svc.bathrooms.start()
    assert "gpiozero" in doors(client)["error"] and doors(client)["active"] == []


def test_config_validation_and_save(client):
    assert post(client, {"pins": {"male": 99}}).status_code == 400
    assert post(client, {"pins": {"male": 5, "female": 5}}).status_code == 400
    assert post(client, {"pins": {"male": "x"}}).status_code == 400
    assert post(client, {"from": "8am"}).status_code == 400
    assert post(client, {"autoplay": True, "from": "09:00", "to": "17:30"}).status_code == 200
    d = doors(client)
    assert (d["autoplay"], d["from"], d["to"]) == (True, "09:00", "17:30")


def paused(svc):
    return svc.player.snapshot()["paused"]


def test_autoplay_pauses_when_both_doors_open_and_resumes_when_one_closes(app):
    svc, _ = setup_doors(app)
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}, {"kind": "ytm", "id": "q2", "title": "Two"}]
    b = svc.bathrooms
    b.set("male", False); b.set("female", False)
    assert not svc.player.snapshot()["playing"]
    b.set("female", True)                                     # first visitor -> play the queue
    assert wait_for(lambda: (svc.player.snapshot()["current"] or {}).get("id") == "q1")
    b.set("male", True); b.set("female", False)               # one door still closed -> keeps playing
    assert wait_for(lambda: svc.player.snapshot()["playing"]) and not paused(svc)
    b.set("male", False)                                      # both open -> PAUSE (not stop)
    assert wait_for(lambda: paused(svc))
    assert svc.player.snapshot()["playing"] and svc.player.snapshot()["current"]["id"] == "q1"
    b.set("female", True)                                     # someone returns -> resume the same track
    assert wait_for(lambda: not paused(svc))
    assert svc.player.snapshot()["current"]["id"] == "q1"


def mpv_cmds(app, name):
    return [c for c in sent_commands(app) if c[0] == name or (c[0] == "set_property" and c[1] == name)]


def test_radio_is_held_silent_and_resumed_instantly_without_reconnecting(app):
    svc, _ = setup_doors(app)
    b = svc.bathrooms
    b.set("male", True)                                       # empty queue -> first station
    first = svc.stations.all()[0]["id"]
    assert wait_for(lambda: (svc.player.snapshot()["current"] or {}).get("id") == first)
    assert wait_for(lambda: len(mpv_cmds(app, "loadfile")) >= 1)   # loadfile goes out from a background thread
    loads = len(mpv_cmds(app, "loadfile"))
    b.set("male", False)                                      # everyone left
    assert wait_for(lambda: paused(svc))                      # reported as paused to the UI...
    assert wait_for(lambda: ["set_property", "mute", True] in sent_commands(app))   # ...but only silenced
    assert ["set_property", "pause", True] not in sent_commands(app)               # never really paused
    b.set("female", True)
    assert wait_for(lambda: not paused(svc))
    assert wait_for(lambda: ["set_property", "mute", False] in sent_commands(app))   # the fake mpv logs it a moment later
    assert len(mpv_cmds(app, "loadfile")) == loads            # no reconnect: instant


def test_toggle_releases_a_held_stream(app):
    svc, _ = setup_doors(app)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    svc.bathrooms.set("male", False)
    assert wait_for(lambda: paused(svc))
    svc.player.toggle()                                       # the user presses play
    assert wait_for(lambda: not paused(svc))


def test_radio_is_stopped_not_held_once_the_hours_end(app):
    svc, _ = setup_doors(app)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    svc.bathrooms._clock = lambda: datetime.datetime(2026, 1, 1, 19, 0)      # past closing time
    svc.bathrooms.evaluate()
    assert wait_for(lambda: not svc.player.snapshot()["playing"])
    assert ["set_property", "mute", True] not in sent_commands(app)


def test_autoplay_controls_music_the_user_started_too(app):
    svc, _ = setup_doors(app)
    b = svc.bathrooms
    b.set("male", False); b.set("female", False)
    svc.player.play_now([{"kind": "ytm", "id": "mine", "title": "Mine"}])   # started by hand, doors both open
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    b.set("male", True); b.set("male", False)                 # a visit comes and goes
    assert wait_for(lambda: paused(svc))                      # paused although the user started it
    b.set("female", True)
    assert wait_for(lambda: not paused(svc)) and svc.player.snapshot()["current"]["id"] == "mine"


def test_enabling_autoplay_pauses_immediately_when_nobody_is_in(app, client):
    svc, _ = setup_doors(app, autoplay=False)
    svc.bathrooms.set("male", False); svc.bathrooms.set("female", False)
    svc.player.play_now([{"kind": "ytm", "id": "x", "title": "Song"}])
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    assert post(client, {"autoplay": True}).status_code == 200
    assert wait_for(lambda: paused(svc))


def test_autoplay_does_not_resume_after_the_user_changes_track(app):
    svc, _ = setup_doors(app)
    b = svc.bathrooms
    b.set("male", True)
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", False); b.set("male", True)
    b.set("male", False)
    svc.player.play_now([{"kind": "ytm", "id": "other", "title": "Other"}])   # user picks something else
    # mpv's events arrive in order but asynchronously: the pause=true sent by autoplay can still be in flight, so
    # wait until "other is playing and not paused" has held steadily before the next door change
    def playing_other():
        return svc.player.snapshot()["current"]["id"] == "other" and not paused(svc)
    assert wait_for(lambda: playing_other() and (time.sleep(0.3) or playing_other()))
    b.set("female", True)
    time.sleep(0.2)
    assert svc.player.snapshot()["current"]["id"] == "other" and not paused(svc)


def test_autoplay_empty_queue_uses_first_station(app):
    svc, _ = setup_doors(app)
    svc.bathrooms.set("male", True)
    first = svc.stations.all()[0]["id"]
    assert wait_for(lambda: (svc.player.snapshot()["current"] or {}).get("id") == first)


def test_autoplay_respects_hours_and_the_switch(app):
    svc, _ = setup_doors(app, hour=22)
    svc.bathrooms.set("male", True)
    assert not svc.player.snapshot()["queue"]                 # outside opening hours
    svc, _ = setup_doors(app, autoplay=False)
    svc.bathrooms.set("male", False); svc.bathrooms.set("male", True)
    assert not svc.player.snapshot()["queue"]                 # switched off


def test_stale_sensor_is_flagged_only_during_opening_hours(app):
    svc, made = setup_doors(app, hour=15, pins={"male": 12})
    svc.bathrooms.start()
    now = svc.bathrooms._clock().timestamp()
    rooms = lambda: {r["id"]: r for r in svc.bathrooms.snapshot()}
    svc.bathrooms._rooms["male"]["since"] = now - 3600                  # changed an hour ago
    assert rooms()["male"]["stale"] is False
    svc.bathrooms._rooms["male"]["since"] = now - 5 * 3600              # 5 h without a change (since 10:00)
    assert rooms()["male"]["stale"] is True
    svc.bathrooms._rooms["male"]["since"] = now - 20 * 3600             # yesterday: only today's hours count
    assert rooms()["male"]["stale"] is True                             # 08:00 -> 15:00 = 7 h
    assert rooms()["female"]["stale"] is False                          # no sensor configured -> never stale
    svc.bathrooms._clock = lambda: datetime.datetime(2026, 1, 1, 22, 0)
    assert rooms()["male"]["stale"] is False                            # closed hours
    svc.bathrooms._clock = lambda: datetime.datetime(2026, 1, 1, 8, 30)
    svc.bathrooms._rooms["male"]["since"] = datetime.datetime(2025, 12, 31, 19, 0).timestamp()
    assert rooms()["male"]["stale"] is False                            # 30 min into the day, not overnight


def test_clearing_all_pins_disables_the_sensors_instead_of_falling_back(app, client):
    svc, made = setup_doors(app, pins={"male": 12, "female": 13})
    svc.bathrooms.start()
    assert doors(client)["active"] == ["female", "male"]
    assert post(client, {"pins": {"male": "", "female": None}}).status_code == 200
    assert doors(client)["pins"] == {} and doors(client)["active"] == []
    assert [r["occupied"] for r in svc.bathrooms.snapshot()] == [None, None]


def test_switching_autoplay_off_unmutes_a_held_radio_stream(app, client):
    svc, _ = setup_doors(app)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    svc.bathrooms.set("male", False)
    assert wait_for(lambda: paused(svc))                      # silenced
    assert post(client, {"autoplay": False}).status_code == 200
    assert wait_for(lambda: not paused(svc))                  # un-silenced, still playing
    assert svc.player.snapshot()["playing"]


# ---------- fade-in when a door closing starts the music ----------
def fade_setup(app, fade=2, scale=0.02, volume=60):
    svc, _ = setup_doors(app)
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": fade, "fadeout": 0})
    svc.bathrooms.FADE_SCALE = scale                      # run the fade in milliseconds
    svc.player.set_volume(volume)
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    vols, real = [], svc.player.set_volume

    def spy(v):
        vols.append(v)
        return real(v)
    svc.player.set_volume = spy
    return svc, vols, real


def test_fade_setting_default_and_validation(client):
    assert doors(client)["fade"] == 5
    assert post(client, {"fade": 12}).status_code == 200 and doors(client)["fade"] == 12
    assert post(client, {"fade": 0}).status_code == 200 and doors(client)["fade"] == 0
    for bad in (61, -1, "abc", None):
        assert post(client, {"fade": bad}).status_code == 400
    assert doors(client)["fade"] == 0                     # a rejected value changes nothing


def test_music_fades_in_when_a_door_closes(app):
    svc, vols, _ = fade_setup(app)
    svc.bathrooms.set("male", True)                       # first visitor -> start the queue
    assert wait_for(lambda: len(vols) > 8 and vols[-1] == 60)
    assert vols[0] == 5                                   # starts at 8% of 60, before any sound
    assert vols == sorted(vols) and len(set(vols)) > 5    # a smooth rise, not a jump
    assert svc.player.snapshot()["volume"] == 60 and svc.player.snapshot()["current"]["id"] == "q1"


def test_no_fade_when_set_to_zero(app):
    svc, vols, _ = fade_setup(app, fade=0)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    time.sleep(0.2)
    assert vols == [] and svc.player.snapshot()["volume"] == 60


def test_door_opening_mid_fade_restores_the_volume(app):
    svc, vols, _ = fade_setup(app, scale=0.5)             # a 1 second fade
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: len(vols) >= 3 and vols[-1] < 60)
    svc.bathrooms.set("male", False)                      # visitor leaves halfway through
    assert wait_for(lambda: paused(svc) and svc.player.snapshot()["volume"] == 60)
    n = len(vols)
    time.sleep(0.4)
    assert len(vols) == n                                 # the cancelled fade made no further changes
    assert svc.player.snapshot()["volume"] == 60


def test_your_own_volume_change_ends_the_fade(app):
    svc, vols, real = fade_setup(app, scale=0.5)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: len(vols) >= 3 and vols[-1] < 40)
    real(20)                                              # you drag the slider (not through the fade)
    time.sleep(0.5)
    assert svc.player.snapshot()["volume"] == 20          # the fade gave up and left your value alone


def test_the_fade_runs_again_on_the_next_visit(app):
    svc, vols, _ = fade_setup(app)
    b = svc.bathrooms
    b.set("male", True)
    assert wait_for(lambda: vols and vols[-1] == 60 and svc.player.snapshot()["volume"] == 60)
    b.set("male", False)
    assert wait_for(lambda: paused(svc))
    vols.clear()
    b.set("female", True)                                 # someone else walks in -> resume, quietly at first
    assert wait_for(lambda: not paused(svc) and vols and vols[-1] == 60)
    assert vols[0] == 5 and svc.player.snapshot()["volume"] == 60


# ---------- spoken announcements at the doors ----------
class Speaker:
    """Stands in for the text-to-speech engine: records what was said and can be held 'mid-sentence'."""

    def __init__(self, hold=False, fail=False):
        self.said, self.during, self.fail = [], [], fail
        self.started, self.gate = threading.Event(), threading.Event()
        if not hold:
            self.gate.set()

    def __call__(self, text):
        self.said.append(text)
        self.started.set()
        self.gate.wait(3)
        if self.fail:
            raise RuntimeError("no speakers")


def talking(app, hold=False, fail=False, hour=10, **settings):
    svc, made = setup_doors(app, hour=hour)
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": 0, "fadeout": 0, "bye": "", **settings})
    b = svc.bathrooms
    b.speaker = Speaker(hold, fail)
    b._speech_ok = lambda: True
    b.set("male", False)                                      # first readings (None -> False) are never announced
    b.set("female", False)
    return svc, b, b.speaker


def test_announcement_settings_defaults_and_validation(client):
    d = doors(client)
    assert d["announce"] is True and d["speech"] is False        # (speech is off while testing)
    assert d["welcome"] == "Thank you for choosing Cytron DJ. Enjoy the vibe!"
    assert d["reminder"] == "Please remember to flush and keep it clean."
    assert post(client, {"welcome": "  Hello   there  ", "reminder": "", "announce": False}).status_code == 200
    d = doors(client)
    assert d["welcome"] == "Hello there" and d["reminder"] == "" and d["announce"] is False
    assert post(client, {"welcome": "x" * 161}).status_code == 400
    assert post(client, {"reminder": 5}).status_code == 400
    assert doors(client)["welcome"] == "Hello there"             # rejected values change nothing


def test_welcome_is_spoken_before_the_music_starts(app):
    svc, b, sp = talking(app, hold=True)
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", True)                                        # a door closes
    assert sp.started.wait(2) and sp.said == ["Thank you for choosing Cytron DJ. Enjoy the vibe!"]
    time.sleep(0.2)
    assert not svc.player.snapshot()["playing"]                # still talking: the music waits
    sp.gate.set()                                              # ...the welcome finishes
    assert wait_for(lambda: (svc.player.snapshot()["current"] or {}).get("id") == "q1")


def test_reminder_is_spoken_a_delay_after_the_door_closed(app):
    svc, b, sp = talking(app, reminder_delay=1)
    b.FADE_SCALE = 0.3                                         # a 0.3 second wait in the test
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", True)
    assert wait_for(lambda: len(sp.said) == 1)                 # the welcome comes straight away
    assert sp.said[0] == "Thank you for choosing Cytron DJ. Enjoy the vibe!"
    assert wait_for(lambda: len(sp.said) == 2)                 # the reminder follows while the door is still closed
    assert sp.said[1] == "Please remember to flush and keep it clean."
    assert svc.player.snapshot()["playing"]


def test_reminder_is_skipped_when_the_door_opens_first(app):
    svc, b, sp = talking(app, reminder_delay=1)
    b.FADE_SCALE = 0.5
    b.set("male", True)
    assert wait_for(lambda: len(sp.said) == 1)
    b.set("male", False)                                       # left before the reminder was due
    time.sleep(0.8)
    assert len(sp.said) == 1
    b.set("male", True); b.set("male", False); b.set("male", True)    # closing again restarts one wait, not two
    time.sleep(0.8)
    assert sp.said.count("Please remember to flush and keep it clean.") == 1


def test_reminder_delay_setting_default_and_validation(client):
    assert doors(client)["reminder_delay"] == 60
    assert post(client, {"reminder_delay": 150}).status_code == 200 and doors(client)["reminder_delay"] == 150
    for bad in (-1, 3601, "abc", None):
        assert post(client, {"reminder_delay": bad}).status_code == 400
    assert doors(client)["reminder_delay"] == 150
    assert post(client, {"reminder_delay": 0}).status_code == 200 and doors(client)["reminder_delay"] == 0


def test_message_over_playing_music_ducks_it_and_restores(app):
    svc, b, sp = talking(app, hold=True)
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", True)
    sp.gate.set()
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    sp.said.clear(); sp.started.clear(); sp.gate.clear()
    b.set("female", True)                                      # the other room is used: a message over the playing music
    assert sp.started.wait(2)
    assert wait_for(lambda: ["set_property", "volume", 30] in sent_commands(app))      # music ducked while talking
    sp.gate.set()
    assert wait_for(lambda: sent_commands(app).count(["set_property", "volume", 100]) >= 1)   # and restored afterwards


def test_nothing_is_said_at_startup_or_when_rewired(app):
    svc, made = setup_doors(app, pins={"male": 12, "female": 13})
    b = svc.bathrooms
    b.speaker = Speaker()
    b._speech_ok = lambda: True
    made[12] = FakeButton(12, pressed=True)
    b.start()                                                  # a door is already closed at start-up
    b.start()                                                  # rewiring resets the readings and re-reads them
    time.sleep(0.2)
    assert b.speaker.said == []


def test_no_announcement_when_off_empty_or_outside_the_hours(app):
    svc, b, sp = talking(app, announce=False)
    b.set("male", True); b.set("male", False)
    time.sleep(0.2)
    assert sp.said == []
    svc2, b2, sp2 = talking(app, reminder="")                  # an empty message is simply skipped
    b2.set("male", True)
    assert wait_for(lambda: sp2.said == ["Thank you for choosing Cytron DJ. Enjoy the vibe!"])
    b2.set("male", False)
    time.sleep(0.2)
    assert len(sp2.said) == 1
    svc3, b3, sp3 = talking(app, hour=22)                      # after the closing time
    b3.set("male", True); b3.set("male", False)
    time.sleep(0.2)
    assert sp3.said == []


def test_a_broken_speaker_never_stops_the_music(app):
    svc, b, sp = talking(app, fail=True)
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", True)
    assert wait_for(lambda: (svc.player.snapshot()["current"] or {}).get("id") == "q1")


def test_a_second_message_is_skipped_while_one_is_being_spoken(app):
    svc, b, sp = talking(app, hold=True)
    b.set("male", True)
    assert sp.started.wait(2)
    assert b._say("another one") is False                      # while the welcome is still playing
    time.sleep(0.2)
    assert len(sp.said) == 1
    sp.gate.set()


def test_preview_button_endpoint(app, client):
    svc, b, sp = talking(app)
    assert post_to(client, "/api/doors/announce", {"which": "welcome"}).status_code == 200
    assert wait_for(lambda: sp.said == ["Thank you for choosing Cytron DJ. Enjoy the vibe!"])
    assert post_to(client, "/api/doors/announce", {"which": "bogus"}).status_code == 400
    b._speech_ok = lambda: False
    r = post_to(client, "/api/doors/announce", {"which": "reminder"})
    assert r.status_code == 400 and "espeak-ng" in r.get_json()["error"]


def post_to(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


# ---------- volume behaviour around spoken messages ----------
def mpv_volumes(app):
    return [c[2] for c in sent_commands(app) if c[:2] == ["set_property", "volume"]]


def test_the_music_comes_back_up_gradually_after_a_message(app):
    svc, b, sp = talking(app, hold=True)
    svc.player.DUCK_SCALE = 0.05
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", True)
    sp.gate.set()
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    sp.said.clear(); sp.started.clear(); sp.gate.clear()
    b.set("female", True)
    assert sp.started.wait(2)
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [30])
    sp.gate.set()
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [100])
    rise = mpv_volumes(app)
    up = rise[len(rise) - 1 - rise[::-1].index(30):]           # everything after the dip bottomed out
    assert up == sorted(up) and up[0] == 30 and up[-1] == 100 and len(set(up)) > 5    # a ramp, not a snap


def test_the_voice_is_not_quiet_when_a_message_arrives_mid_fade(app):
    svc, vols, real = fade_setup(app, scale=0.5, volume=60)   # a 1 second fade
    b = svc.bathrooms
    b.speaker, b._speech_ok = lambda text: None, (lambda: True)
    b.set("male", False); b.set("female", False)
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": 2, "welcome": "", "reminder": "Mind the step", "reminder_delay": 0})
    b.set("male", True)
    assert wait_for(lambda: len(vols) >= 3 and vols[-1] < 40)  # the fade is under way and the volume is low
    seen = []
    b.speaker = lambda text: seen.append(svc.player.snapshot()["volume"])
    b.set("female", True)                                      # the other door closes: the reminder (no delay), mid-fade
    assert wait_for(lambda: seen)
    assert seen == [60]                                        # spoken at your volume, not the faded-down one


def test_the_fade_curve_starts_gently(app):
    svc, vols, _ = fade_setup(app, volume=100)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: len(vols) > 15 and vols[-1] == 100)
    assert vols[0] == 8 and vols[10] < 8 + (100 - 8) * 0.4     # at the halfway mark well under half of the way there


def test_a_message_failure_is_logged_not_raised(app, caplog):
    svc, b, sp = talking(app, fail=True)
    with caplog.at_level("WARNING", logger="piplayer.bathrooms"):
        assert b._say("hello") is False
    assert "no speakers" in caplog.text


# ---------- the announcement controls in Settings: voice, music level, return time ----------
def test_music_level_and_return_time_settings(client):
    d = doors(client)
    assert d["duck"] == 30 and d["rise"] == 2 and d["voice"] == ""
    assert post(client, {"duck": 50, "rise": 4}).status_code == 200
    d = doors(client)
    assert d["duck"] == 50 and d["rise"] == 4
    for bad in ({"duck": 101}, {"duck": -1}, {"duck": "x"}, {"rise": 31}, {"rise": -1}, {"rise": None}):
        assert post(client, bad).status_code == 400
    assert doors(client)["duck"] == 50                         # rejected values change nothing


def test_voice_setting_only_accepts_installed_voices(client, monkeypatch):
    from piplayer import speech
    monkeypatch.setattr(speech, "voices", lambda: ["en_GB-alan-medium", "espeak-ng"])
    monkeypatch.setattr(speech, "use_voice", lambda v: used.append(v))
    used = []
    assert post(client, {"voice": "en_GB-alan-medium"}).status_code == 200
    assert doors(client)["voice"] == "en_GB-alan-medium" and doors(client)["voices"] == ["en_GB-alan-medium", "espeak-ng"]
    assert post(client, {"voice": "nope"}).status_code == 400
    assert post(client, {"voice": 3}).status_code == 400
    assert post(client, {"voice": ""}).status_code == 200      # back to automatic
    assert used == ["en_GB-alan-medium", ""]


def test_changing_the_voice_prepares_the_messages_again(app, client, monkeypatch):
    from piplayer import speech
    monkeypatch.setattr(speech, "voices", lambda: ["espeak-ng"])
    svc = app.extensions["piplayer"]
    got = []
    svc.bathrooms.preparer = lambda *t: got.append(t)
    svc.bathrooms._speech_ok = lambda: True
    assert post(client, {"voice": "espeak-ng"}).status_code == 200
    assert wait_for(lambda: got and len(got[0]) == 3)


def test_the_saved_music_level_and_return_time_are_used(app):
    svc, b, sp = talking(app, duck=15, rise=6)
    calls = []
    svc.player.duck = lambda on, level=None, up=None, **kw: calls.append((on, level, up))
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    b.set("female", True); b.set("female", False)
    assert wait_for(lambda: len(calls) >= 2)
    assert calls[:2] == [(True, 15, 6), (False, 15, 6)]


def test_duck_level_and_return_time_reach_mpv(app):
    p = app.extensions["piplayer"].player
    p.DUCK_SCALE = 0.02
    p.duck(True, level=10)
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [10])
    p.duck(False, up=0)
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [100])


# ---------- fade-out when the last door opens ----------
def out_setup(app, fadeout=2, scale=0.05, volume=60, **settings):
    svc, vols, real = fade_setup(app, fade=0, scale=scale, volume=volume)
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": 0, "fadeout": fadeout, **settings})
    svc.bathrooms.set("male", False)
    svc.bathrooms.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    vols.clear()
    return svc, vols, real


def test_fadeout_setting_default_and_validation(client):
    assert doors(client)["fadeout"] == 3
    assert post(client, {"fadeout": 6}).status_code == 200 and doors(client)["fadeout"] == 6
    for bad in (61, -1, "abc", None):
        assert post(client, {"fadeout": bad}).status_code == 400
    assert doors(client)["fadeout"] == 6


def test_music_fades_out_then_pauses_and_the_volume_is_put_back(app):
    svc, vols, _ = out_setup(app)
    svc.bathrooms.set("male", False)                       # the last visitor leaves
    assert not paused(svc) or vols                         # not cut instantly
    assert wait_for(lambda: paused(svc) and vols and vols[-1] == 60)
    low = min(vols)
    assert low <= 6                                        # it went right down (about 8 % of 60) before the pause
    down = vols[:vols.index(low) + 1]
    assert down == sorted(down, reverse=True) and len(set(down)) > 5      # a smooth fall, not a drop
    assert svc.player.snapshot()["volume"] == 60           # ready for the next visit's fade-in


def test_no_fadeout_when_set_to_zero(app):
    svc, vols, _ = out_setup(app, fadeout=0)
    svc.bathrooms.set("male", False)
    assert wait_for(lambda: paused(svc))
    assert vols == []


def test_a_door_closing_mid_fadeout_keeps_the_music_playing_at_your_volume(app):
    svc, vols, _ = out_setup(app, fadeout=2, scale=0.5)    # a 1 second fade-out
    svc.bathrooms.set("male", False)
    assert wait_for(lambda: len(vols) >= 3 and vols[-1] < 50)
    svc.bathrooms.set("female", True)                      # someone walks in halfway
    assert wait_for(lambda: svc.player.snapshot()["volume"] == 60)
    n = len(vols)
    time.sleep(0.5)
    assert len(vols) == n and not paused(svc) and svc.player.snapshot()["playing"]


def test_your_own_volume_change_ends_the_fadeout_and_pauses(app):
    svc, vols, real = out_setup(app, fadeout=2, scale=0.5)
    svc.bathrooms.set("male", False)
    assert wait_for(lambda: len(vols) >= 3 and vols[-1] < 45)
    real(25)
    assert wait_for(lambda: paused(svc))
    time.sleep(0.2)
    assert svc.player.snapshot()["volume"] == 25           # your value, not restored over


# ---------- goodbye message and quiet idle music ----------
def test_goodbye_is_spoken_when_a_door_opens(app):
    svc, b, sp = talking(app, bye="See you soon", reminder_delay=3600)
    b.set("male", True)
    assert wait_for(lambda: len(sp.said) == 1)                 # the welcome
    b.set("male", False)
    assert wait_for(lambda: sp.said[-1:] == ["See you soon"])
    svc2, b2, sp2 = talking(app, bye="")                       # an empty goodbye is skipped
    b2.set("male", True); b2.set("male", False)
    time.sleep(0.2)
    assert sp2.said == ["Thank you for choosing Cytron DJ. Enjoy the vibe!"]
    svc3, b3, sp3 = talking(app, announce=False, bye="x")
    b3.set("male", True); b3.set("male", False)
    time.sleep(0.2)
    assert sp3.said == []


def test_bye_setting_default_and_preview(client, app):
    assert doors(client)["bye"] == "Thank you for visiting. See you again soon!"
    assert post(client, {"bye": "x" * 161}).status_code == 400
    assert post(client, {"bye": "  Bye   now "}).status_code == 200 and doors(client)["bye"] == "Bye now"
    svc, b, sp = talking(app, bye="Bye now")
    assert post_to(client, "/api/doors/announce", {"which": "bye"}).status_code == 200
    assert wait_for(lambda: sp.said == ["Bye now"])


def test_idle_setting_validation(client):
    assert post(client, {"idle": 50}).status_code == 200 and doors(client)["idle"] == 50
    for bad in (-1, 101, "x", None):
        assert post(client, {"idle": bad}).status_code == 400
    assert doors(client)["idle"] == 50


def test_music_keeps_playing_quietly_when_nobody_is_in(app):
    svc, _ = setup_doors(app)
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": 0, "fadeout": 0, "idle": 30})
    b = svc.bathrooms
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", False); b.set("female", False)               # everyone out: a song still plays...
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    assert wait_for(lambda: ["set_property", "volume", 30] in sent_commands(app))   # ...at 30 %
    assert not paused(svc)
    b.set("male", True)                                        # a visitor: back to full volume
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [100])
    assert not paused(svc)
    b.set("male", False)                                       # leaves: quiet again, still no pause
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [30])
    assert not paused(svc) and svc.player.snapshot()["playing"]


def test_idle_zero_pauses_as_before_and_idle_stops_after_hours(app):
    svc, _ = setup_doors(app)
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": 0, "fadeout": 0, "idle": 0})
    b = svc.bathrooms
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.set("male", False); b.set("female", False); b.set("male", True)
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    b.set("male", False)
    assert wait_for(lambda: paused(svc))


def test_no_idle_music_after_the_hours(app):
    svc, _ = setup_doors(app, hour=22)                         # after the hours: nothing plays, idle or not
    svc.settings.set("bathrooms", {"autoplay": True, "pins": {}, "fade": 0, "fadeout": 0, "idle": 30})
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    svc.bathrooms.set("male", False)
    time.sleep(0.3)
    assert not svc.player.snapshot()["playing"]


def test_a_message_over_idle_music_returns_to_the_idle_level(app):
    svc, b, sp = talking(app, idle=30, bye="", welcome="Hi")
    svc.player.queue = [{"kind": "ytm", "id": "q1", "title": "One"}]
    b.evaluate()
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [30])
    b._say("hello")
    assert wait_for(lambda: mpv_volumes(app)[-1:] == [30])      # dips no lower than 30 and returns to 30, never to 100
    assert 100 not in mpv_volumes(app)[mpv_volumes(app).index(30):]


# ---------- speaking speed, message variants, {greeting} ----------
def test_speaking_speed_setting_default_and_validation(client):
    from piplayer import speech
    assert doors(client)["speed"] == 1.0
    assert post(client, {"speed": 0.75}).status_code == 200
    assert doors(client)["speed"] == 0.75 and speech._chosen["speed"] == 0.75
    for bad in (0.1, 2, "fast", None):
        assert post(client, {"speed": bad}).status_code == 400
    assert doors(client)["speed"] == 0.75                        # rejected values change nothing
    post(client, {"speed": 1.0})


def test_speed_changes_the_cache_key_and_the_espeak_rate(monkeypatch):
    from piplayer import speech
    speech.use_speed(1.0)
    normal = speech._key("espeak-ng", "hi")
    speech.use_speed(1.5)
    try:
        assert speech._key("espeak-ng", "hi") != normal          # a new speed is rendered again, not served from the cache
        calls = []
        monkeypatch.setattr(speech.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
        monkeypatch.setattr(speech, "_pad", lambda src, dst: None)
        monkeypatch.setattr(speech.Path, "unlink", lambda self, *a, **k: None)
        speech._render_espeak("hi", speech.Path("/tmp/x.wav"))
        assert calls[0][calls[0].index("-s") + 1] == "225"       # 150 words/min x 1.5
        speech.use_speed("junk")
        assert speech._chosen["speed"] == 1.0                    # nonsense falls back to normal
        speech.use_speed(9)
        assert speech._chosen["speed"] == speech.MAX_SPEED       # and out-of-range values are clamped
    finally:
        speech.use_speed(1.0)


def test_messages_are_one_variant_per_line(client):
    assert post(client, {"welcome": "  Hello   there \n\n Welcome in  \n"}).status_code == 200
    assert doors(client)["welcome"] == "Hello there\nWelcome in"
    assert post(client, {"welcome": "\n".join(["x"] * 11)}).status_code == 400     # too many variants
    assert post(client, {"welcome": "ok\n" + "x" * 161}).status_code == 400       # one line too long
    assert doors(client)["welcome"] == "Hello there\nWelcome in"


def test_a_different_variant_is_said_each_time_and_never_the_same_twice(app):
    svc, b, sp = talking(app, welcome="One\nTwo\nThree")
    said = [b._text("welcome") for _ in range(30)]
    assert set(said) == {"One", "Two", "Three"}
    assert all(a != c for a, c in zip(said, said[1:]))
    svc2, b2, _ = talking(app, welcome="Only one")
    assert [b2._text("welcome") for _ in range(3)] == ["Only one"] * 3          # a single message is just repeated


def test_greeting_follows_the_time_of_day_and_every_wording_is_prepared(app):
    svc, b, sp = talking(app, welcome="{greeting}! Welcome.")
    for hour, word in ((9, "Good morning"), (14, "Good afternoon"), (20, "Good evening")):
        b._clock = lambda h=hour: datetime.datetime(2026, 1, 1, h, 0)
        assert b._text("welcome") == f"{word}! Welcome."
    b._clock = lambda: datetime.datetime(2026, 1, 1, 9, 0)
    b.set("male", True)                                        # and a real door event says it too
    assert wait_for(lambda: sp.said) and sp.said == ["Good morning! Welcome."]
    svc, b, sp = talking(app, welcome="{greeting}! Hi\nPlain", reminder="Bye")
    assert sorted(b._all_texts()) == sorted(["Good morning! Hi", "Good afternoon! Hi", "Good evening! Hi", "Plain", "Bye"])


def test_a_closed_door_resumes_music_the_user_had_paused(app):
    svc, _ = setup_doors(app)
    b = svc.bathrooms
    svc.player.play_now([{"kind": "ytm", "id": "mine", "title": "Mine"}])
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    b.set("male", False); b.set("female", False)
    assert wait_for(lambda: paused(svc))
    svc.player.pause(False); assert wait_for(lambda: not paused(svc))
    svc.player.pause(True); assert wait_for(lambda: paused(svc))     # paused by hand while nobody is in
    b._playing = None
    b.set("male", True)                                       # a visitor closes the door
    assert wait_for(lambda: not paused(svc))                  # ...the music must play, not stay silent


def test_autoplay_retries_when_the_stream_failed_to_start(app):
    svc, _ = setup_doors(app)
    b = svc.bathrooms
    b.RETRY_AFTER = 0
    import piplayer.bathrooms as mod
    mod.RETRY_AFTER = 0
    svc.player.queue = []
    svc.stations.all = lambda: []                             # nothing to play yet
    b.set("male", True)
    assert b._playing is None                                 # not remembered as "started"
    svc.stations.all = lambda: [{"id": "r1", "title": "R", "url": "http://x/", "kind": "radio"}]
    b.evaluate()                                              # the next tick
    assert wait_for(lambda: svc.player.snapshot()["playing"])
    svc.player.state.update(playing=False, loading=False, error="Could not play this item")   # the stream dropped for good
    b.evaluate()
    assert wait_for(lambda: svc.player.snapshot()["playing"] and not svc.player.snapshot()["error"])


def test_saving_other_settings_does_not_restart_the_sensors(app, client):
    """The UI resends the pins with every autosave: an unchanged wiring must not blank the readings (that paused the music)."""
    svc, made = setup_doors(app, pins={"male": 12, "female": 13})
    svc.bathrooms.start()
    made[12].when_pressed()                                   # someone is inside
    since = svc.bathrooms.snapshot()[0]["since"]
    assert post(client, {"pins": {"male": 12, "female": 13}, "fade": 3}).status_code == 200
    room = svc.bathrooms.snapshot()[0]
    assert room["occupied"] is True and room["since"] == since
    assert not made[12].closed                                # the same button object is still in use


def test_unchanged_pins_are_retried_after_a_gpio_error(app, client):
    svc, made = setup_doors(app, pins={"male": 12})
    svc.bathrooms.error = "RuntimeError: pin busy"
    post(client, {"pins": {"male": 12}})
    assert svc.bathrooms.error is None and 12 in made        # a save is the way to retry a failed start
