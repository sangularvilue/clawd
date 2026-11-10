"""GO. A 16:9, ~82 s film cut to Kanye West's "Stronger" (104 BPM).

The premise, in one sentence: this generation chooses the hard things, and every one of us is a station that
has to answer "Go."

The words: President Kennedy at Rice Stadium, 12 September 1962 ("But why, some say, the Moon?... We choose to
go to the Moon... not because they are easy, but because they are hard... one we are unwilling to postpone,
and one we intend to win"). What holds it together: the Mission Control go/no-go poll (from the film
"Apollo 13"): the flight director calls each station and every answer lands on a different American, waiting.
The same call closes the film, and nobody answers it: that station is the viewer.

The turn is WAIT -> GO, not then -> now. Before the drop everything is coiled and still (a sprinter settling
into her blocks, a surgeon's hands held up, a pilot's visor coming down, a rocket on the pad). On "because
they are hard" the hook drops and all of them go at once. Past and present are mixed and keep their own color.

Song bed (make_bed(); beats of the edit; only clean bars of the record are used, never the verses):
   0-9    cold open, no music: Kennedy asks why
   9-17   the two-bar vocoder intro: people waiting
  17-61   the dark bass passage from late in the record (bars 107-117), climbing: the poll, then Kennedy
  61-93   THE DROP: the first hook (bars 2-9); its last bar is the a-cappella break
  93-125  the last eight bars of the record (126-133); 125 is its final hit
 125-141  the room erupts; silence; the flight director asks again. End line: "Are you go?"
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
M0 = 9                           # edit beat of the bed's first downbeat
MUSIC_IN = M0 - PHASE / BEAT     # so the record's pick-up before the downbeat is kept
BUILD = B = M0 + 8               # 17  the bass passage starts
DROP = D = BUILD + 44            # 61  the hook
BREAK = DROP + 28                # 89  the a-cappella bar
FINALE = F = DROP + 32           # 93
LAST = L = FINALE + 32           # 125 the record's last hit
END_AT = LAST + 3.0              # 128 silence
LIMIT = 0.84
FX = dict(sat=1.0, chroma=3, shake=4, punch=0.04)

# ---------------------------------------------------------------- the song bed
# Record beats (4 per bar; bar b starts at PHASE + 4b beats): the intro (bars 0-1), the bass passage with its
# a-cappella lead-out (bars 107-117), hook 1 with its break (bars 2-9), the last eight bars (126-133) and the tail.
RAW = 'media/raw/go_song/stronger.flac'
SEGMENTS = [(None, 8, 0.0, 0.0), (428, 472, -7.0, -2.5), (8, 40, 0.0, 0.0), (504, None, 0.0, 0.0)]
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

# ---------------------------------------------------------------- the voices
# Kennedy: media/go_jfk_choose.m4a / .mp4 (one continuous piece, picture and sound in step). Phrases are
# (first word starts, last word ends), seconds into that file, from the word-level transcript in the log.
JFK = 'jfk_choose'
PH = dict(
    WHY=(0.30, 4.74),        # But why, some say, the Moon? Why choose this as our goal?
    CHOOSE=(26.91, 35.05),   # We choose to go to the Moon in this decade and do the other things, not because
                             # they are easy, but because they are hard,
    WIN=(47.09, 51.45),      # one we are unwilling to postpone, and one we intend to win,
    ROAR=(53.20, 57.20),     # the stadium, after it
)
# The poll: media/go_poll_film.m4a / .mp4 (the film's dialogue channel). (call starts, answer starts, answer ends)
ASK = (4.30, 5.96)           # "Give me a go/no-go for launch."
POLL = dict(Booster=(6.86, 7.38, 7.56), Retro=(7.98, 8.74, 8.92), FIDO=(9.10, 9.90, 10.42),
            Guidance=(10.50, 10.94, 11.36), Surgeon=(11.94, 12.58, 12.92), EECOM=(13.42, 14.38, 14.92),
            GNC=(15.14, 15.90, 16.20))
SAID = {}  # phrase -> (file key, source time of its first word, the beat that word lands on)


def say(key, ph, w0, w1, at, gain=1.25, duck=0.35, lead=0.1, tail=0.25):
    SAID[ph] = (key, w0, at)
    VOICEOVER.append(dict(file=media(key), at=at - lead / BEAT, src_in=w0 - lead, dur=w1 - w0 + lead + tail, gain=gain, duck=duck))


def jfk(ph, at, **kw):
    say(JFK, ph, PH[ph][0], PH[ph][1], at, **kw)


def answer(name, beat, gain=1.2, duck=0.4):
    """One call of the poll, placed so that its ANSWER lands on `beat`. Returns the beat the call starts on."""
    c0, a0, a1 = POLL[name]
    start = beat - (a0 - c0) / BEAT
    say('poll_film', name, c0, a1, start, gain=gain, duck=duck, lead=0.05, tail=0.06)
    return round(start, 2)


def W(ph, t):
    """The beat of the edit at which second t of a phrase's file is heard."""
    key, w0, at = SAID[ph]
    return round(at + (t - w0) / BEAT, 2)


