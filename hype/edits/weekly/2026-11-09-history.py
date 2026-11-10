"""HISTORY WILL ASK. A 16:9, ~105 s film cut to Sabaton's "Soldier of Heaven" (our pipe-organ version).

The premise, in one sentence: history is asking this generation of Americans the same three questions it asked
every generation before it, and the answer decides "the fate of freedom for a thousand years".

The words are the close of Reagan's commencement address at Notre Dame, 17 May 1981 (National Archives tape):
  "But history will ask, and our answer determines the fate of freedom for a thousand years: Did a nation born
   of hope lose hope? Did a people forged by courage find courage wanting? Did a generation steeled by hard war
   and a harsh peace forsake honor at the moment of great climactic struggle for the human spirit? If history
   asks such questions, it also answers them. And the answers are to be found in the heritage left by
   generations of Americans before us. They stand in silent witness to what the world will soon know and
   history someday record: that in its third century, the American nation came of age, affirmed its leadership
   of free men and women, serving selflessly a vision of man with God, government for people, and humanity at
   peace."
2026 is the 250th year: the start of that third century's second half. 9 November is the day the Wall fell.

The motif is a BELL: history asking. It tolls after each question; each question is answered, in black and
white, by the generation it was put to (the Depression's builders, the men on the ramp, the Moon and the Wall).
On "history someday record:" the song's chorus drops, the picture turns to color, and the bell is ours: today's
Americans answering. The sentence finishes across the key change ("came of age" -> liftoff). After the last
chord, silence, one toll, and a hand reaching for the bell. End line: "History is asking."

Song bed (make_bed(); 96 BPM; beats of the edit, the music enters at beat 12 after a cold open):
  12-28 the synth intro and drum fill, 28-78 verse 1 with no singer (the band only), all lo-fi under the voice;
  78 chorus 3 at full fidelity with the organ on the vocal line; 110 the key change, full organ;
  142 the final chord; 150 the organ lets go; ring-out to ~155.
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
DROP = M + 66                # 78  chorus 3: color, full fidelity, the organ
LIFT = M + 98                # 110 the key change, organ tutti
CHORD = M + 130              # 142 the final chord
RELEASE = M + 138            # 150 the organ lets go
LOFI = dict(until=DROP, cutoff=2300, hp=170)
LIMIT = 0.94                 # master limiter on the finished mix
FX = dict(sat=0.0, chroma=3, shake=4, punch=0.04)  # black and white unless a shot says otherwise
COLOR = dict(sat=1.05)

# ---------------------------------------------------------------- the song bed
# Recording beats of Soldier of Heaven (grid phase 0.085 s; bar N starts at 1 + 4(N-1) + the 5/4 bars before it):
# bars 1-16 (rec beats 1-67: intro, drum fill, verse 1) from the instrumental stems, then straight to chorus 3
# (bar 63, rec beat 255), the key-change chorus (287) and the final chord (319) of the organ mix Will approved
# ("Soldier of Heaven (organ) - backing track for Nov 9 video", the one with the shorter ending).
BED_PHASE = 0.085
MASTER = 10 ** (-2.5 / 20)   # the organ mix was mastered 2.5 dB down; the bare stems are matched to it
BEDS = {
    'organ': dict(segments=[('out/soh_score_organ_v3.backing.wav', 1, 67, MASTER), ('out/soh_organ_short.wav', 255, None, 1.0)],
                  end=207.84, fade=1.7),
    'vocals': dict(segments=[('out/soh_score_organ_v3.backing.wav', 1, 67, 1.0), ('media/raw/organ_soh/soh.mp3', 255, None, 1.0)],
                   end=207.84, fade=1.7),
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
    Q3=(21.06, 29.34),   # Did a generation steeled by hard war and a harsh peace forsake honor at the moment of
                         # great climactic struggle for the human spirit?
    C1=(30.12, 34.12),   # If history asks such questions, it also answers them.
    C2=(34.90, 40.16),   # And the answers are to be found in the heritage left by generations of Americans before us.
    D1=(40.86, 46.14),   # They stand in silent witness to what the world will soon know and history someday record:
    D2=(46.96, 51.34),   # that in its third century, the American nation came of age,
    D3=(52.32, 62.04),   # affirmed its leadership of free men and women, serving selflessly a vision of man with
                         # God, government for people, and humanity at peace.
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
say('Q3', 34.6)                              # "Did a generation steeled by hard war and a harsh peace forsake honor at the
                                             #  moment of great climactic struggle for the human spirit?"  (to 47.9)
toll(48.0, gain=0.85, dur=5.0)
say('C1', 53.0)                              # "If history asks such questions, it also answers them."  (to 59.4)
say('C2', 60.2)                              # "And the answers are to be found in the heritage left by generations of Americans before us."  (to 68.6)
say('D1', 69.0)                              # "They stand in silent witness to what the world will soon know and history someday record:"  (to 77.45)
toll(DROP, gain=0.6, duck=1.0, dur=5.0)      # the drop: the bell is ours now
say('D2', LIFT - 0.15 - (PH['D2'][1] - PH['D2'][0]) / BEAT, gain=1.15, duck=0.5)  # "that in its third century, the American nation came of age," ("age" ends on the key change)
toll(LIFT, note='c', gain=0.55, duck=1.0, dur=5.0)
say('D3', LIFT + 8.0, gain=1.15, duck=0.5)   # "affirmed its leadership of free men and women, serving selflessly a vision of man with God,
                                             #  government for people, and humanity at peace."          (118 to 133.6)
toll(CHORD, note='c', gain=0.6, duck=1.0, dur=3.2, fade=2.6)
if have('bells_c', '.wav'):                  # ... and every bell rings with it, then makes room for the voice
    VOICEOVER.append(dict(file=media('bells_c', '.wav'), at=CHORD + 0.1, src_in=0.0, dur=6.5, gain=0.42, duck=1.0, fade=0.1))
if have(YOURS):                              # the handoff, over the held chord: "pass on" lands as the organ lets go
    say('Y', CHORD + 3.4, gain=1.35, duck=0.38, tail=0.35)  # "And now, they're yours ... to protect ... and pass on."  (145.4 to 150.7)
END_AT = RELEASE + 4.0                       # 154: the organ has let go; the last shots
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
    S(0.0, 'liberty_bell', alt=[('w1104_bells', 0.0)], speed=0.7),            # toll: the Liberty Bell, the crack
    S(2.3, R81, lips='A'),                                                    # "But history will ask,"
    S(4.5, 'liberty_bell_2', alt=[('w1104_bells', 1.6)], speed=0.5),          # toll: the bell on its pedestal, 1925
    S(6.25, R81, lips='B'),                                                   # "and our answer determines"
    S(W('B', 9.74), 'w1102_statue_liberty', alt=['valley'], speed=0.8),       # "the fate of freedom for a thousand years."
], M)

# ---- 12-78: the three questions, each answered by the generation it was put to. Lo-fi; drums at 28.
VERSE = layout([
    S(12.0, 'hope_born', alt=['valley']),                                     # "Did a nation"  (immigrants crowd the rail, waving, as the ship comes in)
    S(W('Q1', 13.86), 'hope_born_2', alt=[('call_explorers', 0.0)]),          # "born of hope"  (a mother in a shawl beams at her baby)
    S(W('Q1', 15.00), 'breadline'),                                           # "lose hope?"    (the bread line, 1930)
    S(17.4, 'dust_bowl', **{'in': 2.0}),                                      # toll: the farmer leans into the dust
    S(19.3, 'hope_answer', alt=[('call_ironworkers', 0.0)]),                  # the answer: they built (the Empire State's steel, 1930)
    S(20.9, 'call_dam', alt=[('hope_answer_2', 0.0)]),                        # ... and the dam
    S(22.5, 'forged', alt=[('w1102_steel_pour', 0.0), ('call_steel', 0.0)]),  # "Did a people forged by courage"
    S(W('Q2', 18.48), 'pearl_harbor'),                                        # "find courage wanting?"  (Battleship Row)
    S(DRUMS, 'go_ramp', fx=dict(punch=0.1)),                                  # toll + drums: the ramp drops and they go
    S(30.0, 'courage_answer', alt=[('w1102_paratroopers', 0.0)]),             # out the door
    S(31.5, 'bastogne'),                                                      # the Ardennes
    S(33.0, 'courage_answer_2', alt=[('go_ramp_2', 0.6)]),                    # down the gangway
    S(34.5, R81, lips='Q3'),                                                  # "Did a generation steeled by"
    S(W('Q3', 22.60), 'w1102_dday_ramp', alt=[('bastogne_2', 0.0)]),          # "hard war"
    S(W('Q3', 23.26), 'harsh_peace', alt=[('call_vietnam_korea', 0.0)]),      # "and a harsh peace"
    S(W('Q3', 24.20), 'w1102_arlington_guard', alt=[('call_old_guard', 0.0)]),  # "forsake honor"  (the Tomb sentinel)
    S(W('Q3', 25.60), 'apollo13'),                                            # "at the moment of great climactic"  (Mission Control, April 1970)
    S(W('Q3', 27.94), 'call_reagan_wall', alt=[('apollo13_2', 1.9)]),         # "struggle for the human spirit?"  (the Wall, still standing)
    S(48.0, 'apollo11', alt=[('call_aldrin', 0.0)], **{'in': 0.6}),           # toll: the answer, the flag on the Moon
    S(49.6, 'spirit_answer', alt=[('w1102_miracle_ice', 0.0)]),               # ... and on top of the Wall, 9 November 1989
    S(51.2, 'spirit_answer_2', alt=[('spirit_answer', 2.0)], **{'in': 0.15}),  # a hammer and a chisel
    S(52.5, R81, lips='C1'),                                                  # "If history asks such questions,"
    S(W('C1', 32.80), 'iwo_jima', alt=[('w1102_iwo_flag', 0.0)], **{'in': 0.3}),  # "it also answers them."
    S(59.8, 'w1104_lincoln', alt=[('call_lincoln', 0.0)]),                    # "And the answers are to be found"
    S(W('C2', 36.26), 'rushmore', fit='cover', zoom=(1.0, 1.1)),              # "in the heritage"
    S(W('C2', 36.98), 'valley', fit='cover', zoom=(1.0, 1.1), center=(0.42, 0.42)),  # "left by"  (Washington crossing the Delaware)
    S(W('C2', 38.10), 'w1102_rosie'),                                         # "generations"
    S(W('C2', 38.68), 'w1102_willow_run', alt=[('call_ford', 0.0)]),          # "of Americans"
    S(W('C2', 39.28), 'call_doughboys', alt=[('call_marines', 0.0)]),         # "before us."
    S(68.8, 'w1102_normandy_cemetery'),                                       # "They stand in silent witness"
    S(W('D1', 42.34), 'call_earthrise', alt=[('call_artemis_earth', 0.0)]),   # "to what the world will soon know"
    S(W('D1', 43.90) + 0.1, 'liberty_bell', alt=[('w1104_bells', 0.0)], speed=0.55, fx=dict(punch=0.0), **{'in': 0.3}),  # "and history someday record:"
], DROP)

# ---- 78-110: THE DROP. Color; the organ; today's Americans answer the bell.
CHORUS = layout([
    S(DROP, 'flight_deck_2', fx=dict(punch=0.12, bloom=0.3), **{'in': 1.35}),  # the jet goes
    S(80.0, 'flight_deck', **{'in': 1.6}),                                    # the yellow shirt signals through the steam
    S(81.0, 'mach_team'),                                                     # the launch crew at the Viper
    S(82.0, 'mach_viper'),                                                    # and it dives
    S(83.5, 'young_welder_2', alt=[('young_welder', 0.0), ('call_anon_welder', 0.3)]),  # she looks at us, snaps the hood down, strikes the arc
    S(86.5, 'shipyard'),                                                      # a carrier's hull module on the hook
    S(87.5, 'linemen'),                                                       # setting the pole
    S(88.5, 'fire_crew', alt=[('call_now_firefighters', 1.2)]),               # going in together
    S(90.0, 'build_crew'),                                                    # the wall goes up
    S(91.0, 'relay_handoff_2'),                                               # the baton
    S(93.0, 'huddle_hands', **{'in': 1.3}),                                   # the break
    S(94.0, 'nd_helmets', alt=[('tunnel_run', 0.5)], crop=(0.0, 0.1, 0.86, 0.86), **{'in': 0.2}),  # Notre Dame, gold helmets under the lights
    S(95.0, 'mission_control_cheer_2', **{'in': 0.3}),                        # Artemis II is home
    S(97.0, 'surgical_team', alt=[('young_welder', 0.0)]),                    # the team at the table
    S(98.0, 'fire_crew_2', alt=[('mach_team_3', 0.0)]),                       # the line holds
    S(99.0, 'b2_flyover', **{'in': 1.0}),                                     # over the stadium
    S(100.7, 'flag_stadium'),                                                 # the flag, held by a line of sailors
    S(W('D2', 46.96) - 0.1, 'fireworks', alt=[('fireworks_2', 0.0)]),         # "that in its third century,"  (the 250th summer)
    S(W('D2', 49.24), 'w1102_capitol', alt=[('rushmore_2', 0.0)]),            # "the American nation"
    S(W('D2', 50.44), 'grads_today_2', alt=[('call_anon_grads', 0.2), ('call_cadets', 0.0)]),  # "came of age,"  (the tassels turn)
], LIFT)

# ---- 110-142: THE KEY CHANGE. The sentence finishes over the generation it describes; then everything at once.
FINAL = layout([
    S(LIFT, 'launch', alt=[('w1104_launch', 0.0), ('call_artemis', 1.2)], fx=dict(bloom=0.4, punch=0.14)),  # Artemis II, liftoff on the downbeat
    S(112.5, 'launch_2', alt=[('call_now_starship', 0.0), ('w1102_artemis', 0.0)], fx=dict(bloom=0.3)),
    S(114.0, 'flight_deck_3'),                                                # the director, arms wide in the steam
    S(115.5, 'mach_glide', **{'in': 1.85}),                                   # the Glide comes in
    S(W('D3', 52.32) - 0.1, 'blue_angels', alt=[('/blue_angels', 0.0)]),      # "affirmed its leadership"
    S(W('D3', 53.54), 'mach_team_2'),                                         # "of free men and women,"  (a woman and a man lift the airframe under the flag)
    S(W('D3', 55.40) - 0.2, 'coast_guard_crew', alt=[('call_coast_guard', 0.0), ('call_now_firefighters', 0.0)]),  # "serving selflessly"
    S(W('D3', 56.54), 'nd_grotto', **{'in': 1.75}),                           # "a vision of man"  (the Grotto, candles)
    S(W('D3', 57.90) - 0.1, 'nd_basilica', alt=[('w1104_basilica_nd', 0.0), ('touchdown_jesus', 0.0)]),  # "with God,"
    S(W('D3', 58.78) - 0.1, 'new_citizens', alt=[('call_anon_citizens', 0.0)]),  # "government for people,"
    S(W('D3', 60.34) - 0.2, 'kids_team', alt=[('call_anon_family', 1.4)]),    # "and humanity"
    S(W('D3', 60.88) + 0.3, 'call_anon_wedding_2'),                           # "at peace."
], LIFT + 24.0)


def strobe(*keys):
    """Half-beat cuts: the generations, then and now, one after the other."""
    out = []
    for k in keys:
        k = (k,) if isinstance(k, str) else k
        it = C(k[0], 0.5, **({'in': k[1]} if len(k) > 1 else {}))
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=8)
        out.append(it)
    return out


STROBE = strobe(('go_ramp', 0.3), ('flight_deck_2', 2.2), ('call_dam', 0.5), ('shipyard', 0.4),
                ('bastogne', 0.5), ('linemen', 0.4), ('iwo_jima', 1.2), ('flag_stadium', 1.0),
                ('w1102_rosie', 0.5), ('young_welder', 0.5), ('apollo11', 1.5), ('mission_control_cheer', 1.6),
                ('breadline_2', 0.5), ('build_crew', 1.0), ('hope_born_2', 0.3), ('nd_students', 0.5))

# ---- 142-154: the final chord. Every bell rings; Reagan hands it over.
LAST = layout([
    S(CHORD, 'grads_today', alt=[('nd_students', 1.2)], fx=dict(bloom=0.3, punch=0.14)),  # every bell rings: confetti on the class of today
    S(CHORD + 3.1, YOURS, lips='Y'),                                          # "And now, they're yours"
    S(W('Y', 7.55), 'oath', **{'in': 0.3}),                                   # "to protect"
    S(W('Y', 8.70), 'kids_team_2', alt=[('call_kid_flag', 0.0)]),             # "and pass on."  (a coach and his boys)
    S(W('Y', 9.60) + 0.7, 'w1102_statue_liberty', **{'in': 1.0}),             # the torch again, in color now
], END_AT)

# ---- silence; one toll; a child's hand reaches for the bell. We stop before it lands.
END_TEXT = os.environ.get('HIST_TEXT', 'History is asking.')
END = [
    C('liberty_bell', 3.5, speed=0.5, **{'in': 0.2}),                         # the toll
    C('bell_reach', END_LEN - 3.5, alt=[('liberty_bell_2', 0.0)], fx=dict(punch=0.0, shake=0, chroma=0),
      text=[(4.2, END_TEXT, 44, 0.945, 'serif')]),
]

# Black and white until the drop; from it on, color, except the generations before us.
OLD_REFS = {'go_ramp', 'call_dam', 'bastogne', 'iwo_jima', 'w1102_rosie', 'call_aldrin', 'apollo11', 'breadline_2', 'valley',
            'hope_born_2',
            'liberty_bell', R81, YOURS}


def era(items):
    for it in items:
        path = it.get('clip') or it.get('photo')
        if not path:
            continue
        key = os.path.splitext(os.path.basename(path))[0]
        key = key[len(P):] if key.startswith(P) else key
        it['fx'] = dict(it.get('fx', {}), sat=0.0 if key in OLD_REFS else COLOR['sat'])


era(CHORUS + FINAL + STROBE + LAST + END)
SEQ = OPEN + VERSE + CHORUS + FINAL + STROBE + LAST + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed %s: %.2f s' % (SONG_VERSION, make_bed()))
    if 'bell' in sys.argv:
        make_bells()
        make_reach()
        print('bells and the ending shot written')
    b = 0.0
    marks = {id(OPEN[0]): 'OPEN', id(VERSE[0]): 'VERSE', id(CHORUS[0]): 'DROP', id(FINAL[0]): 'LIFT',
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
