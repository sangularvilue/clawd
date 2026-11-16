"""SOMEDAY IS TODAY. A 16:9, ~85 s film cut to Dropkick Murphys' "I'm Shipping Up to Boston" (about 130 BPM).

The premise, in one sentence: someone asked this of you before you were born (when the team is up against it,
go in there with all you've got), and "someday" has come due on your watch.

The story, told in order, one voice at a time over one continuous build:
  1920  George Gipp, dying, to Knute Rockne (Reagan in the 1940 film): "Rock... someday, when the team's up
        against it and the breaks are beating the boys, ask them to go in there with all they've got and win
        just one for the Gipper."
  1928  Rockne carries it eight years. The real Rockne, on his own 78 record: "And don't forget, men: today's the
        day we're gonna win! Fight! Fight! Fight! Fight! Fight!"  -> THE DROP: a hand slaps the PLAY LIKE A
        CHAMPION TODAY sign on the downbeat and the team pours out of the tunnel, in color.
  1981  The man who played the Gipper, now President, back at Notre Dame (the record's own breakdown): "There will
        come times in the lives of all of us when we'll be faced with causes bigger than ourselves, and they won't
        be on a playing field."  -> the final riff: Americans going in where it isn't a game.
  Then silence, a hand reaching for the sign, and we stop before it lands. End line: "Someday is today."

What holds it together: a hand slapping the sign, on the beat (with the sound of it), between the chapters; the
last hand never lands. The turn: black and white until the first slap on the drop, color after.

Song bed (make_bed(); beats of the edit at a fixed 130 BPM; the band's tempo wanders 126-131, so every section is
stretched slightly onto the grid; built from Demucs stems so nothing shouted sits under a voice):
    0-24   the mandolin intro (its riff played twice)          Gipp's request
   24-52   the light drums come in                              1928: Rockne
   52      THE DROP: the band slams in (record 0:20)            the slap; the tunnel; color
   52-84   the riff
   84-120  the last chorus, gang vocals                         Notre Dame, no one speaks
  120-140  the record's breakdown (drums fall away), stretched  Reagan, 1981
  140-165  the final riff; the held last hit, then a dead stop  Americans going in
  165-180  silence; the reach; "Someday is today."
Run `python3 edits/weekly/2026-11-16-someday.py bed` once to build the bed (and the slap).
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'sd_'
BPM = 130.0
BEAT = 60 / BPM
SONG = 'media/sd_bed.wav'
SONG_START = 0.0
MUSIC_IN = 0.0                   # the mandolin starts on the first frame
LIMIT = 0.84
FX = dict(sat=0.0, chroma=3, shake=4, punch=0.04)   # black and white until the drop
COLOR = dict(sat=1.05)

# ---------------------------------------------------------------- the song bed
RAW_STEMS = 'media/raw/sd_song/stems/htdemucs/boston'     # Demucs (htdemucs) stems of the CD-rip FLAC
BEATS_JSON = 'media/sd_beats.json'                          # the record's tracked beat times (librosa), seconds
PRE = 0.04                       # the mandolin's first note leads the tracked beat 0 by ~30 ms: keep its attack
# (first record beat, last record beat (None = to the end of the file), keep the vocals stem?, gain dB)
SEGMENTS = [
    (0, 16, False, -1.5),        #   0  the mandolin riff, alone
    (8, 16, False, -1.5),        #  16  its second half again
    (16, 44, False, -1.0),       #  24  the drums come in, lightly
    (44, 76, True, 0.0),         #  52  THE DROP: the full band slams in; the riff
    (252, 288, True, 0.0),       #  84  the last bar of a riff and the last chorus
    (288, 300, 'first', 0.0),    # 120  the breakdown: the drums fall away (the chorus's last shout kept, then no vocals)
    (292, 300, False, 0.0),      # 132  its last two bars again, so Reagan has room
    (300, None, True, 0.0),      # 140  the final riff, the held last hit, the dead stop
]
DROP = D = 52
BREAKDOWN = K = 120
FINAL = F = 140


def _beats():
    return json.load(open(os.path.join(HERE, BEATS_JSON)))


def seg_starts():
    """Edit beat at which each segment starts, and the final hit's edit beat."""
    b, out = 0.0, []
    for a, z, _, _ in SEGMENTS:
        out.append(b)
        if z is not None:
            b += z - a
    return out


