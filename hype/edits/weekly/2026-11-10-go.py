"""GO. A 16:9, ~88 s film cut to Kanye West's "Stronger" (104 BPM).

The premise, in one sentence: this generation chooses the hard things, and every one of us is a station that
has to answer "Go."

The words: President Kennedy at Rice Stadium, 12 September 1962 ("We choose to go to the Moon... not because
they are easy, but because they are hard... one we are unwilling to postpone, and one we intend to win").
What holds it together: the Mission Control go/no-go poll. The flight director calls each station and every
"Go!" lands on a beat and on a different American. The last station he calls is the viewer.

The turn is WAIT -> GO, not then -> now. Before the drop everything is coiled and still (horses in the gate,
a sprinter set in the blocks, controllers at their consoles, a rocket on the pad). On the drop all of them go
at once. Past and present are mixed throughout and keep their own color.

Song bed (make_bed(); beats of the edit; only clean bars of the record are used, never the verses):
   0-8    cold open: radio hiss, the flight director asks for a go/no-go
   8-16   the two-bar vocoder intro
  16-60   the dark bass passage from late in the record (bars 107-117): the build, under Kennedy and the poll
  60-92   THE DROP: the first hook (bars 2-9); the last bar of it is the a-cappella break
  92-140  the instrumental finale (bars 122-133), then the record's own last hit
 140-152  silence; one more station is called; nobody answers. End line: "Are you go?"
Run `python3 edits/weekly/2026-11-10-go.py bed` once to build the bed.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'go_'
BPM = 104.0
BEAT = 60 / BPM
SONG = 'media/go_bed.wav'
SONG_START = 0.0
PHASE = 0.262                    # the record's first downbeat (bar 0), seconds
M0 = 8                           # edit beat of the bed's first downbeat
MUSIC_IN = M0 - PHASE / BEAT     # so the record's pick-up before the downbeat is kept
BUILD = M0 + 8                   # 16  the bass passage starts
DROP = BUILD + 44                # 60  the hook
BREAK = DROP + 28                # 88  the a-cappella bar
FINALE = DROP + 32               # 92
LAST = FINALE + 48               # 140 the record's last hit
END_AT = LAST + 2.0              # 142 silence
LIMIT = 0.94
FX = dict(sat=1.0, chroma=3, shake=4, punch=0.04)

# ---------------------------------------------------------------- the song bed
# Record beats (4 per bar; bar b starts at PHASE + 4b beats): the intro (bars 0-1), the bass passage with its
# a-cappella lead-out (bars 107-117), hook 1 with its break (bars 2-9), the last twelve bars (122-133) and the tail.
RAW = 'media/raw/go_song/stronger.flac'
SEGMENTS = [(None, 8, 0.0, 0.0), (428, 472, -7.0, -2.5), (8, 40, 0.0, 0.0), (488, None, 0.0, 0.0)]
# (from, to) in record beats, None = start / end of file; then gain in dB at the segment's start and end: the bass
# passage is nearly as loud as the hook on the record, so it starts 7 dB down and climbs, and the drop has somewhere to go


def make_bed(xfade=0.02):
    import numpy as np
    import soundfile as sf
    tmp = os.path.join(HERE, 'media', 'raw', 'go_bed_tmp.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(HERE, RAW), '-map', '0:a:0', '-ar', '44100', '-ac', '2',
                    '-c:a', 'pcm_f32le', tmp], check=True)
    x, sr = sf.read(tmp, dtype='float32')
    os.remove(tmp)
    t = lambda rb: PHASE + rb * BEAT
    nx = int(xfade * sr)
    ramp = np.linspace(0, 1, nx)[:, None]
    y = None
    for a, b, g0, g1 in SEGMENTS:
        i0 = 0 if a is None else int(round(t(a) * sr))
        i1 = len(x) if b is None else int(round(t(b) * sr))
        seg = x[i0:i1] * (10 ** (np.linspace(g0, g1, i1 - i0) / 20))[:, None]
        if y is None:
            y = seg
        else:  # the outgoing segment fades out over the incoming one's last moments before its bar line
            y = np.concatenate([y[:-nx], y[-nx:] * (1 - ramp) + x[i0 - nx:i0] * ramp * 10 ** (g0 / 20), seg])
    pk = np.abs(y).max()
    if pk > 0.98:
        y = y * (0.98 / pk)
    sf.write(os.path.join(HERE, SONG), y, sr, subtype='PCM_24')
    return len(y) / sr


# ---------------------------------------------------------------- footage
def _find(key):
    for name in ((key[1:],) if key.startswith('/') else (P + key,)):
        for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
            path = os.path.join(HERE, 'media', name + ext)
            if os.path.exists(path):
                return kind, path
    return None, None


def C(key, beats, alt=None, **kw):
    """Footage from media/go_<key>.*; else the first alternate that exists (alt = key or (key, in) or a list),
    else a labeled card, so the cut renders from day one and fills in as footage lands."""
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
    return 'media/' + P + key + ext


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


VOICEOVER = []

# ---------------------------------------------------------------- picture (first pass: the WAIT -> GO skeleton)
OPEN = layout([
    S(0.0, 'mocr_wait'),                                  # a room of people waiting for one word
    S(4.0, 'poll_film'),                                  # the flight director asks
    S(M0, 'pad_wait'),                                    # the rocket on the pad, venting
    S(M0 + 4, 'derby_wait'),                              # horses in the gate
], BUILD)

WAIT = layout([
    S(BUILD, 'jfk_choose'),                               # Kennedy at Rice
    S(BUILD + 6, 'sprint_wait'),
    S(BUILD + 9, 'cat_wait'),
    S(BUILD + 12, 'drag_wait'),
    S(BUILD + 15, 'surgeon_wait'),
    S(BUILD + 18, 'jfk_choose'),
    S(BUILD + 24, 'snap_wait'),
    S(BUILD + 27, 'jump_wait'),
    S(BUILD + 30, 'firing_wait'),
    S(BUILD + 33, 'mach_wait'),
    S(BUILD + 36, 'hard'),                                # "not because they are easy"
    S(BUILD + 40, 'jfk_choose'),                          # "but because they are hard"
], DROP)

GO = layout([
    S(DROP, 'derby_go', fx=dict(punch=0.14)),             # the gate bursts
    S(DROP + 2, 'sprint_go'),
    S(DROP + 4, 'cat_go'),
    S(DROP + 6, 'drag_go'),
    S(DROP + 8, 'pad_go', fx=dict(bloom=0.3)),
    S(DROP + 11, 'snap_go'),
    S(DROP + 13, 'jump_go'),
    S(DROP + 15, 'mach_go'),
    S(DROP + 17, 'swim_go'),
    S(DROP + 19, 'rodeo_go'),
    S(DROP + 21, 'indy_go'),
    S(DROP + 23, 'alert_go'),
    S(DROP + 25, 'surgeon_go'),
    S(DROP + 26.5, 'staging'),
    S(BREAK, 'walkout_2026'),                             # the a-cappella bar: they walk out
], FINALE)

FIN = layout([
    S(FINALE, 'launch_go', fx=dict(bloom=0.35, punch=0.14)),
    S(FINALE + 4, 'mocr_go'),
    S(FINALE + 8, 'scramble_go'),
    S(FINALE + 12, 'weld_go'),
    S(FINALE + 16, 'jfk_choose'),                         # "...one we intend to win"
    S(FINALE + 32, 'launch_go_2'),
    S(FINALE + 40, 'eagle_descent'),
], LAST)

END_TEXT = os.environ.get('GO_TEXT', 'Are you go?')
END = [
    C('mocr_wait_2', END_AT - LAST),
    C('poll_film', 10.0, text=[(5.0, END_TEXT, 50, 0.84, 'serif')]),
]

SEQ = OPEN + WAIT + GO + FIN + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
    b = 0.0
    marks = {id(OPEN[0]): 'OPEN', id(WAIT[0]): 'BUILD', id(GO[0]): 'DROP', id(FIN[0]): 'FINALE', id(END[0]): 'END'}
    for s in SEQ:
        if id(s) in marks:
            print('%6.1f  %s' % (b, marks[id(s)]))
        if 'list' in sys.argv:
            src = s.get('clip') or s.get('photo') or ('SLOT ' + s['p']['desc'])
            print('   %6.2f  %5.2f  %s  in=%s' % (b, s['beats'], os.path.basename(src), s.get('in', '')))
        if s['beats'] <= 0:
            print('!! non-positive length at beat %.2f: %s' % (b, s))
        b += s['beats']
    print('total %.1f beats = %.1f s; missing: %s' % (b, b * BEAT, sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
