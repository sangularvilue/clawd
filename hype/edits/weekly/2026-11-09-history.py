"""HISTORY WILL ASK. A 16:9, ~94 s film cut to Sabaton's "Soldier of Heaven" (our pipe-organ version).

The premise, in one sentence: history is asking this generation of Americans the same three questions it asked
every generation before it, and the answer decides "the fate of freedom for a thousand years".

The words are from the close of Reagan's commencement address at Notre Dame, 17 May 1981 (National Archives
tape). Only the spine of the passage is used (mockup 1 ran the whole thing and it was too much talk):
  "But history will ask, and our answer determines the fate of freedom for a thousand years:
   Did a nation born of hope lose hope?
   Did a people forged by courage find courage wanting?
   Did a generation steeled by hard war and a harsh peace forsake honor?"
and, over the last chord: "And now, they're yours to protect and pass on."
From the drop to the last chord nobody speaks: the music and the pictures answer.

The motif is a BELL: history asking. It tolls after each question; each question is answered, in black and
white, by the generation it was put to (the Depression's builders, the men on the ramp, the Moon and the Wall).
At the drop the picture turns to color and the bell is ours: today's Americans going when it rings. The last
bars set then against now, shot for shot (the ironworkers' heave / the wall going up, the ramp / the fire
crew, the flag on the Moon / Artemis). On the last chord every bell rings and Reagan hands it over. Then
silence, one toll, and two children's white-gloved hands at the Liberty Bell; we stop before they touch it.
End line: "History is asking."

Every clip is new to this film (review.py flags anything an earlier edit used).

Song bed (make_bed(); 96 BPM; beats of the edit, the music enters at beat 12 after a cold open):
  12-28 the synth intro and drum fill, 28-44 half of verse 1, 44-60 the pre-chorus, no singer, all lo-fi;
  60 chorus 3 at full fidelity with the organ on the vocal line; 92 the key change, full organ;
  124 the final chord; 132 the organ lets go; 136-150 silence and the last toll.
Run `python3 edits/weekly/2026-11-09-history.py bed bell` once to build the bed, the tuned bells and the last shot.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'w1109_'
BPM = 96.0
BEAT = 60 / BPM
SONG_VERSION = os.environ.get('HIST_SONG', 'organ')  # organ | vocals (Sabaton sings the choruses)
SONG = 'media/w1109_bed_soh_%s.wav' % SONG_VERSION
SONG_START = 0.0
MUSIC_IN = M = 12            # cold open: the bell and Reagan's thesis in silence
DRUMS = M + 16               # 28  the drums come in (verse 1)
PRE = M + 32                 # 44  the pre-chorus starts to climb
DIP = M + 44                 # 56  the bar before the chorus
DROP = M + 48                # 60  chorus 3: color, full fidelity, the organ
LIFT = DROP + 32             # 92  the key change, organ tutti
CHORD = DROP + 64            # 124 the final chord
RELEASE = DROP + 72          # 132 the organ lets go
LOFI = dict(until=DROP, cutoff=2300, hp=170)
LIMIT = 0.94                 # master limiter on the finished mix
FX = dict(sat=0.0, chroma=3, shake=4, punch=0.04)  # black and white unless a shot says otherwise
COLOR = dict(sat=1.05)

# ---------------------------------------------------------------- the song bed
# Recording beats of Soldier of Heaven (grid phase 0.085 s; bar N starts at 1 + 4(N-1) + the 5/4 bars before it):
# bars 1-8 (rec beats 1-33: intro, drum fill, half of verse 1) and bars 13-16 (51-67, the pre-chorus) from the
# instrumental stems, then straight to chorus 3 (bar 63, rec beat 255), the key-change chorus (287) and the final
# chord (319) of the organ mix Will approved ("Soldier of Heaven (organ) - backing track for Nov 9 video", the
# one with the shorter ending).
BED_PHASE = 0.085
MASTER = 10 ** (-2.5 / 20)   # the organ mix was mastered 2.5 dB down; the bare stems are matched to it
BEDS = {
    'organ': dict(segments=[('out/soh_score_organ_v3.backing.wav', 1, 33, MASTER), ('out/soh_score_organ_v3.backing.wav', 51, 67, MASTER),
                            ('out/soh_organ_short.wav', 255, None, 1.0)], end=207.84, fade=1.7),
    'vocals': dict(segments=[('out/soh_score_organ_v3.backing.wav', 1, 33, 1.0), ('out/soh_score_organ_v3.backing.wav', 51, 67, 1.0),
                             ('media/raw/organ_soh/soh.mp3', 255, None, 1.0)], end=207.84, fade=1.7),
}


def _read(path):
    import soundfile as sf
    full = os.path.join(HERE, path)
    if full.endswith('.mp3'):
        tmp = os.path.join(HERE, 'media', 'raw', 'w1109_bed_tmp.wav')
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', full, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_f32le', tmp], check=True)
        x = sf.read(tmp, dtype='float32')[0]
        os.remove(tmp)
        return x
    return sf.read(full, dtype='float32')[0]


def make_bed(version=SONG_VERSION, xfade=0.03):
    import numpy as np
    import soundfile as sf
    cfg, sr = BEDS[version], 44100
    t = lambda rb: BED_PHASE + rb * BEAT
    nx = int(xfade * sr)
    ramp = np.linspace(0, 1, nx)[:, None]
    y = None
    for path, a, b, g in cfg['segments']:
        x = _read(path) * g
        i0 = int(round(t(a) * sr))
        i1 = int(round((t(b) if b is not None else cfg['end']) * sr))
        seg = x[i0:min(len(x), i1)]
        if y is None:
            y = seg
        else:  # the outgoing segment fades out over the incoming one's last moments before its bar line
            y = np.concatenate([y[:-nx], y[-nx:] * (1 - ramp) + x[i0 - nx:i0] * ramp, seg])
    nf = int(cfg['fade'] * sr)
    y[-nf:] *= np.linspace(1, 0, nf)[:, None] ** 2
    pk = np.abs(y).max()
    if pk > 0.98:
        y = y * (0.98 / pk)
    sf.write(os.path.join(HERE, 'media', 'w1109_bed_soh_%s.wav' % version), y, sr, subtype='PCM_24')
    return len(y) / sr


# ---------------------------------------------------------------- the bell
# One bell all the way through: media/w1109_bell_toll.m4a, a big tower bell whose strike note is F (prime 347 Hz,
# hum 170, minor-third tierce 410, quint 523). It is re-pitched by plain resampling (no artifacts; a lower bell
# rings longer, as a bigger bell would) so it sits in the song's key: E for the verse and chorus 3 (A minor: the
# bell's E-G-B over it), C after the key change (C minor: its C-E flat-G is the chord itself).
# The peal on the final chord is media/w1109_bells_peal.m4a (Wittmund; its bells centre on a flat E), lowered so
# they fall on C minor's notes. If the recordings are missing, a synthesized tower bell stands in.
def _rate(path):
    return int(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate',
                               '-of', 'csv=p=0', path], capture_output=True, text=True, check=True).stdout.strip())


def make_bells():
    real = os.path.join(HERE, media('bell_toll'))
    for name, hz, dur in (('bell_e', 329.63, 14.0), ('bell_c', 261.63, 16.0)):
        out = os.path.join(HERE, media(name, '.wav'))
        if os.path.exists(real):
            sr = _rate(real)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', real, '-af',
                            'asetrate=%d,aresample=44100,afade=t=out:st=%f:d=4' % (round(sr * hz / 347.0), dur - 4),
                            '-t', str(dur), '-ac', '2', '-c:a', 'pcm_s24le', out], check=True)
        else:
            make_bell(hz / 2, name)
    peal = os.path.join(HERE, media('bells_peal'))
    if os.path.exists(peal):
        sr = _rate(peal)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', peal, '-af',
                        'asetrate=%d,aresample=44100,afade=t=in:d=0.04,afade=t=out:st=2.2:d=4.3' % round(sr * 2 ** (-3.65 / 12)),
                        '-t', '6.5', '-ac', '2', '-c:a', 'pcm_s24le', os.path.join(HERE, media('bells_c', '.wav'))], check=True)


# The ending: two children's white-gloved hands at the Liberty Bell (the 4 July "Let Freedom Ring" tapping, the
# crack between them). The girl's hand lifts off the bell and starts back toward it; we slow that to a fifth of
# its speed and stop on the frame before it lands.
def make_reach(t0=0.80, t1=1.32, slow=5.0, hold=6.0):
    src = os.path.join(HERE, media('liberty_bell_tap', '.mp4'))
    if not os.path.exists(src):
        return
    # the newscast picture is a 640x280 strip: kept whole, letterboxed, so the end line can sit in the bar under it
    vf = ('trim=%f:%f,setpts=%f*(PTS-STARTPTS),minterpolate=fps=30:mi_mode=blend,'
          'tpad=stop_mode=clone:stop_duration=%f,scale=1280:560:flags=lanczos,unsharp=5:5:0.5,'
          'pad=1280:720:0:80:black' % (t0, t1, slow, hold))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', vf, '-an', '-c:v', 'libx264', '-crf', '14',
                    '-pix_fmt', 'yuv420p', os.path.join(HERE, media('bell_reach', '.mp4'))], check=True)


def make_bell(note_hz, name, dur=9.0, seed=7):
    import sys
    import numpy as np
    import soundfile as sf
    sys.path.insert(0, HERE)
    sr = 44100
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    tt = np.arange(n) / sr
    #          ratio  amp   decay (s)
    partials = [(0.5, 0.60, 6.0), (1.0, 0.80, 3.6), (1.189, 0.62, 2.7), (1.5, 0.24, 1.8), (2.0, 1.00, 1.7),
                (2.51, 0.30, 1.0), (2.66, 0.22, 0.85), (3.01, 0.42, 0.75), (4.1, 0.30, 0.5), (5.43, 0.18, 0.32),
                (6.8, 0.12, 0.24), (8.3, 0.08, 0.16), (10.1, 0.05, 0.1)]
    y = np.zeros((n, 2), np.float32)
    for r, amp, tau in partials:
        f = note_hz * r
        for ch in (0, 1):
            beat_hz = rng.uniform(0.15, 0.6) * (1 + r / 4)
            a = np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28))
            b = np.sin(2 * np.pi * (f + beat_hz) * tt + rng.uniform(0, 6.28))
            y[:, ch] += (amp * np.exp(-tt / tau) * (0.62 * a + 0.38 * b)).astype(np.float32)
    # the clapper: a few ms of bright noise and a dull thud
    k = int(0.03 * sr)
    noise = rng.standard_normal((k, 2)) * np.exp(-np.arange(k) / (0.004 * sr))[:, None]
    y[:k] += (0.5 * (noise - np.roll(noise, 3, 0))).astype(np.float32)
    att = int(0.002 * sr)
    y[:att] *= np.linspace(0, 1, att)[:, None]
    y[-int(0.5 * sr):] *= np.linspace(1, 0, int(0.5 * sr))[:, None]
    try:  # a little stone room around it
        import organ
        wet = organ.cathedral(y.T.copy(), rt60=4.0, wet=1.0, hp=200.0).T
        y = y + 0.22 * wet[:n] / max(1e-9, np.abs(wet).max()) * np.abs(y).max()
    except Exception as e:  # the dry bell is fine too
        print('bell reverb skipped:', e)
    y *= 0.9 / np.abs(y).max()
    sf.write(os.path.join(HERE, 'media', P + name + '.wav'), y, sr, subtype='PCM_24')


# ---------------------------------------------------------------- footage
def _find(key):
    for name in ((key[1:],) if key.startswith('/') else (P + key, key)):  # this week's media, else an earlier week's clip by its full name ('/name' = exactly that file)
        for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
            path = os.path.join(HERE, 'media', name + ext)
            if os.path.exists(path):
                return kind, path
    return None, None


def C(key, beats, alt=None, **kw):
    """Footage from media/w1109_<key>.*; else the first alternate that exists (alt = key or (key, in) or
    (key, in, crop) or a list of them), else a labeled card."""
    kind, path = _find(key)
    for a in ([alt] if isinstance(alt, (str, tuple)) else alt or []) if not path else []:
        a = (a,) if isinstance(a, str) else a
        kind, path = _find(a[0])
        if path:
            kw.pop('in', None), kw.pop('crop', None), kw.pop('speed', None)
            if len(a) > 1 and a[1] is not None:
                kw['in'] = a[1]
            if len(a) > 2:
                kw['crop'] = a[2]
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


def _dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None


def media(key, ext='.m4a'):
    return 'media/' + P + key + ext


def have(key, ext='.m4a'):
    return os.path.exists(os.path.join(HERE, media(key, ext)))


# ---------------------------------------------------------------- the voice: Reagan, Notre Dame, 17 May 1981
# media/w1109_r81_history.m4a / .mp4 hold the whole passage (62.6 s; picture and sound in step). Each phrase is
# (first word starts, last word ends), seconds into that file, from the word-level transcript.
R81 = 'r81_history'
RCROP = (0.17, 0.03, 0.70, 0.525)   # medium close-up of Reagan at the lectern out of the 4:3 tape
YOURS = 'r81_yours'                 # "...And now, they're yours to protect and pass on."  (words 6.28-9.60 of its file)
PH = dict(
    A=(6.50, 7.62),      # But history will ask,
    B=(8.44, 11.96),     # and our answer determines the fate of freedom for a thousand years.
    Q1=(13.28, 15.94),   # Did a nation born of hope lose hope?
    Q2=(16.70, 20.10),   # Did a people forged by courage find courage wanting?
    Q3=(21.06, 25.66),   # Did a generation steeled by hard war and a harsh peace forsake honor
                         # (he goes on "...at the moment of great climactic struggle for the human spirit?" after a
                         #  0.75 s pause; the cut is in that pause)
)
PH['Y'] = (6.28, 9.60)              # And now, they're yours / to protect / and pass on.   (in r81_yours)
FILE = {'Y': YOURS}                 # phrases that live in another file
VOICEOVER = []
SAID = {}  # phrase -> the beat its first word lands on


def say(ph, at, gain=1.0, duck=0.4, lead=0.12, tail=0.28):
    w0, w1 = PH[ph]
    SAID[ph] = at
    VOICEOVER.append(dict(file=media(FILE.get(ph, R81)), at=at - lead / BEAT, src_in=w0 - lead, dur=w1 - w0 + lead + tail,
                          gain=gain, duck=duck))


def at(ph, t):
    """The beat of the edit at which second t of the Reagan file is heard (for word-to-picture cuts)."""
    return round(SAID[ph] + (t - PH[ph][0]) / BEAT, 2)


def lips(ph, beat):
    """In-point of the Reagan clip that keeps his lips in step with phrase ph for a shot starting at `beat`."""
    return round(PH[ph][0] + (beat - SAID[ph]) * BEAT, 3)


TOLLS = []


def toll(beat, note='e', gain=0.9, duck=0.8, dur=5.0, fade=3.0):
    """History asks: one strike of the bell (media/w1109_bell_e.wav in the verse's key, _c after the key change).
    The voice lines are added after the tolls, so wherever a line overlaps a toll the line's duck wins."""
    f = media('bell_' + note, '.wav')
    if os.path.exists(os.path.join(HERE, f)):
        VOICEOVER.append(dict(file=f, at=beat, src_in=0.0, dur=dur, gain=gain, duck=duck, fade=min(fade, dur)))
    TOLLS.append(beat)


toll(0.15, dur=4.5, fade=3.2, duck=1.0)      # the bell, in silence
say('A', 2.5, duck=1.0)                      # "But history will ask,"                                  (to 4.3)
toll(4.6, dur=4.5, fade=3.4, duck=1.0)
say('B', 6.4, duck=1.0)                      # "and our answer determines the fate of freedom for a thousand years."  (to 12.0)
say('Q1', 13.0)                              # "Did a nation born of hope lose hope?"                   (to 17.3)
toll(17.45, gain=0.85, dur=5.0)
say('Q2', 22.6)                              # "Did a people forged by courage find courage wanting?"   (to 28.0; the drum fill under "find courage wanting")
toll(DRUMS + 0.05, gain=0.85, dur=5.0)       # ... and the drums answer
say('Q3', 34.6, tail=0.2)                    # "Did a generation steeled by hard war and a harsh peace forsake honor?"  (to 42.0)
toll(42.2, gain=0.85, dur=5.0)
toll(DIP, gain=0.9, dur=2.6, fade=2.2)       # the bar before the drop: the bell alone
toll(DROP, gain=0.6, duck=1.0, dur=5.0)      # the drop: the bell is ours now
toll(LIFT, note='c', gain=0.55, duck=1.0, dur=5.0)
toll(CHORD, note='c', gain=0.6, duck=1.0, dur=3.2, fade=2.6)
if have('bells_c', '.wav'):                  # ... and every bell rings with it, then makes room for the voice
    VOICEOVER.append(dict(file=media('bells_c', '.wav'), at=CHORD + 0.1, src_in=0.0, dur=6.5, gain=0.42, duck=1.0, fade=0.1))
if have(YOURS):                              # the handoff, over the held chord: "pass on" lands as the organ lets go
    say('Y', CHORD + 4.4, gain=1.35, duck=0.38, tail=0.35)  # "And now, they're yours ... to protect ... and pass on."
END_AT = RELEASE + 4.0                       # 136: the organ has let go; the last shots
END_LEN = 14.0                               # beats: the toll rings out inside them
toll(END_AT + 0.5, note='c', gain=1.0, duck=1.0, dur=(END_LEN - 0.9) * BEAT, fade=5.0)   # one toll, in silence

# ---------------------------------------------------------------- picture
OLD = dict(sat=0.0)   # stays black and white after the drop (the generations before us)


def S(start, key, alt=None, **kw):
    """A shot that starts on an absolute beat of the edit; layout() gives it its length."""
    return dict(_at=start, _key=key, _alt=alt, **kw)


def layout(rows, end):
    out = []
    for i, r in enumerate(rows):
        r = dict(r)
        start, key, alt = r.pop('_at'), r.pop('_key'), r.pop('_alt')
        nxt = rows[i + 1]['_at'] if i + 1 < len(rows) else end
        ph = r.pop('lips', None)
        if ph:  # Reagan on screen, in sync
            r.update({'in': lips(ph, start), 'crop': RCROP})
            key = FILE.get(ph, R81)
        out.append(C(key, round(nxt - start, 3), alt, **r))
    return out


W = lambda ph, t: at(ph, t)  # the beat a word lands on

# ---- 0-12: cold open. The bell; the thesis, in silence.
OPEN = layout([
    S(0.0, 'liberty_bell', speed=0.7),                                        # toll: the Liberty Bell, the crack
    S(2.3, R81, lips='A'),                                                    # "But history will ask,"
    S(4.5, 'liberty_bell_2', speed=0.5),                                      # toll: the bell on its pedestal, 1925
    S(6.25, R81, lips='B'),                                                   # "and our answer determines the fate of freedom"
    S(W('B', 10.94), 'valley', fit='cover', zoom=(1.0, 1.08), center=(0.42, 0.42)),  # "for a thousand years."  (Washington crossing the Delaware)
], M)

# ---- 12-60: the three questions, each answered by the generation it was put to. Lo-fi; drums at 28.
VERSE = layout([
    S(12.0, 'hope_born'),                                                     # "Did a nation"  (immigrants crowd the rail, waving, as the ship comes in)
    S(W('Q1', 13.86), 'hope_born_2'),                                         # "born of hope"  (a mother in a shawl beams at her baby)
    S(W('Q1', 15.00), 'breadline'),                                           # "lose hope?"    (the bread line, 1930)
    S(17.4, 'dust_bowl', **{'in': 2.0}),                                      # toll: the farmer leans into the dust
    S(19.2, 'hope_answer'),                                                   # the answer: they built (the Empire State's steel, 1930)
    S(20.9, 'hope_answer_2'),
    S(22.5, 'forged'),                                                        # "Did a people forged by courage"  (the ladle, the sparks)
    S(W('Q2', 18.48), 'pearl_harbor'),                                        # "find courage wanting?"  (Battleship Row)
    S(DRUMS, 'go_ramp', fx=dict(punch=0.1)),                                  # toll + drums: the ramp drops and they go
    S(30.0, 'bastogne'),                                                      # the Ardennes: digging the ammunition out of the snow
    S(31.5, 'go_ramp_2', **{'in': 0.6}),                                      # down the gangway
    S(33.0, 'bastogne', **{'in': 2.3}),                                       # bent into the blizzard
    S(34.5, R81, lips='Q3'),                                                  # "Did a generation steeled by"
    S(W('Q3', 22.60), 'bastogne_2'),                                          # "hard war"
    S(W('Q3', 23.26), 'go_miners'),                                           # "and a harsh peace"  (the shift rolls into the mine)
    S(W('Q3', 24.20), 'apollo13'),                                            # "forsake honor?"  (Mission Control, April 1970) ... toll
    S(43.0, 'apollo11', **{'in': 0.3}),                                       # the answer: the flag goes up on the Moon
    S(46.5, 'spirit_answer'),                                                 # on top of the Wall, 9 November 1989
    S(49.0, 'spirit_answer_2', **{'in': 0.15}),                               # a hammer and a chisel
    S(50.5, 'hope_answer_2', **{'in': 1.5}),                                  # the answers, once more, faster as the music climbs
    S(51.5, 'forged_2', **{'in': 1.4}),
    S(52.5, 'go_ramp', **{'in': 1.6}),
    S(53.5, 'go_ramp_2', **{'in': 2.2}),
    S(54.5, 'spirit_answer', **{'in': 2.2}),
    S(DIP, 'liberty_bell', speed=0.55, fx=dict(punch=0.0), **{'in': 0.3}),    # toll: the bell, alone
], DROP)

# ---- 60-92: THE DROP. Color; the organ; nobody speaks. The bell is ours: they go when it rings.
CHORUS = layout([
    S(DROP, 'bell_town_2', alt=[('flight_deck_3', 0.0)], fx=dict(punch=0.14, bloom=0.3), **{'in': 0.8}),  # a town's bell swinging on the Fourth of July, 2026, in color: ours now
    S(61.0, 'flight_deck_2', fx=dict(punch=0.1), **{'in': 1.35}),             # and the jet goes
    S(63.0, 'flight_deck', **{'in': 1.6}),                                    # the yellow shirt signals through the steam
    S(64.0, 'young_welder_2'),                                                # she looks at us, snaps the hood down, strikes the arc
    S(67.0, 'young_welder', **{'in': 0.5}),
    S(68.0, 'fire_crew'),                                                     # going in together
    S(69.5, 'fire_crew_2'),                                                   # the line holds
    S(70.5, 'build_crew'),                                                    # the wall goes up
    S(72.0, 'linemen'),                                                       # setting the pole
    S(73.0, 'surgical_team'),                                                 # the team at the table
    S(74.0, 'relay_handoff_2'),                                               # the baton
    S(76.0, 'huddle_hands', **{'in': 1.3}),                                   # the break
    S(77.0, 'nd_helmets', crop=(0.0, 0.1, 0.86, 0.86), **{'in': 1.35}),       # Notre Dame, gold helmets under the lights
    S(78.0, 'kids_team', **{'in': 0.8}),                                      # the smallest line fires off the ball
    S(79.5, 'mission_control_cheer_2', **{'in': 0.3}),                        # Artemis II is home
    S(81.5, 'mission_control_cheer', **{'in': 1.6}),                          # the room goes up
    S(82.5, 'new_citizens'),                                                  # right hands raised
    S(84.0, 'mach_team'),                                                     # the launch crew at the Viper
    S(85.5, 'mach_team', **{'in': 2.1}),                                      # the operators
    S(87.0, 'mach_team_2'),                                                   # the airframe lifted under the flag
    S(89.0, 'mach_team_3'),                                                   # carried out across the desert
    S(90.5, 'grads_today_2'),                                                 # the tassels turn
], LIFT)

# ---- 92-116: THE KEY CHANGE. Bigger pictures, held longer.
FINAL = layout([
    S(LIFT, 'blue_angels', fx=dict(bloom=0.25, punch=0.14)),                  # the diamond climbs on its smoke
    S(94.5, 'nd_students', **{'in': 0.5}),                                    # the stadium on its feet
    S(96.0, 'relay_handoff', crop=(0.0, 0.0, 0.86, 0.86), **{'in': 2.2}),     # four women and the flag
    S(98.0, 'flight_deck_3'),                                                 # the director, arms wide in the steam
    S(99.5, 'nd_basilica'),                                                   # the Basilica of the Sacred Heart
    S(101.5, 'nd_grotto', **{'in': 1.75}),                                    # the Grotto, every candle lit
    S(103.0, 'fire_crew_3'),                                                  # at the door of the fire
    S(104.5, 'flight_deck_2', **{'in': 2.7}),                                 # off the bow, over the sea
    S(106.0, 'launch_2'),                                                     # Artemis II: ignition
    S(107.5, 'launch', fx=dict(bloom=0.35)),                                  # and the whole stack goes past the camera
], LIFT + 18.0)


def pairs(beats, *rows):
    """Then and now, shot for shot: (old key, in), (new key, in), ... each `beats` long."""
    out = []
    for k in rows:
        k = (k,) if isinstance(k, str) else k
        it = C(k[0], beats, **({'in': k[1]} if len(k) > 1 else {}))
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=6 if beats >= 1 else 8)
        out.append(it)
    return out