def make_bed(xfade=0.012):
    import numpy as np
    import soundfile as sf
    bt = _beats()
    st = {k: sf.read(os.path.join(HERE, RAW_STEMS, k + '.wav'), dtype='float32')[0] for k in ('drums', 'bass', 'other', 'vocals')}
    sr = 44100
    n = min(len(v) for v in st.values())
    inst = (st['drums'] + st['bass'] + st['other'])[:n]
    voc = st['vocals'][:n]
    tmpd = os.path.join(HERE, 'media', 'raw', 'sd_bedtmp')
    os.makedirs(tmpd, exist_ok=True)
    y = None
    nx = int(xfade * sr)
    for i, (a, z, keep, g) in enumerate(SEGMENTS):
        t0 = bt[a] - (PRE if i == 0 else 0.0)
        if z is None:
            t1 = n / sr
            ratio = (bt[-1] - bt[a]) / ((len(bt) - 1 - a) * BEAT)
        else:
            t1 = bt[z]
            ratio = (bt[z] - bt[a]) / ((z - a) * BEAT)
        i0, i1 = int(round(t0 * sr)), int(round(t1 * sr))
        i1 = min(n, i1 + int(0.35 * sr)) if z is not None else i1   # stretch a little past the bar line, then trim exactly
        v = voc[i0:i1].copy()
        if keep is False:
            v[:] = 0
        elif keep == 'first':           # keep the shout on the segment's first beat only, then fade the stem out
            k = int((bt[a + 1] - bt[a]) * 0.9 * sr)
            v[k:] = 0
            r = int(0.05 * sr)
            v[k - r:k] *= np.linspace(1, 0, r)[:, None]
        seg = (inst[i0:i1] + v) * 10 ** (g / 20)
        p_in, p_out = os.path.join(tmpd, 'in.wav'), os.path.join(tmpd, 'out.wav')
        sf.write(p_in, seg, sr, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p_in, '-af',
                        'rubberband=tempo=%.6f:pitchq=quality:transients=crisp:detector=percussive' % ratio,
                        '-c:a', 'pcm_f32le', p_out], check=True)
        s2 = sf.read(p_out, dtype='float32')[0]
        if z is not None:               # exact length on the grid
            want = int(round(((z - a) * BEAT + (PRE if i == 0 else 0.0)) * sr))
            s2 = s2[:want] if len(s2) >= want else np.concatenate([s2, np.zeros((want - len(s2), 2), np.float32)])
        if y is None:
            y = s2
        else:                           # butt-joined on the bar line, each side eased over 12 ms (no length change)
            k = len(y)
            y = np.concatenate([y, s2])
            y[k - nx:k] *= np.cos(np.linspace(0, np.pi / 2, nx))[:, None]
            y[k:k + nx] *= np.sin(np.linspace(0, np.pi / 2, nx))[:, None]
    for f in os.listdir(tmpd):
        os.remove(os.path.join(tmpd, f))
    os.rmdir(tmpd)
    pk = np.abs(y).max()
    if pk > 0.98:
        y = y * (0.98 / pk)
    sf.write(os.path.join(HERE, SONG), y, sr, subtype='PCM_24')
    return len(y) / sr


def make_slap():
    """A hand on a wooden sign: a sharp broadband crack, a short boxy knock and a little stairwell around it."""
    import numpy as np
    import soundfile as sf
    sr = 44100
    rng = np.random.default_rng(3)
    n = int(0.6 * sr)
    t = np.arange(n) / sr
    crack = rng.standard_normal(n) * np.exp(-t / 0.006)
    from scipy.signal import butter, sosfilt
    crack = sosfilt(butter(2, [900, 7000], 'bandpass', fs=sr, output='sos'), crack)
    knock = (np.sin(2 * np.pi * 190 * t) * 0.8 + np.sin(2 * np.pi * 410 * t) * 0.35) * np.exp(-t / 0.035)
    thump = np.sin(2 * np.pi * 85 * t) * np.exp(-t / 0.05) * 0.6
    dry = crack * 1.6 + knock + thump
    room = np.convolve(dry, rng.standard_normal(int(0.25 * sr)) * np.exp(-np.arange(int(0.25 * sr)) / sr / 0.07))[:n] * 0.04
    y = dry + room
    y = y / np.abs(y).max() * 0.95
    sf.write(os.path.join(HERE, 'media', 'sd_slap_synth.wav'), np.stack([y, y], 1).astype('float32'), sr, subtype='PCM_24')


