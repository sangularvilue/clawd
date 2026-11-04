"""Week 3 (Nov 4): "TAKE THE CLIFFS." Our pipe-organ Soldier of Heaven, 16:9.

Concept: Reagan at Pointe du Hoc over the song's bridge, low ("These are the boys of Pointe du Hoc.
These are the men who took the cliffs."), then the organ slams in on the chorus: the
Church (organ, Swiss Guard, the Basilica, St. Michael), the mountains and the Rangers,
the builders (Mach), his places (Chicago, DC, Notre Dame); the key change pulls out all
the stops (strobes, launches, a meme), the final C-minor chord lands on the card, and
Kobe gets the last word as the organ releases: "Job's not finished."

Song: media/w1104_song_bed.mp3: the organ mix's bridge ~15 dB down under the speech, then our
49 s organ hype cut (media/w1109_song.mp3) from 0.62 s before the chorus (96.000 BPM, studio click).
Beats from the drop (DROP): +0 chorus (plenum), +32 key change (tutti, pedal, chords),
+64 final chord, +72 organ release into the cathedral reverb, ring-out to ~+77.
The Church appears only in the rapid-fire strobes (Will's note).
Footage slots read media/w1104_<key>.*; alt=(key, in) borrows another clip until a slot
lands; text entries: (beat, text, size@720p, y[, style, end_beat]).
"""
import math
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'w1104_'
BPM = 96.0
BEAT = 60 / BPM  # SONG / SONG_START / MUSIC_IN are set with the speech below


def _find(key):
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.webm', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
        path = os.path.join(HERE, 'media', P + key + ext)
        if os.path.exists(path):
            return kind, path
    return None, None


def C(key, label, desc, beats, alt=None, **kw):
    """Footage from media/w1104_<key>.*; if missing, an alternate (alt=(key, in)), else a labeled card."""
    kind, path = _find(key)
    if not path and alt:
        kind, path = _find(alt[0])
        if path:
            kw['in'] = alt[1]
    if path:
        kw.pop('p', None)
        if kind == 'photo':
            for k in ('in', 'speed', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
                kw.pop(k, None)
        return dict({kind: path}, beats=beats, **kw)
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
        kw.pop(k, None)
    return dict(shot='slot', beats=beats, p=dict(label=label, desc=desc, kind='clip'), **kw)


def M(name, beats, **kw):
    """A still from the inspiration board (memes keep their own captions)."""
    return dict(photo=os.path.join(HERE, 'inspiration', name), beats=beats, fit='contain', **kw)


def strobe(*items):
    """Half-beat cuts."""
    out = []
    for it in items:
        it = dict(it, beats=0.5)
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=10)
        out.append(it)
    return out


def _dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None


# ---- the speech pre-roll: Reagan, Pointe du Hoc, 6 June 1984 (WHCA recording, public domain),
# the ~7 s of applause between the two sentences closed up. The organ lands 0.45 s after "cliffs".
SPEECH = 'media/' + P + 'speech_pdh_tight.m4a'
LINE_END = 5.76  # s into the file: end of "...who took the cliffs."
sd = _dur(os.path.join(HERE, SPEECH)) or 6.4
# The song plays low under the speech: media/w1104_song_bed.mp3 is the organ mix from DROP beats before
# the chorus (the bridge, ~15 dB down, which breaks to near-silence under "who took the cliffs"), then the
# 49 s hype cut at full level. It was built for DROP = 11; change DROP and the bed has to be rebuilt.
SONG = 'media/' + P + 'song_bed.mp3'
SONG_START = 0.0
MUSIC_IN = 0
DROP = 11  # the organ slams in on this beat, 0.45 s after "cliffs"
SPEECH_AT = DROP - (LINE_END + 0.45) / BEAT
VOICEOVER = [dict(file=SPEECH, at=SPEECH_AT, src_in=0.0, dur=min(sd, LINE_END + 0.3), gain=1.0, duck=1.0)]
# Reagan's own clip starts 0.15 s before "These"; line his lips up with the voiceover
reagan_in = max(0.0, 0.15 - (SPEECH_AT - 1) * BEAT)
PRE = [
    C('cliffs', 'POINTE DU HOC', 'the cliffs', 1, dim=0.3, speed=0.8, **{'in': 0.8}),
    C('reagan_pdh', 'REAGAN', 'Pointe du Hoc, 1984', 4, dim=0.1, **{'in': reagan_in}),
    C('cliffs_2', 'POINTE DU HOC', 'up the cliff face', 3, dim=0.2, speed=0.85, alt=('cliffs', 1.5)),
    C('rangers_climb', 'RANGERS', 'up the rope', DROP - 8, dim=0.15, speed=0.9),
]