# 110-116 a beat each, 116-124 half a beat each: the generations before us against this one
RHYME = pairs(1.0, ('hope_answer', 0.4), ('build_crew', 0.6),                 # the heave / the wall goes up
              ('forged', 0.5), ('young_welder', 1.2),                         # sparks / sparks
              ('go_ramp', 0.2), ('fire_crew', 1.0))                           # down the ramp / through the door
STROBE = pairs(0.5, ('bastogne', 0.6), ('linemen', 0.4),                      # digging in / digging in
               ('apollo13', 0.8), ('mission_control_cheer', 2.2),             # the room holds its breath / the room goes up
               ('apollo11', 1.6), ('launch_2', 3.1),                          # the flag on the Moon / the way back
               ('hope_born_2', 0.3), ('new_citizens', 1.0),                   # the mother at the rail / the oath
               ('hope_born', 1.6), ('grads_today_2', 0.6),                    # waving at the harbor / the class of today
               ('go_ramp_2', 1.4), ('flight_deck', 0.6),                      # down the gangway / the deck
               ('spirit_answer', 1.0), ('nd_students', 2.0),                  # on the Wall / in the stands
               ('liberty_bell_2', 1.0), ('liberty_bell', 1.0))                # ... and the bell

# ---- 124-136: the final chord. Every bell rings; Reagan hands it over.
LAST = layout([
    S(CHORD, 'bell_town_2', alt=[('grads_today', 0.0)], fx=dict(bloom=0.3, punch=0.14), **{'in': 2.9}),  # every bell rings
    S(CHORD + 1.6, 'bell_town_4', alt=[('grads_today', 1.0)], **{'in': 3.9}),  # ... hauled by hand, 4 July 2026
    S(CHORD + 2.8, 'grads_today'),                                            # confetti on the class of today
    S(CHORD + 4.1, YOURS, lips='Y'),                                          # "And now, they're yours"
    S(W('Y', 7.55), 'oath', **{'in': 0.3}),                                   # "to protect"
    S(W('Y', 8.70), 'kids_team_2'),                                           # "and pass on."  (a coach and his boys)
    S(W('Y', 9.60) + 0.5, 'nd_basilica_2'),                                   # the altar, as the organ rings out
], END_AT)