# ---------------------------------------------------------------- footage
def _find(key):
    for name in ((key[1:],) if key.startswith('/') else (P + key, key)):
        for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
            path = os.path.join(HERE, 'media', name + ext)
            if os.path.exists(path):
                return kind, path
    return None, None


def C(key, beats, alt=None, **kw):
    """Footage from media/sd_<key>.* (or an exact media name), else the first alternate that exists
    (alt = key or (key, in) or a list of them), else a labeled card."""
    kind, path = _find(key)
    for a in ([alt] if isinstance(alt, (str, tuple)) else alt or []) if not path else []:
        a = (a,) if isinstance(a, str) else a
        kind, path = _find(a[0])
        if path:
            kw.pop('in', None), kw.pop('crop', None), kw.pop('speed', None)
            if len(a) > 1 and a[1] is not None:
                kw['in'] = a[1]
            break
    if path:
        if kind == 'photo':
            for k in ('in', 'speed', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
                kw.pop(k, None)
            kw.setdefault('fit', 'cover')
            kw.setdefault('zoom', (1.0, 1.07))
        return dict({kind: path}, beats=beats, **kw)
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck', 'mg'):
        kw.pop(k, None)
    return dict(shot='slot', beats=beats, p=dict(label=key.upper().replace('_', ' '), desc=key, kind='clip'), **kw)


def media(key, ext='.m4a'):
    return 'media/' + key + ext


def have(key, ext='.m4a'):
    return os.path.exists(os.path.join(HERE, media(key, ext)))


def S(start, key, alt=None, **kw):
    """A shot that starts on an absolute beat of the edit; layout() gives it its length."""
    return dict(_at=start, _key=key, _alt=alt, **kw)


def layout(rows, end):
    out = []
    for i, r in enumerate(rows):
        r = dict(r)
        start, key, alt = r.pop('_at'), r.pop('_key'), r.pop('_alt')
        nxt = rows[i + 1]['_at'] if i + 1 < len(rows) else end
        out.append(C(key, round(nxt - start, 3), alt, **r))
    return out


# ---------------------------------------------------------------- the voices
# (file, first word starts, last word ends), seconds into the file, from the word-level transcripts in the logs.
GIPP = 'sd_gipp_voice'           # Reagan as Gipp, 1940 film; his voice separated from the film's score (make_voices())
GIPP_PIC = 'w1109_gipper'        # the same take with its picture (lips in sync with the original timing)
ROCKNE_TODAY = 'w1109_rockne_real_today'
ROCKNE_FIGHT = 'w1109_rockne_real_fight'
REAGAN = 'w1109_reagan81_causes'
PH = dict(
    ROCK=(GIPP, 0.00, 0.66),           # "Rock..."
    SOMEDAY=(GIPP, 2.44, 7.18),        # "someday when the team's up against it, the breaks are beating the boys,"
    ASK=(GIPP, 8.96, 10.94),           # "ask them to go in there with all they've got"
    WIN=(GIPP, 11.66, 13.24),          # "win just one for the Gipper."
    TODAY=(ROCKNE_TODAY, 0.00, 2.72),  # "And don't forget, men: today's the day we're gonna win!"
    FIGHT=(ROCKNE_FIGHT, 1.30, 2.64),  # "Fight! Fight! Fight! Fight! Fight!"
    CAUSES=(REAGAN, 0.15, 7.80),       # "There will come times in the lives of all of us when we'll be faced with causes
                                       #  bigger than ourselves, and they won't be on a playing field."
)
VOICEOVER = []
SAID = {}


def say(ph, at, gain=1.25, duck=0.4, lead=0.08, tail=0.25):
    """Phrase ph so that its first word lands on beat `at`."""
    f, w0, w1 = PH[ph]
    SAID[ph] = (f, w0, at)
    VOICEOVER.append(dict(file=media(f), at=at - lead / BEAT, src_in=max(0.0, w0 - lead), dur=w1 - w0 + lead + tail,
                          gain=gain, duck=duck))


def ends(ph, beat):
    """The beat a phrase must start on so that its last word ends on `beat`."""
    f, w0, w1 = PH[ph]
    return beat - (w1 - w0) / BEAT


def W(ph, t):
    """The beat of the edit at which second t of a phrase's file is heard."""
    f, w0, at = SAID[ph]
    return round(at + (t - w0) / BEAT, 2)


def lips(ph, beat):
    """In-point that keeps the speaker's lips in step with phrase ph for a shot starting at `beat`."""
    f, w0, at = SAID[ph]
    return round(w0 + (beat - at) * BEAT, 3)


SLAPS = []


def slap(beat, gain=0.9, duck=1.0):
    """The sound of a hand on the sign, on a beat."""
    f = 'media/sd_slap.m4a' if have('sd_slap') else 'media/sd_slap_synth.wav'
    if os.path.exists(os.path.join(HERE, f)):
        VOICEOVER.append(dict(file=f, at=beat - 0.004 / BEAT, src_in=0.0, dur=0.5, gain=gain, duck=duck, fade=0.3))
    SLAPS.append(beat)


# 1920: the request, over the mandolin (one phrase at a time; the pauses between them are his own, a little shorter)
say('ROCK', 1.5, gain=1.3, duck=0.55)                        # "Rock..."
say('SOMEDAY', 5.0, gain=1.3, duck=0.55)                     # "someday when the team's up against it, the breaks are beating the boys,"
say('ASK', 19.5, gain=1.3, duck=0.5)                         # "ask them to go in there with all they've got"  (the drums answer on 24)
say('WIN', 25.0, gain=1.3, duck=0.5)                         # "win just one for the Gipper."
slap(32.0)                                                   # the first hand on the sign
# 1928: Rockne himself, eight years later
say('TODAY', 40.0, gain=1.35, duck=0.45)                     # "And don't forget, men: today's the day we're gonna win!"
say('FIGHT', ends('FIGHT', D - 0.35), gain=1.4, duck=0.45, lead=0.04, tail=0.12)   # "Fight! Fight! Fight! Fight! Fight!" -> the drop
slap(D, gain=1.0)                                            # THE DROP: the hand lands on the downbeat
for b in (D + 8, D + 16, D + 24, 84, 92, 100, 108):           # the motif on the bar lines while Notre Dame runs out
    slap(b, gain=0.55)
# 1981: the Gipper himself, in the record's breakdown; "playing field" ends on the final riff's downbeat
say('CAUSES', ends('CAUSES', F - 0.25), gain=1.35, duck=0.5, tail=0.3)
slap(F, gain=1.0)
END_HIT = seg_starts()[-1]
try:
    _bt = _beats()
    END_HIT = round(seg_starts()[-1] + (150.70 - _bt[300]) / ((_bt[-1] - _bt[300]) / (len(_bt) - 1 - 300)), 2)
except Exception:
    END_HIT = F + 24.7
END_AT = round(END_HIT + 3.6, 2)     # the held hit, the dead stop, a breath of silence

# ---------------------------------------------------------------- picture
OLD = dict(sat=0.0)


def G(start, ph):                     # Gipp on screen, in sync (the original take's timing)
    return S(start, GIPP_PIC, **{'in': lips(ph, start)})


def R(start):                         # Reagan in 1981, in sync
    return S(start, REAGAN, crop=(0.17, 0.03, 0.70, 0.525), **{'in': lips('CAUSES', start)})


# ---- 0-32: 1920. The request, black and white, over the mandolin.
OPEN = layout([
    S(0.0, 'w1109_sign_static', alt=['w1109_sign_reach'], zoom=(1.0, 1.06)),   # the sign in the dark: PLAY LIKE A CHAMPION TODAY
    G(1.3, 'ROCK'),                                                             # "Rock..."
    S(3.4, 'w1109_gipp_photo', fit='contain', zoom=(1.0, 1.08)),                # the real George Gipp, 1920
    G(W('SOMEDAY', 2.44) - 0.15, 'SOMEDAY'),                                    # "someday"
    S(W('SOMEDAY', 3.06), 'w1109_nd_1920s_2'),                                  # "when the team's up against it"
    S(W('SOMEDAY', 5.92), 'w1109_mud_game_2', **{'in': 0.8}),                   # "the breaks are beating the boys"
    S(W('SOMEDAY', 7.18) + 1.0, 'td1920s', alt=[('w1109_nd_1920s', 1.0)]),       # (the mandolin, alone)
    S(W('ASK', 8.96) - 0.1, 'w1109_nd_1920s_3'),                                # "ask them to go in there"
    S(24.0, 'w1109_nd_1920s', **{'in': 1.05}),                                  # "with all they've got"  (the drums come in)
    G(W('WIN', 11.66) - 0.2, 'WIN'),                                            # "win just one for the Gipper."
], 32.0)

# ---- 32-52: 1928. A hand on the sign; Yankee Stadium; Rockne's own voice; the hand comes up.
REACH_CONTACT = 2.9                   # w1109_sign_reach: the hand meets the sign 2.9 s in
MID = layout([
    S(32.0, 'w1109_sign_slap', **{'in': 0.85}),                                 # the first slap, on the beat
    S(34.0, 'army1928_2', alt=[('w1109_four_horsemen', None)]),                 # Yankee Stadium, the Corps of Cadets: 1928
    S(36.5, 'rockne_team', alt=[('w1109_rockne_real_2', 0.2)]),                 # Rockne among his players (talking: before his voice)
    S(W('TODAY', 0.00) - 0.2, 'rockne_team_2', alt=[('w1109_rockne_real_2', 1.5)]),   # "And don't forget, men:"  (wide: no lips)
    S(W('TODAY', 1.20) - 0.1, 'army1928_3', alt=[('w1109_nd_1920s_2', 1.0)]),   # "today's the day we're gonna win!"  (the goal line)
    S(45.5, 'army1928', alt=[('w1109_nd_1920s_3', 2.0)]),                       # the line
    S(47.0, 'gipp_action', alt=[('w1109_nd_1920s_2', 2.0)], **{'in': 1.0}),
    S(W('FIGHT', 1.30) - 0.1, 'td1920s', alt=[('w1109_nd_1920s', 0.2)], **{'in': 0.6}),  # "Fight!"
    S(W('FIGHT', 1.60) - 0.1, 'w1109_nd_1920s_3', **{'in': 0.4}),               # "Fight!"
    S(W('FIGHT', 1.88) - 0.1, 'army1928_2', alt=[('w1109_nd_1920s_2', 2.4)], **{'in': 1.2}),   # "Fight!"
    S(W('FIGHT', 2.12) - 0.1, 'w1109_mud_game', **{'in': 0.6}),                 # "Fight!"
    S(W('FIGHT', 2.40) - 0.1, 'w1109_sign_reach',                               # "Fight!" and the hand comes up to the sign...
      **{'in': round(REACH_CONTACT - (D - W('FIGHT', 2.40) + 0.1) * BEAT, 3)}),
], D)

# ---- 52-84: THE DROP. ...and lands. Color. The team pours out of the tunnel.
DROPS = layout([
    S(D, 'slap', alt=[('w1109_sign_reach', REACH_CONTACT)], fx=dict(punch=0.16, bloom=0.3, sat=1.05)),
    S(D + 1.5, 'tunnel', alt=[('w1109_tunnel_run_2', 1.3)], fx=dict(punch=0.1)),
    S(D + 4, 'tunnel_2', alt=[('w1109_tunnel_run', 0.6)]),
    S(D + 6, 'charge'),
    S(D + 8, 'slap_2', alt=[('w1109_sign_slap_3', 0.0)]),
    S(D + 9, 'students'),
    S(D + 11, 'band'),
    S(D + 13, 'stairs'),
    S(D + 16, 'slap_3', alt=[('w1109_sign_slap_2', 0.3)]),
    S(D + 17, 'tunnel', alt=[('w1109_tunnel_run_2', 2.0)], **{'in': 1.6}),
    S(D + 19, 'dome'),
    S(D + 21, 'charge', **{'in': 1.5}),
    S(D + 24, 'slap_4', alt=[('w1109_sign_slap', 0.85)]),
    S(D + 25, 'win'),
    S(D + 28, 'students', **{'in': 1.5}),
    S(D + 30, 'army1928', alt=[('w1109_nd_1920s', 1.4)], **{'in': 1.0}),        # then
], 84)

# ---- 84-120: the last chorus, gang vocals; no one speaks. Then and now, a slap on every bar.
CHORUS = layout([
    S(84, 'slap', alt=[('w1109_sign_slap', 0.85)], **{'in': 0.0}),
    S(85, 'tunnel_2', alt=[('w1109_tunnel_run', 0.0)], **{'in': 1.0}),
    S(88, 'band', **{'in': 1.5}),
    S(90, 'w1109_nd_1920s_2', **{'in': 0.5}),
    S(92, 'slap_2', alt=[('w1109_sign_slap_3', 0.0)], **{'in': 0.2}),
    S(93, 'win', **{'in': 1.5}),
    S(96, 'w1109_four_horsemen'),
    S(97, 'charge', **{'in': 2.5}),
    S(100, 'slap_3', alt=[('w1109_sign_slap_2', 0.3)], **{'in': 0.2}),
    S(101, 'students', **{'in': 2.5}),
    S(104, 'stairs', **{'in': 1.5}),
    S(106, 'w1109_rockne_real_2', **{'in': 2.0}),
    S(108, 'slap_4', alt=[('w1109_sign_slap', 0.85)], **{'in': 0.2}),
    S(109, 'tunnel', alt=[('w1109_tunnel_run_2', 2.6)], **{'in': 2.4}),
    S(112, 'dome', **{'in': 1.5}),
    S(114, 'win', **{'in': 2.8}),
    S(117, 'w1109_gipp_photo_2', fit='contain'),
], K)

# ---- 120-140: the breakdown. Reagan, 1981: the causes that won't be on a playing field. Faces before they go in.
BREAK = layout([
    S(K, 'reagan1981', alt=[('w1109_r81_grads', 0.0)]),                          # the arena, 17 May 1981
    R(W('CAUSES', 0.15) - 0.2),                                                 # "There will come times in the lives of all of us"
    S(W('CAUSES', 2.38) + 0.3, 'storm_linemen', speed=0.7),                     # "when we'll be faced with"
    S(W('CAUSES', 4.12) - 0.1, 'mud_training', speed=0.7),                      # "causes bigger than ourselves,"
    S(W('CAUSES', 5.48) + 0.2, 'fire_in', speed=0.6),                           # (a breath)
    R(W('CAUSES', 6.0) - 0.15),                                                 # "and they won't be on a playing field."
], F)

# ---- 140-165: the final riff. Americans going in where it isn't a game. The held last hit.
FIN = layout([
    S(F, 'fire_in', fx=dict(punch=0.14, bloom=0.25)),
    S(F + 2, 'surf_rescue'),
    S(F + 4, 'slap', alt=[('w1109_sign_slap', 0.85)], **{'in': 0.0}),
    S(F + 5, 'wildfire'),
    S(F + 7, 'mud_training_2'),
    S(F + 8, 'storm_linemen', **{'in': 1.5}),
    S(F + 10, 'mach_new'),
    S(F + 12, 'flood_rescue'),
    S(F + 13, 'er_team'),
    S(F + 14, 'tunnel_2', alt=[('w1109_tunnel_run', 0.8)], **{'in': 0.5}),
    S(F + 16, 'night_builders'),
    S(F + 17, 'fire_in_2'),
    S(F + 18, 'wildfire_2'),
    S(F + 19, 'mach_new_2'),
    S(F + 20, 'charge', **{'in': 0.5}),
    S(F + 21, 'slap_2', alt=[('w1109_sign_slap_3', 0.0)], **{'in': 0.2}),
    S(F + 21.5, 'surf_rescue', **{'in': 1.5}),
    S(F + 22, 'slap_3', alt=[('w1109_sign_slap_2', 0.3)], **{'in': 0.2}),
    S(F + 22.5, 'fire_in', **{'in': 2.0}),
    S(F + 23, 'slap_4', alt=[('w1109_sign_slap', 0.85)], **{'in': 0.2}),
    S(F + 23.5, 'mud_training', **{'in': 2.5}),
    S(F + 24, 'tunnel', alt=[('w1109_tunnel_run_2', 1.3)], **{'in': 0.3}),
    S(END_HIT, 'charge', fx=dict(punch=0.16, bloom=0.3), **{'in': 1.0}),        # the held last hit
], END_AT)

# ---- silence. A hand comes up to the sign; we stop before it lands.
END_TEXT = os.environ.get('SD_TEXT', 'Someday is today.')
END = [
    C('reach_hold', 14.0, alt=[('w1109_sign_reach', 0.6)], fx=dict(punch=0.0, shake=0, chroma=0, sat=1.0),
      text=[(7.0, END_TEXT, 54, 0.5, 'serif')]),
]


def make_reach(src='w1109_sign_reach', t0=1.7, t1=2.78, slow=4.0, hold=4.0):
    """The last shot: the hand comes up toward the sign at a quarter speed and stops a frame before it lands."""
    path = os.path.join(HERE, 'media', src + '.mp4')
    if not os.path.exists(path):
        return
    vf = ('trim=%f:%f,setpts=%f*(PTS-STARTPTS),minterpolate=fps=30:mi_mode=blend,tpad=stop_mode=clone:stop_duration=%f'
          % (t0, t1, slow, hold))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-vf', vf, '-an', '-c:v', 'libx264', '-crf', '14',
                    '-pix_fmt', 'yuv420p', os.path.join(HERE, 'media', 'sd_reach_hold.mp4')], check=True)

