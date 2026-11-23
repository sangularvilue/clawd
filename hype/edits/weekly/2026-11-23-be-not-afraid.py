"""BE NOT AFRAID. A 16:9, ~95 s film cut to Sabaton's "The Last Stand" (about 104 BPM).

The premise, in one sentence: you weren't made to stay behind closed doors: this generation is called out into
the open.

The words are Pope John Paul II's: in St Peter's Square on 22 October 1978, at the Mass that began his
pontificate, "Be not afraid! Open wide the doors for Christ!"; and in Denver on 15 August 1993, to hundreds of
thousands of young Americans, not to be afraid to go out on the streets and into public places, that this is no time
to be ashamed of the Gospel, that it is the time to preach it from the rooftops. (The song is about the Swiss
Guard who held the steps of St Peter's in 1527 so the Pope could escape.)

What holds it together: DOORS. Before the drop every shot is a closed door, a shut gate, a raised ramp, someone
waiting behind it; on the chorus's downbeat they are thrown open and people pour out into the light and the streets.
The ending is handed to the viewer: one door left closed, light under it. End line: "Open the doors."

Song bed (make_bed(); 104 BPM; beats of the edit; the band's verses are left out, so no singer is under a voice):
    0-     the free-time swell before the band (record 6.0-18.4 s)      1978: the cry, in Italian
    SW-    the riff, instrumental (record beats 2-35)                    1993: Denver, every door still shut
    PRE-   two bars of the pre-chorus with the singer taken out
    D      THE DROP: chorus 1 (record beat 115)                          the doors thrown open
    BR     the record's quiet bridge                                     John Paul again, a last line
    LI     the lead-in to the last chorus, the choir building
    K      THE KEY CHANGE: the last chorus to the record's dead stop     everything at once
    then silence, the closed door, the line.
Run `python3 edits/weekly/2026-11-23-be-not-afraid.py bed` once to build the bed.
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'bn_'
BPM = 104.0
BEAT = 60 / BPM
SONG = 'media/bn_bed.wav'
SONG_START = 0.0
MUSIC_IN = 0.0
LIMIT = 0.84
FX = dict(sat=1.0, chroma=3, shake=4, punch=0.04)

# ---------------------------------------------------------------- the song bed
RAW_STEMS = 'media/raw/bn_song/stems/htdemucs/laststand'   # Demucs (htdemucs) stems of the archive.org MP3
BEATS_JSON = 'media/bn_beats.json'                          # the record's tracked beats (librosa); bars start on beats = 3 mod 4
PRE = 0.0
SWELL_FROM = 6.0                 # record seconds: where the swell starts (it rises from -45 dB here to the band at 18.4 s)
# (first record beat (None = the swell, from SWELL_FROM), last record beat (None = to the end), vocals?, gain dB)
SEGMENTS = [
    (None, 2, False, 0.0),       # the swell, then the band's first hit (record beat 2)
    (2, 35, False, 0.0),         # the riff, instrumental (8 bars and the pickup)
    (107, 115, False, 0.0),      # the pre-chorus's last two bars, the singer taken out
    (115, 147, True, 0.0),       # THE DROP: chorus 1, the band's own vocals
    (275, 287, False, 0.0),      # the quiet bridge
    (319, 331, False, 0.0),      # the lead-in, the choir taken out: John Paul speaks over it
    (331, None, True, 0.0),      # THE KEY CHANGE: the last chorus to the dead stop
]
OVERLAYS = []


def _beats():
    return json.load(open(os.path.join(HERE, BEATS_JSON)))


def seg_starts():
    """Edit beat at which each segment starts."""
    bt = _beats()
    b, out = 0.0, []
    for a, z, _, _ in SEGMENTS:
        out.append(round(b, 3))
        if z is not None:
            b += (bt[z] - SWELL_FROM) / BEAT if a is None else z - a
    return out


_S = seg_starts()
SW, PREC, D, BR, LI, K = _S[1], _S[2], _S[3], _S[4], _S[5], _S[6]   # riff, pre-chorus, DROP, bridge, lead-in, KEY CHANGE


def make_bed(xfade=0.012):
    import numpy as np
    import soundfile as sf
    bt = _beats()
    st = {k: sf.read(os.path.join(HERE, RAW_STEMS, k + '.wav'), dtype='float32')[0] for k in ('drums', 'bass', 'other', 'vocals')}
    sr = 44100
    n = min(len(v) for v in st.values())
    inst = (st['drums'] + st['bass'] + st['other'])[:n]
    voc = st['vocals'][:n]
    tmpd = os.path.join(HERE, 'media', 'raw', 'bn_bedtmp')
    os.makedirs(tmpd, exist_ok=True)
    y = None
    nx = int(xfade * sr)
    for i, (a, z, keep, g) in enumerate(SEGMENTS):
        t0 = (bt[a] if a is not None else SWELL_FROM) - (PRE if i == 0 else 0.0)
        if z is None:
            t1 = n / sr
            ratio = (bt[-1] - bt[a]) / ((len(bt) - 1 - a) * BEAT)
        elif a is None:                 # the free-time swell before the band: no stretch, exact length
            t1 = bt[z]
            ratio = 1.0
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
            want = int(round(((bt[z] - SWELL_FROM) if a is None else (z - a) * BEAT + (PRE if i == 0 else 0.0)) * sr))
            s2 = s2[:want] if len(s2) >= want else np.concatenate([s2, np.zeros((want - len(s2), 2), np.float32)])
        if y is None:
            y = s2
        else:                           # butt-joined on the bar line, each side eased over 12 ms (no length change)
            k = len(y)
            y = np.concatenate([y, s2])
            y[k - nx:k] *= np.cos(np.linspace(0, np.pi / 2, nx))[:, None]
            y[k:k + nx] *= np.sin(np.linspace(0, np.pi / 2, nx))[:, None]
    for a, z, at in OVERLAYS:                # vocals only, stretched to whole beats, eased in and out
        i0, i1 = int(round(bt[a] * sr)), int(round(bt[z] * sr))
        p_in, p_out = os.path.join(tmpd, 'ov.wav'), os.path.join(tmpd, 'ov2.wav')
        sf.write(p_in, voc[i0:i1], sr, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p_in, '-af', 'rubberband=tempo=%.6f' % ((bt[z] - bt[a]) / ((z - a) * BEAT)),
                        '-c:a', 'pcm_f32le', p_out], check=True)
        o = sf.read(p_out, dtype='float32')[0]
        k = int(round((at * BEAT + PRE) * sr))
        m = min(len(o), len(y) - k)
        r = int(0.01 * sr)
        o[:r] *= np.linspace(0, 1, r)[:, None]
        o[m - r:m] *= np.linspace(1, 0, r)[:, None]
        y[k:k + m] += o[:m]
    for f in os.listdir(tmpd):
        os.remove(os.path.join(tmpd, f))
    os.rmdir(tmpd)
    pk = np.abs(y).max()
    if pk > 0.98:
        y = y * (0.98 / pk)
    sf.write(os.path.join(HERE, SONG), y, sr, subtype='PCM_24')
    return len(y) / sr


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
CRY_F = 'bn_be_not_afraid_1978'      # St Peter's Square, 22 Oct 1978; on camera, reading from his throne
STR_F = 'bn_denver_streets'          # Denver, 15 Aug 1993, an ad-lib after the homily; on camera at the microphone
GO_F = 'bn_denver_other'             # Denver, 1993; at the altar
PH = dict(
    CRY=(CRY_F, 0.30, 7.70),         # "Non abbiate paura! ... Aprite, anzi spalancate le porte a Cristo!"
    P1=(STR_F, 8.62, 9.30),          # "I said,"
    P2=(STR_F, 10.55, 14.25),        # "you should not be ashamed"
    P3=(STR_F, 15.95, 16.70),        # "of the Gospel."
    P4=(STR_F, 18.25, 20.20),        # "You should be proud"
    P5=(STR_F, 21.05, 21.95),        # "of the Gospel."
    Q1=(GO_F, 0.28, 4.75),           # "The Church asks you to go,"
    Q4=(GO_F, 14.40, 16.05),         # "for all the young people of the world,"
    Q6=(GO_F, 21.15, 22.25),         # "this generation,"
    Q7=(GO_F, 23.75, 25.20),         # "the future generation."
)
VOICEOVER = []
SAID = {}


def say(ph, at, gain=1.25, duck=0.4, lead=0.08, tail=0.25, fade=0.08):
    """Phrase ph so that its first word lands on beat `at`."""
    f, w0, w1 = PH[ph]
    SAID[ph] = (f, w0, at)
    VOICEOVER.append(dict(file=media(f), at=at - lead / BEAT, src_in=max(0.0, w0 - lead), dur=w1 - w0 + lead + tail,
                          gain=gain, duck=duck, fade=fade))


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


def say_if(ph, at, **kw):
    if have(PH[ph][0]):
        say(ph, at, **kw)
    else:
        SAID[ph] = (PH[ph][0], PH[ph][1], at)


# 1978, over the swell: the cry ends as the band hits
say_if('CRY', ends('CRY', SW - 0.25), gain=1.35, duck=0.55, tail=0.2)
# 1993, over the riff and the pre-chorus (his own pauses, a little tighter); "of the Gospel" ends a beat before the drop
say_if('P1', SW + 5, gain=1.4, duck=0.42)
say_if('P2', round(SW + 5 + (10.55 - 8.62) / BEAT, 3), gain=1.4, duck=0.42)   # his own pause, so the picture runs on
say_if('P3', SW + 17, gain=1.4, duck=0.42)
say_if('P4', PREC, gain=1.45, duck=0.4)
say_if('P5', round(PREC + (21.05 - 18.25) / BEAT, 3), gain=1.45, duck=0.4, tail=0.3)
SILENCE = [(D - 0.75, D - 0.02)]                                     # a stop before the hit
# 1993, over the bridge and the lead-in: "the future generation." ends on the key change
say_if('Q1', BR + 1, gain=1.45, duck=0.42)
say_if('Q4', 104.5, gain=1.45, duck=0.42)
say_if('Q6', 110.5, gain=1.45, duck=0.42)
say_if('Q7', ends('Q7', K - 0.4), gain=1.5, duck=0.42, tail=0.3)

# ---------------------------------------------------------------- picture (skeleton: shut before the drop, open after)
STOP_REC = 232.62                     # record seconds: the guitars cut off dead (the drums' last fill is 231.55-231.84)
_bt = _beats()
END_HIT = round(K + (STOP_REC - _bt[331]) / ((_bt[-1] - _bt[331]) / (len(_bt) - 1 - 331)), 2)   # the dead stop, in edit beats
END_AT = END_HIT                                                     # the picture cuts with the music

def L(start, ph, crop=None, **kw):     # John Paul on screen, in sync
    f = PH[ph][0]
    if crop:
        kw['crop'] = crop
    return S(start, '/' + f, **dict(kw, **{'in': lips(ph, start)}))


JP78 = (0.0, 0.0, 1.0, 1.0)
JP93 = (0.12, 0.0, 0.76, 1.0)          # the 4:3 Denver tape, framed on him

# ---- 0-SW: the swell. The Holy Door shut; 1978, the new Pope cries out.
OPEN = layout([
    S(0.0, 'holy_door_shut', speed=0.75),                                        # the Holy Door, shut, the Swiss Guard either side
    L(W('CRY', 0.30) - 0.3, 'CRY'),                                              # "Non abbiate paura!"
    S(W('CRY', 3.15) - 0.15, 'holy_door_hand', **{'in': 0.6}),                   # "Aprite, anzi spalancate"  (an old Pope leans in to push it)
    L(W('CRY', 6.32) - 0.15, 'CRY'),                                             # "le porte"
    S(W('CRY', 7.10) - 0.1, 'jp2_young', **{'in': 0.5}),                          # "a Cristo!"  (his arm raised over the square)
], SW)

# ---- SW-D: the riff. Denver, 1993; every door still shut.
STREETS = layout([
    S(SW, 'jp2_denver_2', fx=dict(punch=0.12)),                                  # the band hits: young Americans, Denver 1993
    S(SW + 3, 'jp2_denver'),                                                     # he takes their hands
    L(W('P1', 8.62) - 0.2, 'P1', crop=JP93),                                     # "I said,"
    S(W('P1', 9.40), 'jp2_young_2', **{'in': 1.0}),                              # (his pause: the same man in 1978)
    L(W('P1', 10.45), 'P1', crop=JP93),                                          # "you should not be"
    S(W('P2', 13.60) - 0.1, 'ordination', **{'in': 1.6}),                        # "ashamed"  (a man face down on the marble)
    L(W('P3', 15.95) - 0.2, 'P3', crop=JP93),                                    # "of the Gospel."
    S(SW + 19, 'holy_door_above'),                                               # the threshold from above
    S(SW + 22, 'swiss_guard', **{'in': 0.3}),                                    # a recruit raises his hand to swear
    S(SW + 25, 'ramp_shut', alt=[('holy_door_shut', 1.5)]),
    S(SW + 28, 'ordination_2'),                                                  # his head on his hands
    S(SW + 30, 'church_shut', alt=[('holy_door_hand', 3.0)]),
    L(PREC - 0.2, 'P4', crop=JP93),                                              # "You should be proud"
    S(W('P5', 21.05) - 0.2, 'jp2_denver_2', **{'in': 2.0}),                      # "of the Gospel."  (they throw up their arms)
    S(D - 0.75, 'holy_door_shut', **{'in': 3.2}),                                # the stop: the door, shut
], D)

# ---- D-BR: THE DROP. Chorus 1; the band's own singers. The doors thrown open.
DOORS = layout([
    S(D, 'holy_door_open', fx=dict(punch=0.18, bloom=0.3)),                      # the Holy Door swings open
    S(D + 2, 'loggia_open', alt=[('wyd', 0.0)]),                                 # the loggia opens on the first American pope
    S(D + 4, 'church_open', alt=[('swiss_guard_2', 0.0)]),
    S(D + 6, 'mach_door_open', alt=[('hangar_open', 0.0)]),
    S(D + 8, 'smoke_crowd', alt=[('wyd_2', 0.0)]),
    S(D + 10, 'bay_open', alt=[('holy_door_through', 0.0)]),
    S(D + 12, 'wyd'),                                                            # Americans at World Youth Day under the flag
    S(D + 14, 'ramp_open', alt=[('swiss_guard_2', 1.5)]),
    S(D + 16, 'procession', alt=[('wyd_2', 1.5)]),
    S(D + 18, 'swiss_guard_2'),                                                  # the Guard marches down the steps
    S(D + 20, 'chicago_cheer', alt=[('jp2_denver_2', 1.0)]),
    S(D + 22, 'holy_door_through'),                                              # through the open door
    S(D + 24, 'leo_crowd', alt=[('wyd', 2.0)]),
    S(D + 26, 'home_door', alt=[('hangar_open', 2.0)]),
    S(D + 28, 'wyd_2', **{'in': 2.0}),
    S(D + 30, 'rooftop'),                                                        # St Peter's from above, the city beyond
], BR)

# ---- BR-K: the bridge and the lead-in, the choir taken out. "The Church asks you to go... this generation."
GOES = layout([
    L(BR + 1 - 0.2, 'Q1', crop=JP93),                                            # "The Church asks you to go,"
    S(W('Q1', 3.40), 'jp2_denver_2', **{'in': 1.0}),
    S(104.5 - 0.2, 'wyd_2'),                                                     # "for all the young people of the world,"
    S(108.0, 'ordination', **{'in': 2.4}),
    S(110.5 - 0.2, 'swiss_guard', **{'in': 1.2}),                                # "this generation,"
    S(113.0, 'wyd', **{'in': 1.0}),
    S(W('Q7', 23.75) - 0.2, 'jp2_denver', **{'in': 1.2}),                        # "the future generation."
], K)
GOES.insert(0, C('holy_door_above', round(BR + 1 - 0.2 - BR, 3), **{'in': 2.0}))   # BR: a beat of the threshold

# ---- K-END_AT: THE KEY CHANGE to the record's dead stop. Everything at once.
FINAL = layout([
    S(K, 'loggia_open_2', alt=[('holy_door_open', 0.4)], fx=dict(punch=0.2, bloom=0.35)),
    S(K + 2, 'smoke_crowd_2', alt=[('wyd', 0.5)]),
    S(K + 4, 'swiss_guard_2', **{'in': 0.8}),
    S(K + 6, 'procession_2', alt=[('wyd_2', 0.6)]),
    S(K + 8, 'mach_door_open', alt=[('hangar_open', 1.0)]),
    S(K + 10, 'ordination', **{'in': 0.4}),
    S(K + 12, 'church_open', alt=[('holy_door_through', 1.2)]),
    S(K + 14, 'wyd', **{'in': 2.6}),
    S(K + 16, 'bay_open', alt=[('swiss_guard', 2.0)]),
    S(K + 18, 'jp2_denver_2', **{'in': 0.4}),
    S(K + 20, 'rooftop', **{'in': 1.5}),
    S(K + 22, 'holy_door_open', **{'in': 0.2}),
    S(K + 24, 'wyd_2', **{'in': 0.2}),
    S(K + 26, 'swiss_guard_2', **{'in': 2.2}),
    S(K + 28, 'leo_crowd', alt=[('jp2_denver', 2.4)]),
    S(K + 30, 'loggia_open', alt=[('holy_door_through', 2.0)], **{'in': 1.0}),
    S(K + 34, 'wyd', **{'in': 1.6}),
    S(K + 36, 'holy_door_open', **{'in': 1.6}),
], END_AT)

END_TEXT = os.environ.get('BN_TEXT', 'Open the doors.')
END = [                                       # silence: the door, shut; the line
    C('holy_door_shut', 6.0, speed=0.5, fx=dict(punch=0.0, shake=0, chroma=0)),
    C('holy_door_shut', 8.0, speed=0.35, dim=0.7, fx=dict(punch=0.0, shake=0, chroma=0, sat=0.6),
      text=[(1.0, END_TEXT, 58, 0.5, 'serif')], **{'in': 1.6}),
]

SEQ = OPEN + STREETS + DOORS + GOES + FINAL + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
    b = 0.0
    marks = {id(OPEN[0]): '1978', id(STREETS[0]): 'RIFF 1993', id(DOORS[0]): 'DROP', id(GOES[0]): 'BRIDGE + LEAD-IN',
             id(FINAL[0]): 'KEY CHANGE', id(END[0]): 'END'}
    for s in SEQ:
        if id(s) in marks:
            print('%6.1f  %s' % (b, marks[id(s)]))
        if 'list' in sys.argv:
            src = s.get('clip') or s.get('photo') or ('SLOT ' + s['p']['desc'])
            print('   %6.2f  %5.2f  %s  in=%s' % (b, s['beats'], os.path.basename(src), s.get('in', '')))
        if s['beats'] <= 0:
            print('!! non-positive length at beat %.2f: %s' % (b, s.get('clip') or s.get('p')))
        b += s['beats']
    print('segments start at', _S, ' last hit', END_HIT, ' end', END_AT)
    print('total %.1f beats = %.1f s; missing: %s' % (b, b * BEAT, sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
