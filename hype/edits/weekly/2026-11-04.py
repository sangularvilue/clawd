"""Week 3 (Nov 4): "TAKE THE CLIFFS." Our pipe-organ Soldier of Heaven, 16:9.

Concept: Reagan at Pointe du Hoc over near-silence ("These are the boys of Pointe du Hoc.
These are the men who took the cliffs."), then the organ slams in on the chorus: the
Church (organ, Swiss Guard, the Basilica, St. Michael), the mountains and the Rangers,
the builders (Mach), his places (Chicago, DC, Notre Dame); the key change pulls out all
the stops (strobes, launches, a meme), the final C-minor chord lands on the card, and
Kobe gets the last word as the organ releases: "Job's not finished."

Song: media/w1109_song.mp3, our organ hype cut (96.000 BPM, studio click). Its chorus
downbeat at 0.62 s is SONG_START; the song comes in at beat MUSIC_IN, after the speech.
Song beats from there: +0 chorus (plenum), +32 key change (tutti, pedal, chords),
+64 final chord, +72 organ release into the cathedral reverb, ring-out to ~+77.
Footage slots read media/w1104_<key>.*; alt=(key, in) borrows another clip until a slot
lands; text entries: (beat, text, size@720p, y[, style, end_beat]).
"""
import math
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'w1104_'
SONG = 'media/w1109_song.mp3'
BPM = 96.0
SONG_START = 0.62
BEAT = 60 / BPM


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


# ---- the speech pre-roll: the song waits for the line, then lands on the next beat
SPEECH = 'media/' + P + 'speech_pdh.m4a'
if not os.path.exists(os.path.join(HERE, SPEECH)):
    SPEECH = 'media/' + P + 'speech_ike.m4a'
SPEECH_AT = 0.5  # beats of silence before the first word
sd = _dur(os.path.join(HERE, SPEECH))
MUSIC_IN = 2 * math.ceil((SPEECH_AT + (sd or 5.0) / BEAT + 0.6) / 2) if sd else 8  # whole bars' worth of beats, even
VOICEOVER = [dict(file=SPEECH, at=SPEECH_AT, src_in=0.0, dur=sd, gain=1.5, duck=1.0)] if sd else []

pre_a = round(MUSIC_IN * 0.36 * 2) / 2
pre_b = round(MUSIC_IN * 0.32 * 2) / 2
pre_c = MUSIC_IN - pre_a - pre_b
PRE = [
    C('cliffs', 'POINTE DU HOC', 'the cliffs from the sea', pre_a, dim=0.25, speed=0.8),
    C('reagan_pdh', 'REAGAN', 'Pointe du Hoc, 1984', pre_b, dim=0.15),
    C('rangers_climb', 'RANGERS', 'up the cliffs', pre_c, dim=0.2, speed=0.85),
]

# ---- the organ comes in (song beat 0)
CHORUS = [
    # +0  the Church: the drop lands on the organ itself
    C('organ_pipes', 'THE ORGAN', 'pipes, full stops', 2, fx=dict(punch=0.1)),
    C('swiss_guard', 'SWISS GUARD', 'oath / halberds', 2),
    C('basilica_nd', 'BASILICA', 'Sacred Heart, Notre Dame', 2, speed=0.8),
    C('st_michael', 'ST. MICHAEL', 'the archangel', 2, fit='contain', zoom=(1.0, 1.08)),
    # +8  the mountains and the Rangers
    C('ski_troops', '10TH MOUNTAIN', 'ski troops', 2),
    C('alpine', 'THE ALPS', 'avalanche / ridge', 1),
    C('rangers_climb', 'RANGERS', 'the climb', 1, **{'in': 1.5}),
    C('carrier', 'CARRIER', 'cat launch', 2),
    C('f22', 'F-22', 'afterburner', 2),
    # +16  the builders
    C('mach', 'MACH INDUSTRIES', 'flight / factory', 2, alt=('test_fire', 0.5)),
    C('test_fire', 'TEST FIRE', 'booster static fire', 1),
    C('hypersonic', 'HYPERSONIC', 'test launch', 1),
    C('mach_2', 'MACH INDUSTRIES', 'second shot', 2, alt=('carrier_2', 0.5)),
    C('launch', 'LIFTOFF', 'engines, tower clear', 2),
    # +24  his places
    C('chicago_river', 'CHICAGO', 'the green river', 2),
    C('bulls', 'BULLS', 'Jordan', 1),
    C('soldier_field', 'SOLDIER FIELD', 'Chicago', 1),
    C('lincoln', 'LINCOLN MEMORIAL', 'push in', 1),
    C('blossoms', 'DC', 'cherry blossoms', 1),
    C('nd_td', 'NOTRE DAME', 'touchdown', 2),
]