# ---- the organ comes in (song beat 0). The Church only appears in the rapid-fire strobes.
CHORUS = [
    # +0  the drop lands on the biggest hardware
    C('launch', 'LIFTOFF', 'engines, tower clear', 2, fx=dict(punch=0.1)),
    C('carrier', 'CARRIER', 'cat launch', 2),
    C('mach_2', 'MACH INDUSTRIES', 'Viper at sunset', 2, alt=('carrier_2', 0.5)),
    C('test_fire', 'TEST FIRE', 'booster static fire', 2),
    # +8  the mountains and the Rangers
    C('ski_troops', '10TH MOUNTAIN', 'ski troops', 2),
    C('alpine', 'THE ALPS', 'powder', 1),
    C('ski_troops_2', '10TH MOUNTAIN', 'skis on shoulders', 1, alt=('ski_troops', 1.0), **{'in': 0.3}),
    C('f22', 'F-22', 'the climb', 2),
    C('eagle', 'EAGLE', 'in flight', 2),
    # +16  the builders
    C('mach', 'MACH INDUSTRIES', 'static fire', 2, alt=('test_fire', 0.5)),
    C('hypersonic', 'TOMAHAWK', 'ship launch', 1),
    C('hypersonic_2', 'MINUTEMAN III', 'out of the silo', 1, **{'in': 0.6}),
    C('mach_3', 'MACH INDUSTRIES', 'launch, onboard', 2, alt=('mach', 1.8)),
    C('lincoln', 'LINCOLN MEMORIAL', 'push in', 2),
    # +24  his places
    C('chicago_river', 'CHICAGO', 'dye boats', 1),
    C('chicago_river_2', 'CHICAGO', 'the green river', 1),
    C('bulls', 'BULLS', 'The Shot', 1),
    C('soldier_field', 'SOLDIER FIELD', 'Chicago', 1),
    C('lincoln_2', 'LINCOLN MEMORIAL', 'at dusk', 1),
    C('blossoms', 'DC', 'cherry blossoms', 1),
    C('nd_td', 'NOTRE DAME', 'touchdown', 2),
]

# ---- key change: all the stops (song beat 32)
TUTTI = [
    C('fireworks_dc', 'THE MALL', 'fireworks', 2, fx=dict(punch=0.1)),
    C('launch', 'LIFTOFF', 'climb-out', 2, **{'in': 1.5}),
    C('rocky_snow_2', 'ROCKY IV', 'the log', 2, alt=('rocky_snow', 0.0)),
    C('strongman', 'STRONGMAN', 'the stone', 2, **{'in': 0.2}),
    # +40  rapid fire: the Church in flashes
    *strobe(C('organ_pipes', 'THE ORGAN', 'pipes', 1),
            C('carrier', 'CARRIER', 'launch', 1, **{'in': 1.0}),
            C('swiss_guard', 'SWISS GUARD', 'halberds', 1),
            C('f22', 'F-22', 'pass', 1, **{'in': 1.2}),
            C('basilica_nd', 'BASILICA', 'Sacred Heart', 1),
            C('thunder', 'LIGHTNING', 'the bolt', 1, **{'in': 0.15}),
            C('st_michael', 'ST. MICHAEL', 'the archangel', 1, fit='contain'),
            C('test_fire', 'TEST FIRE', 'plume', 1, **{'in': 1.5})),
    # +44  the meme, then grit
    M('09_crocodile_dunk_pray_harder.jpg', 2, zoom=(1.0, 1.06)),
    C('rocky_snow', 'ROCKY IV', 'in the snow', 2),
    C('strug', 'KERRI STRUG', '1996', 1, **{'in': 0.6}),
    C('gibson_2', 'KIRK GIBSON', 'the fist pump', 1, alt=('gibson', 0.2), **{'in': 1.6}),
    C('bodybuilder', 'BODYBUILDER', 'the pose', 1),
    C('bulls', 'BULLS', 'Jordan', 1, **{'in': 1.5}),
    # +52  the builders again
    C('carrier_2', 'CARRIER', 'F-14 off the cat', 2, alt=('carrier', 2.0), **{'in': 0.4}),
    C('mach', 'MACH INDUSTRIES', 'bench fire', 2, **{'in': 2.6}),
    # +56  one per beat
    C('strongman', 'STRONGMAN', 'the roar', 1, **{'in': 1.4}),
    C('soldier_field_2', 'SOLDIER FIELD', 'kickoff', 1, alt=('soldier_field', 1.5), **{'in': 2.2}),
    C('gibson', 'KIRK GIBSON', 'the swing', 1, **{'in': 0.3}),
    C('eagle_2', 'EAGLE', 'the strike', 1, alt=('eagle', 1.6)),
    # +60  rapid fire into the final chord
    *strobe(C('cathedral', 'NATIONAL SHRINE', 'the nave', 1),
            C('fireworks_dc_2', 'FIREWORKS', 'finale', 1, alt=('fireworks_dc', 1.5)),
            C('organ_pipes_2', 'THE ORGAN', 'console', 1, alt=('organ_pipes', 1.5)),
            C('launch', 'LIFTOFF', 'plume', 1, **{'in': 2.5})),
    C('cliffs_2', 'POINTE DU HOC', 'the cliffs', 2, alt=('cliffs', 1.0)),
]

# ---- the final chord (song beat 64), then Kobe gets the last word as the organ releases (song beat 72):
# "Job's not finished. Job finished?" on him, "I don't think so." back on the card.
KOBE = 'media/' + P + 'kobe.m4a'
kobe_d = _dur(os.path.join(HERE, KOBE))
END = [
    C('cliffs_2', 'POINTE DU HOC', 'closing card', 8, alt=('cliffs', 2.0), dim=0.4, speed=0.6,
      fx=dict(every=4, punch=0.06), text=[(0, 'TAKE THE CLIFFS.', 150, 0.5)]),
]
if kobe_d:
    kobe_at = DROP + 72
    VOICEOVER.append(dict(file=KOBE, at=kobe_at, src_in=0.0, dur=kobe_d, gain=1.0, duck=0.5))
    END += [C('kobe', 'KOBE', "Job's not finished.", 5.5),
            C('cliffs_2', 'POINTE DU HOC', 'card again', 2.5, alt=('cliffs', 3.0), dim=0.4, speed=0.6,
              text=[(0, 'TAKE THE CLIFFS.', 150, 0.5)])]
else:
    END[0]['beats'] = 13

SEQ = PRE + CHORUS + TUTTI + END
