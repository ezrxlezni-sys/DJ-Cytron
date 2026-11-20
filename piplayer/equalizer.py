"""Equalizer: a 5-band graphic EQ applied to mpv's audio filter chain (so radio and music are both covered).

Presets are just gain tables; "custom" is whatever the sliders are set to. The filter is rebuilt and swapped in live
(no restart of the track or the stream). A cut in front of the bands keeps boosted music from clipping.
"""
BANDS = (60, 230, 910, 3600, 14000)           # Hz, centre of each band
LABELS = ("60 Hz", "230 Hz", "910 Hz", "3.6 kHz", "14 kHz")
MAX_DB = 12
PRESETS = {
    "flat":   [0, 0, 0, 0, 0],
    "bass":   [6, 4, 0, 0, 0],
    "vocal":  [-2, -1, 3, 3, 0],
    "treble": [0, 0, 0, 3, 6],
    "loud":   [5, 2, -1, 2, 4],
}
PRESET_TITLES = {"flat": "Flat", "bass": "Bass boost", "vocal": "Vocal", "treble": "Treble", "loud": "Loud"}


def clean_gains(gains):
    """A list of 5 numbers in -12..12 dB (rounded to 0.5), or None if it is not one."""
    if not isinstance(gains, (list, tuple)) or len(gains) != len(BANDS):
        return None
    out = []
    for g in gains:
        if isinstance(g, bool) or not isinstance(g, (int, float)) or g != g or abs(g) > MAX_DB:
            return None
        out.append(round(float(g) * 2) / 2)
    return out


def preset_for(gains):
    """The preset name these gains match, else "custom"."""
    for name, table in PRESETS.items():
        if [float(x) for x in table] == gains:
            return name
    return "custom"


def build_filter(gains):
    """mpv `af` value for these gains ("" removes the filter when everything is flat)."""
    active = [(f, g) for f, g in zip(BANDS, gains) if g]
    if not active:
        return ""
    parts = [f"equalizer=f={f}:t=o:w=1.2:g={g:g}" for f, g in active]
    boost = max(g for _, g in active)
    if boost > 0:
        parts.insert(0, f"volume=-{boost * 0.7:.1f}dB")       # headroom: the loudest boost would otherwise clip
    return "lavfi=[" + ",".join(parts) + "]"