# ---- key change: all the stops (song beat 32)
TUTTI = [
    C('cathedral', 'CATHEDRAL', 'the nave, light', 2, fx=dict(punch=0.1)),
    C('launch', 'LIFTOFF', 'climb-out', 2, **{'in': 1.5}),
    C('eagle', 'EAGLE', 'in flight', 2),
    C('procession', 'PROCESSION', 'banners, crowds', 2),
    # +40  half-beat strobe
    *strobe(C('carrier', 'CARRIER', 'launch', 1, **{'in': 1.0}),
            C('f22', 'F-22', 'pass', 1, **{'in': 1.2}),
            C('test_fire', 'TEST FIRE', 'plume', 1, **{'in': 1.5}),
            C('thunder', 'LIGHTNING', 'the bolt', 1),
            C('strongman', 'STRONGMAN', 'atlas stone', 1),
            C('hypersonic', 'HYPERSONIC', 'launch', 1, **{'in': 1.0}),
            C('ski_troops', '10TH MOUNTAIN', 'downhill', 1, **{'in': 1.5}),
            C('fireworks_dc', 'THE MALL', 'fireworks', 1)),
    # +44  the meme, then grit
    M('09_crocodile_dunk_pray_harder.jpg', 2, zoom=(1.0, 1.06)),
    C('rocky_snow', 'ROCKY IV', 'in the snow', 2),
    C('strug', 'KERRI STRUG', '1996', 1),
    C('gibson', 'KIRK GIBSON', '1988', 1),
    C('bodybuilder', 'BODYBUILDER', 'the pose', 1),
    C('bulls', 'BULLS', 'Jordan', 1, **{'in': 1.5}),
    # +52  reverent beat, then builders
    C('grotto', 'THE GROTTO', 'candles', 2),
    C('mach_3', 'MACH INDUSTRIES', 'third shot', 2, alt=('mach', 1.8)),
    # +56  one per beat
    C('bells', 'BELLS', 'swinging', 1),
    C('swiss_guard_2', 'SWISS GUARD', 'second take', 1, alt=('swiss_guard', 1.6)),
    C('thunder', 'LIGHTNING', 'second bolt', 1, **{'in': 1.6}),
    C('eagle_2', 'EAGLE', 'second take', 1, alt=('eagle', 1.6)),
    # +60  strobe into the final chord
    *strobe(C('fireworks_dc_2', 'FIREWORKS', 'finale', 1, alt=('fireworks_dc', 1.5)),
            C('launch', 'LIFTOFF', 'plume', 1, **{'in': 2.5}),
            C('organ_pipes_2', 'THE ORGAN', 'console', 1, alt=('organ_pipes', 1.5)),
            C('carrier_2', 'CARRIER', 'second launch', 1, alt=('carrier', 2.0))),
    C('cliffs_2', 'POINTE DU HOC', 'the cliffs', 2, alt=('cliffs', 1.0)),
]

# ---- the final chord (song beat 64) and the organ's release (song beat 72)
_kobe = _find('kobe')[1] or _find('biden_finish')[1]
_bite_key = 'kobe' if _find('kobe')[1] else 'biden_finish'
_bite = _dur(_kobe) if _kobe else None
END = [
    C('cliffs_2', 'POINTE DU HOC', 'closing card', 8, alt=('cliffs', 2.0), dim=0.35, speed=0.6,
      fx=dict(every=4, punch=0.06), text=[(0, 'TAKE THE CLIFFS.', 150, 0.5)]),
]
if _bite:
    END.append(C(_bite_key, 'KOBE', "Job's not finished.", round(max(3.0, _bite + 0.3) / BEAT * 2) / 2,
                 voice=True, voice_gain=1.5, duck=0.6))
else:
    END[0]['beats'] = 13

SEQ = PRE + CHORUS + TUTTI + END