# ---- silence; one toll; a child's hand reaches for the bell. We stop before it lands.
END_TEXT = os.environ.get('HIST_TEXT', 'History is asking.')
END = [
    C('liberty_bell', 3.5, speed=0.5, **{'in': 0.2}),                         # the toll
    C('bell_reach', END_LEN - 3.5, alt=[('liberty_bell_2', 0.0)], fx=dict(punch=0.0, shake=0, chroma=0),
      text=[(4.2, END_TEXT, 44, 0.945, 'serif')]),
]

# Black and white until the drop; from it on, color, except the generations before us.
OLD_REFS = {'hope_answer', 'hope_answer_2', 'forged', 'forged_2', 'go_ramp', 'go_ramp_2', 'bastogne', 'apollo13', 'apollo11',
            'hope_born', 'hope_born_2', 'spirit_answer', 'liberty_bell', 'liberty_bell_2', R81, YOURS}


def era(items):
    for it in items:
        path = it.get('clip') or it.get('photo')
        if not path:
            continue
        key = os.path.splitext(os.path.basename(path))[0]
        key = key[len(P):] if key.startswith(P) else key
        it['fx'] = dict(it.get('fx', {}), sat=0.0 if key in OLD_REFS else COLOR['sat'])


era(CHORUS + FINAL + RHYME + STROBE + LAST + END)
SEQ = OPEN + VERSE + CHORUS + FINAL + RHYME + STROBE + LAST + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed %s: %.2f s' % (SONG_VERSION, make_bed()))
    if 'bell' in sys.argv:
        make_bells()
        make_reach()
        print('bells and the ending shot written')
    b = 0.0
    marks = {id(OPEN[0]): 'OPEN', id(VERSE[0]): 'VERSE', id(CHORUS[0]): 'DROP', id(FINAL[0]): 'LIFT', id(RHYME[0]): 'RHYME',
             id(STROBE[0]): 'STROBE', id(LAST[0]): 'CHORD', id(END[0]): 'END'}
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
