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
    (319, 331, True, 0.0),       # the lead-in, the choir building
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
PH = dict(
    CRY=('bn_be_not_afraid_1978', 0.3, 5.0),     # "Non abbiate paura! Aprite, anzi spalancate le porte a Cristo!"  (timings: fill from the log)
    STREETS=('bn_denver_streets', 0.3, 14.0),    # "Do not be afraid to go out on the streets ... preach it from the rooftops."  (fill from the log)
    LAST=('bn_denver_other', 0.3, 4.0),          # a last line in the bridge  (fill from the log)
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


say_if('CRY', ends('CRY', SW - 0.3), gain=1.3, duck=0.6)            # 1978: the cry ends as the band hits
say_if('STREETS', ends('STREETS', D - 1.0), gain=1.35, duck=0.4)    # 1993: "...preach it from the rooftops." ends a beat before the drop
SILENCE = [(D - 0.75, D - 0.02)]                                     # a stop before the hit
say_if('LAST', BR + 1.0, gain=1.3, duck=0.45)                       # in the quiet bridge
END_AT = None                                                        # set below from the record's dead stop

# ---------------------------------------------------------------- picture (skeleton: shut before the drop, open after)
STOP_REC = 232.62                     # record seconds: the guitars cut off dead (the drums' last fill is 231.55-231.84)
_bt = _beats()
END_HIT = round(K + (STOP_REC - _bt[331]) / ((_bt[-1] - _bt[331]) / (len(_bt) - 1 - 331)), 2)   # the dead stop, in edit beats
END_AT = END_HIT                                                     # the picture cuts with the music

OPEN = layout([
    S(0.0, 'holy_door_shut'),                     # the great bronze door, closed
    S(3.0, 'jp2_young'),                          # 1978: the new Pope in St Peter's Square
    S(7.0, 'church_shut'),
    S(10.0, 'jp2_young_2'),                       # "Open wide the doors"
    S(14.0, 'hangar_shut'),
    S(17.0, 'bay_shut'),
], SW)

STREETS = layout([
    S(SW, 'jp2_denver', fx=dict(punch=0.1)),      # the band hits: Denver, 1993
    S(SW + 4, 'ramp_shut'),
    S(SW + 7, 'church_shut', **{'in': 1.5}),
    S(SW + 10, 'jp2_denver_2'),
    S(SW + 14, 'home_door'),
    S(SW + 17, 'hangar_shut', **{'in': 1.5}),
    S(SW + 20, 'bay_shut', **{'in': 1.5}),
    S(SW + 23, 'holy_door_shut', **{'in': 1.5}),
    S(PREC, 'swiss_guard'),
    S(PREC + 4, 'jp2_denver', **{'in': 2.0}),
], D)

DOORS = layout([
    S(D, 'holy_door_open', fx=dict(punch=0.18, bloom=0.3)),    # THE DROP: the doors thrown open
    S(D + 2, 'church_open'),
    S(D + 4, 'hangar_open'),
    S(D + 6, 'bay_open'),
    S(D + 8, 'procession'),
    S(D + 10, 'ramp_open'),
    S(D + 12, 'wyd'),
    S(D + 14, 'tunnel_doors'),
    S(D + 16, 'procession_2'),
    S(D + 18, 'congress'),
    S(D + 20, 'swiss_guard_2'),
    S(D + 22, 'ordination'),
    S(D + 24, 'wyd_2'),
    S(D + 26, 'missionary'),
    S(D + 28, 'congress_2'),
    S(D + 30, 'rooftop'),
], BR)

BRIDGE = layout([
    S(BR, 'jp2_denver_2', **{'in': 1.0}),
    S(BR + 6, 'rooftop', **{'in': 1.5}),
], LI)

LEADIN = layout([
    S(LI, 'procession', **{'in': 1.5}),
    S(LI + 3, 'wyd', **{'in': 1.5}),
    S(LI + 6, 'swiss_guard', **{'in': 1.5}),
    S(LI + 9, 'congress', **{'in': 1.5}),
], K)

FINAL = layout([
    S(K, 'holy_door_open', fx=dict(punch=0.18, bloom=0.35), **{'in': 1.0}),   # THE KEY CHANGE
    S(K + 4, 'procession_2', **{'in': 1.0}),
    S(K + 8, 'wyd_2', **{'in': 1.0}),
    S(K + 12, 'ordination', **{'in': 1.0}),
    S(K + 16, 'congress_2', **{'in': 1.0}),
    S(K + 20, 'church_open', **{'in': 1.0}),
    S(K + 24, 'missionary', **{'in': 1.0}),
    S(K + 28, 'rooftop', **{'in': 1.0}),
], END_AT)

END_TEXT = os.environ.get('BN_TEXT', 'Open the doors.')
END = [
    C('home_door', 12.0, fx=dict(punch=0.0, shake=0, chroma=0), text=[(5.0, END_TEXT, 54, 0.5, 'serif')]),
]

SEQ = OPEN + STREETS + DOORS + BRIDGE + LEADIN + FINAL + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
    b = 0.0
    marks = {id(OPEN[0]): '1978', id(STREETS[0]): 'RIFF 1993', id(DOORS[0]): 'DROP', id(BRIDGE[0]): 'BRIDGE',
             id(LEADIN[0]): 'LEAD-IN', id(FINAL[0]): 'KEY CHANGE', id(END[0]): 'END'}
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