def lips(ph, beat):
    """In-point that keeps the speaker's lips in step with phrase ph for a shot starting at `beat`."""
    key, w0, at = SAID[ph]
    return round(w0 + (beat - at) * BEAT, 3)


jfk('WHY', 0.5, duck=1.0)                         # cold open: "But why, some say, the Moon? Why choose this as our goal?"  (to 8.4)
say('poll_film', 'ASK', ASK[0], ASK[1], B + 0.6, gain=1.25, duck=0.5, lead=0.05, tail=0.15)   # "Give me a go/no-go for launch."
C_BOOSTER = answer('Booster', B + 5.0)            # each answer on a beat, each over someone waiting
C_RETRO = answer('Retro', B + 8.0)
C_FIDO = answer('FIDO', B + 11.5)
C_GUIDANCE = answer('Guidance', B + 15.0)
C_SURGEON = answer('Surgeon', B + 18.5)
C_EECOM = answer('EECOM', B + 22.0)
C_GNC = answer('GNC', B + 25.5)
jfk('CHOOSE', D - 0.08 - (PH['CHOOSE'][1] - PH['CHOOSE'][0]) / BEAT, gain=1.35, duck=0.4)   # "...because they are hard," ends on the drop
jfk('WIN', L - 0.4 - (PH['WIN'][1] - PH['WIN'][0]) / BEAT, gain=1.6, duck=0.42)            # "...and one we intend to win," ends on the last hit
jfk('ROAR', L + 0.1, gain=0.9, duck=1.0, lead=0.0, tail=0.0)                              # the stadium
say('poll_film', 'ASK2', ASK[0], ASK[1], END_AT + 1.6, gain=1.25, duck=1.0, lead=0.05, tail=0.2)   # he asks again; nobody answers

# ---------------------------------------------------------------- picture
JF = dict(sat=0.8)                                # the Rice film has faded toward magenta: pull it back a little


def J(start, ph):                                 # Kennedy on screen, in sync
    return S(start, JFK, fx=JF, **{'in': lips(ph, start)})


def K(start, ph):                                 # the flight director on screen, in sync
    return S(start, 'poll_film', **{'in': lips(ph, start)})


# ---- 0-9: cold open. Why?
OPEN = layout([
    J(0.0, 'WHY'),                                                 # "But why, some say, the Moon?"
    S(W('WHY', 2.95) - 0.3, 'hard', **{'in': 0.6}),                # "Why choose this as our goal?"  (Vanguard, December 1957)
], M0)

# ---- 9-17: the vocoder intro. People waiting for one word.
INTRO = layout([
    S(M0, 'mocr_wait_3'),                                          # 1969: hands clasped at his mouth
    S(M0 + 2.7, 'mach_wait_3', speed=0.8),                         # the Viper on its stand at dusk
    S(M0 + 5.4, 'mocr_wait_4'),                                    # a hand on his head
], B)

# ---- 17-61: the build. The poll: every answer over someone coiled. Then Kennedy.
WAIT = layout([
    K(B, 'ASK'),                                                   # "Give me a go/no-go for launch."
    S(C_BOOSTER, 'pad_wait'),                                      # "Booster!"  the F-1 bells, still        ... "Go!"
    S(C_RETRO, 'sprint_wait_2', **{'in': 2.1}),                    # "Retro!"    she settles into the blocks ... "Go!"
    S(C_FIDO, 'cat_wait_2'),                                       # "FIDO!"     a sailor's eyes on the deck ... "We're go, Flight."
    S(C_GUIDANCE, 'swim_wait'),                                    # "Guidance!" bent on the block           ... "Guidance go!"
    S(C_SURGEON, 'surgeon_wait'),                                  # "Surgeon!"  hands held up               ... "Go, Flight."
    S(C_EECOM, 'alert_wait_2'),                                    # "EECOM!"    the helmet goes on          ... "We're go, Flight."
    S(C_GNC, 'scramble_wait'),                                     # "GNC!"      the visor comes down        ... "We're go."
    S(B + 27.0, 'firing_wait'),                                    # the launch director, 2026, looks up
    J(W('CHOOSE', 26.91) - 0.25, 'CHOOSE'),                        # "We choose to go to the Moon"
    S(W('CHOOSE', 29.13), 'mocr_wait', **{'in': 0.2}),             # "in this decade"
    S(W('CHOOSE', 30.01), 'snap_wait'),                            # "and do the other things,"  (Notre Dame at the line)
    S(W('CHOOSE', 30.63), 'indy_wait', **{'in': 1.0}),             #                             (the pace lap)
    S(W('CHOOSE', 31.71) - 0.1, 'hard_2', **{'in': 0.5}),          # "not because they are easy,"  (it falls back onto the pad)
    S(W('CHOOSE', 33.51) - 0.1, 'hard_3', **{'in': 1.2}),          # "but because they are hard,"
], D)

