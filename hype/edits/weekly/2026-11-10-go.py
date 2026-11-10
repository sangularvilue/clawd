"""GO. A 16:9, ~81 s film cut to Kanye West's "Stronger" (104 BPM).

The premise, in one sentence: this generation chooses the hard things, and every one of us is a station that
has to answer "Go."

It runs as one line of thought over one continuous build (the first cut interleaved Kennedy, the record's
vocoder and the poll, and the opening came out disjointed):
  1. Kennedy at Rice Stadium, 12 September 1962, says his piece in one go: "But why, some say, the Moon? Why
     choose this as our goal? ... We choose to go to the Moon in this decade and do the other things, not
     because they are easy, but because they are hard."
  2. The roll call: the Mission Control go/no-go poll (from the film "Apollo 13"). The flight director calls
     each station and every answer lands on a different American, waiting. "We are go for launch" ends on the drop.
  3. THE DROP: everything that was coiled goes at once (WAIT -> GO is the film's turn; past and present are mixed).
  4. The last eight bars end on Kennedy's "one we are unwilling to postpone, and one we intend to win."
  5. Silence. The flight director asks again, and nobody answers: that station is the viewer. "Are you go?"
(The starting-gate shots are from the film "Secretariat": no clean footage of a real Derby break was found.)

Song bed (make_bed(); beats of the edit; only clean bars of the record are used, never the verses):
   0-60   the dark bass passage from late in the record (bars 107-113, then 110-117), climbing 7 dB from the
          first frame to the drop with no break; its last bar is the a-cappella lull
  60-92   THE DROP: the first hook (bars 2-9); its last bar is the a-cappella break
  92-124  the last eight bars of the record (126-133); 124 is its final hit
 124-140  the room erupts; silence; the flight director asks again. End line: "Are you go?"
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
MUSIC_IN = 0.0                   # the bed starts on the film's first frame
DROP = D = 60                    # the hook
BREAK = DROP + 28                # 88  the a-cappella bar
FINALE = F = DROP + 32           # 92
LAST = L = FINALE + 32           # 124 the record's last hit
END_AT = LAST + 3.0              # 127 silence
LIMIT = 0.84
FX = dict(sat=1.0, chroma=3, shake=4, punch=0.04)

# ---------------------------------------------------------------- the song bed
# Record beats (4 per bar; bar b starts at PHASE + 4b beats): the bass passage (bars 107-113), its four-bar phrase
# again and its a-cappella lead-out (bars 110-117), hook 1 with its break (bars 2-9), the last eight bars (126-133)
# and the tail.
RAW = 'media/raw/go_song/stronger.flac'
SEGMENTS = [(428, 456, -9.5, -5.8), (440, 472, -5.8, -2.0), (8, 40, 0.0, 0.0), (504, None, 0.0, 0.0)]
# (from, to) in record beats, None = end of file; then gain in dB at the segment's start and end: the bass passage
# is nearly as loud as the hook on the record, so it starts well down and climbs, and the drop has somewhere to go


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


LAUNCH = (28.70, 31.46)      # "Launch Control, this is Houston. We are go for launch."
jfk('WHY', 0.5, duck=0.5)                         # "But why, some say, the Moon? Why choose this as our goal?"  (to 8.5)
jfk('CHOOSE', 24.0 - 0.05 - (PH['CHOOSE'][1] - PH['CHOOSE'][0]) / BEAT, gain=1.3, duck=0.45)   # "We choose to go to the Moon ... because they are hard," ends on bar 7
say('poll_film', 'ASK', ASK[0], ASK[1], 24.7, gain=1.25, duck=0.5, lead=0.05, tail=0.15)       # "Give me a go/no-go for launch."
C_BOOSTER = answer('Booster', 30.0)               # the roll call: each answer on a beat, each over someone waiting
C_RETRO = answer('Retro', 33.0)
C_FIDO = answer('FIDO', 36.0)
C_GUIDANCE = answer('Guidance', 39.0)
C_SURGEON = answer('Surgeon', 42.0)
C_EECOM = answer('EECOM', 45.0)
C_GNC = answer('GNC', 48.0)
say('poll_film', 'LAUNCH', LAUNCH[0], LAUNCH[1], D - 0.1 - (LAUNCH[1] - LAUNCH[0]) / BEAT, gain=1.35, duck=0.45, lead=0.05, tail=0.1)   # "...We are go for launch." ends on the drop
jfk('WIN', L - 0.4 - (PH['WIN'][1] - PH['WIN'][0]) / BEAT, gain=1.6, duck=0.42)            # "...and one we intend to win," ends on the last hit
jfk('ROAR', L + 0.1, gain=0.9, duck=1.0, lead=0.0, tail=0.0)                              # the stadium
say('poll_film', 'ASK2', ASK[0], ASK[1], END_AT + 1.6, gain=1.25, duck=1.0, lead=0.05, tail=0.2)   # he asks again; nobody answers

# ---------------------------------------------------------------- picture
JF = dict(sat=0.8)                                # the Rice film has faded toward magenta: pull it back a little


def J(start, ph):                                 # Kennedy on screen, in sync
    return S(start, JFK, fx=JF, **{'in': lips(ph, start)})


def K(start, ph):                                 # the flight director on screen, in sync
    return S(start, 'poll_film', **{'in': lips(ph, start)})


# ---- 0-24: Kennedy, in one go. The bass comes in under his first words.
OPEN = layout([
    J(0.0, 'WHY'),                                                 # "But why, some say, the Moon?"
    S(W('WHY', 2.95) - 0.3, 'hard', **{'in': 0.6}),                # "Why choose this as our goal?"  (Vanguard, December 1957)
    J(W('CHOOSE', 26.91) - 0.3, 'CHOOSE'),                         # "We choose to go to the Moon"
    S(W('CHOOSE', 29.13), 'mocr_wait', **{'in': 0.2}),             # "in this decade"
    S(W('CHOOSE', 30.01), 'snap_wait'),                            # "and do the other things,"  (Notre Dame at the line)
    S(W('CHOOSE', 30.63), 'indy_wait', **{'in': 1.0}),             #                             (the pace lap)
    S(W('CHOOSE', 31.71) - 0.1, 'hard_2', **{'in': 0.5}),          # "not because they are easy,"  (it falls back onto the pad)
    S(W('CHOOSE', 33.51) - 0.1, 'hard_3', **{'in': 1.2}),          # "but because they are hard,"
], 24.0)

# ---- 24-60: the roll call. Every answer over someone coiled; then "we are go for launch" into the drop.
WAIT = layout([
    K(24.0, 'ASK'),                                                # "Give me a go/no-go for launch."
    S(C_BOOSTER, 'pad_wait'),                                      # "Booster!"  the F-1 bells, still        ... "Go!"
    S(C_RETRO, 'sprint_wait_2', **{'in': 2.1}),                    # "Retro!"    she settles into the blocks ... "Go!"
    S(C_FIDO, 'cat_wait_2'),                                       # "FIDO!"     a sailor's eyes on the deck ... "We're go, Flight."
    S(C_GUIDANCE, 'swim_wait'),                                    # "Guidance!" bent on the block           ... "Guidance go!"
    S(C_SURGEON, 'surgeon_wait'),                                  # "Surgeon!"  hands held up               ... "Go, Flight."
    S(C_EECOM, 'alert_wait_2'),                                    # "EECOM!"    the helmet goes on          ... "We're go, Flight."
    S(C_GNC, 'scramble_wait'),                                     # "GNC!"      the visor comes down        ... "We're go."
    S(49.0, 'derby_wait_2', alt=[('mocr_wait_4', 0.0)], **{'in': 0.6}),   # the music thins: a jockey in the gate lifts his eyes
    S(50.6, 'firing_wait'),                                        # the launch director, 2026, looks up
    S(52.2, 'mach_wait_3', speed=0.8),                             # the Viper on its stand at dusk
    S(53.8, 'derby_wait_3', alt=[('mocr_wait_3', 0.0)]),           # the horse's eye through the bars
    K(W('LAUNCH', 28.70) - 0.2, 'LAUNCH'),                         # "Launch Control, this is Houston. We are go for launch."
], D)

# ---- 60-92: THE DROP. Everything goes at once.
FIRST = ([S(D, 'derby_go', fx=dict(punch=0.16, bloom=0.3)),      # the gate bursts
          S(D + 2, 'pad_go', fx=dict(bloom=0.3), **{'in': 1.0})]   # five engines light
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
    S(D + 22, 'rodeo_go', alt=[('mocr_go_2', 0.0)]),               # the chute gate swings and the bronc is out
    S(D + 23.5, 'snap_go', alt=[('sprint_go', 1.7)]),              # Notre Dame: the snap, the line fires out
    S(D + 25, 'derby_go_2', alt=[('cat_go', 0.7)]),                # the whole field, a length out of the gate
    S(D + 26.5, 'drag_go_2', alt=[('drag_go', 3.0)]),              # two Top Fuel cars leave in a fireball
    S(BREAK, 'walkout_1969', **{'in': 1.6}),                       # the a-cappella bar: July 1969, a wave
], F)

# ---- 92-124: the last eight bars. Bigger; then wait/go pairs at half a beat; then Kennedy and the landing.
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


STROBE = pairs(('sprint_wait', 1.0), ('sprint_go', 0.3), ('derby_wait', 1.0), ('derby_go', 0.25),
               ('surgeon_wait_2', 1.0), ('surgeon_go', 0.5), ('alert_wait', 0.5), ('alert_go_2', 0.8),
               ('scramble_wait', 1.2), ('scramble_go', 0.3), ('mach_wait', 0.3), ('mach_go', 0.1),
               ('rodeo_wait', 1.0), ('rodeo_go', 0.15), ('pad_wait', 3.3), ('pad_go', 1.5))

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

SEQ = OPEN + WAIT + GO + FIN + STROBE + CLOSE + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
    b = 0.0
    marks = {id(OPEN[0]): 'KENNEDY', id(WAIT[0]): 'ROLL CALL', id(GO[0]): 'DROP', id(FIN[0]): 'FINALE',
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