OLD_REFS = {'w1109_gipp_photo', 'w1109_gipp_photo_2', 'w1109_four_horsemen', 'w1109_nd_1920s', 'w1109_nd_1920s_2',
            'w1109_nd_1920s_3', 'w1109_rockne_real', 'w1109_rockne_real_2', 'w1109_mud_game', 'w1109_mud_game_2',
            'sd_army1928', 'sd_army1928_2', 'sd_td1920s', 'sd_gipp_action', 'sd_rockne_team', 'sd_rockne_team_2'}


def era(items):
    for it in items:
        path = it.get('clip') or it.get('photo')
        if not path:
            continue
        key = os.path.splitext(os.path.basename(path))[0]
        it['fx'] = dict(it.get('fx', {}), sat=0.0 if key in OLD_REFS else it.get('fx', {}).get('sat', COLOR['sat']))


era(DROPS + CHORUS + BREAK + FIN + END)
SEQ = OPEN + MID + DROPS + CHORUS + BREAK + FIN + END


def make_voices():
    """Reagan's Gipp, separated from the 1940 film's score (Demucs), with a gentle low cut."""
    src = os.path.join(HERE, 'media', 'raw', 'sd_gipp', 'stems', 'htdemucs', 'gipper', 'vocals.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', 'highpass=f=110,lowpass=f=9000,volume=2.0,alimiter=limit=0.89',
                    '-c:a', 'aac', '-b:a', '192k', os.path.join(HERE, 'media', 'sd_gipp_voice.m4a')], check=True)


if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
        make_slap()
        make_voices()
        make_reach()
    b = 0.0
    marks = {id(OPEN[0]): '1920', id(MID[0]): '1928', id(DROPS[0]): 'DROP', id(CHORUS[0]): 'CHORUS',
             id(BREAK[0]): 'BREAKDOWN 1981', id(FIN[0]): 'FINAL', id(END[0]): 'END'}
    for s in SEQ:
        if id(s) in marks:
            print('%6.1f  %s' % (b, marks[id(s)]))
        if 'list' in sys.argv:
            src = s.get('clip') or s.get('photo') or ('SLOT ' + s['p']['desc'])
            print('   %6.2f  %5.2f  %s  in=%s' % (b, s['beats'], os.path.basename(src), s.get('in', '')))
        if s['beats'] <= 0:
            print('!! non-positive length at beat %.2f: %s' % (b, s.get('clip') or s.get('p')))
        b += s['beats']
    print('segments start at', seg_starts(), ' final hit', END_HIT, ' end', END_AT)
    print('total %.1f beats = %.1f s; missing: %s' % (b, b * BEAT, sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