# ---- 61-93: THE DROP. Everything goes at once.
FIRST = ([S(D, 'derby_go', fx=dict(punch=0.16, bloom=0.3)),      # the gate bursts
          S(D + 2, 'pad_go', fx=dict(bloom=0.3))]                # five engines light
         if _find('derby_go')[1] else
         [S(D, 'pad_go', fx=dict(punch=0.16, bloom=0.35), **{'in': 1.1}),   # five engines light (the starting gate goes here when it lands)
          S(D + 2.5, 'scramble_go_2')])                          # the takeoff roll
GO = layout(FIRST + [
    S(D + 4, 'sprint_go'),                                         # out of the blocks
    S(D + 5.5, 'cat_wait', **{'in': 0.5}),                         # the shooters touch the deck
    S(D + 6.5, 'cat_go'),                                          # and the jet is gone
    S(D + 7.5, 'scramble_go'),                                     # the burner lights
    S(D + 9, 'mach_go'),                                           # ignition; the smoke ring
    S(D + 11, 'alert_go'),                                         # across the bay to the engine
    S(D + 12.5, 'alert_go_2'),                                     # rolling, every light on
    S(D + 14, 'surgeon_go'),                                       # the instrument hits the palm
    S(D + 15.5, 'indy_go'),                                        # thirty-three cars to the green
    S(D + 17, 'launch_go_3', **{'in': 1.3}),                       # Artemis II climbs past the camera
    S(D + 19.5, 'walkout_2026', **{'in': 1.3}),                    # the crew, striding out
    S(D + 22, 'mocr_go_2'),                                        # binoculars up at the windows
    S(D + 23.5, 'snap_go', alt=[('sprint_go', 1.7)]),              # Notre Dame: the snap, the line fires out
    S(D + 25, 'cat_go', **{'in': 0.7}),                            # the deck crew watch it go off the bow
    S(D + 26.5, 'drag_go', **{'in': 3.0}),
    S(BREAK, 'walkout_1969', **{'in': 1.6}),                       # the a-cappella bar: July 1969, a wave
], F)

# ---- 93-125: the last eight bars. Bigger; then wait/go pairs at half a beat; then Kennedy and the landing.
FIN = layout([
    S(F, 'launch_go_2', fx=dict(bloom=0.35, punch=0.14)),          # Artemis II, the boosters light
    S(F + 3, 'firing_go', **{'in': 0.3}),                          # the launch director throws her arms wide
    S(F + 5.5, 'staging'),                                         # the ring falls away to the Earth
    S(F + 8.5, 'scramble_go_2'),                                   # the takeoff roll
    S(F + 10, 'mach_go', **{'in': 1.9}),                           # climbing out of frame
    S(F + 12, 'surgeon_go_2'),                                     # the team at the table
    S(F + 14, 'alert_go', **{'in': 1.6}),                          # aboard
], F + 16)


def pairs(*rows):
    """Wait, go, wait, go: half a beat each."""
    out = []
    for k in rows:
        k = (k,) if isinstance(k, str) else k
        it = C(k[0], 0.5, **({'in': k[1]} if len(k) > 1 else {}))
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=8)
        out.append(it)
    return out


STROBE = pairs(('sprint_wait', 1.0), ('sprint_go', 0.3), ('cat_wait_2', 0.5), ('cat_go', 0.1),
               ('surgeon_wait_2', 1.0), ('surgeon_go', 0.5), ('alert_wait', 0.5), ('alert_go_2', 0.8),
               ('scramble_wait', 1.2), ('scramble_go', 0.3), ('mach_wait', 0.3), ('mach_go', 0.1),
               ('firing_wait_2', 1.0), ('firing_go', 0.6), ('pad_wait', 3.3), ('pad_go', 1.5))

CLOSE = layout([
    S(F + 24, 'launch_go', speed=1.0),                             # "one we are unwilling to postpone,"
    S(W('WIN', 49.65) - 0.4, 'eagle_descent', fx=dict(bloom=0.25), **{'in': 2.0}),   # "and one we intend to"  (the shadow meets the Moon)
    S(W('WIN', 51.21) - 0.15, 'mocr_go', fx=dict(punch=0.12)),     # "win,"  the room erupts, July 1969
], END_AT)

# ---- silence. He asks again. A rocket on the pad; the first glow under it as we stop.
END_TEXT = os.environ.get('GO_TEXT', 'Are you go?')
END = layout([
    K(END_AT, 'ASK2'),
    S(END_AT + 5.5, 'pad_wait', speed=0.6, dim=0.22, fx=dict(punch=0.0, shake=0), text=[(3.0, END_TEXT, 68, 0.5, 'serif')], **{'in': 1.2}),
], END_AT + 13.5)

SEQ = OPEN + INTRO + WAIT + GO + FIN + STROBE + CLOSE + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
    b = 0.0
    marks = {id(OPEN[0]): 'OPEN', id(INTRO[0]): 'INTRO', id(WAIT[0]): 'BUILD', id(GO[0]): 'DROP', id(FIN[0]): 'FINALE',
             id(STROBE[0]): 'STROBE', id(CLOSE[0]): 'CLOSE', id(END[0]): 'END'}
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
