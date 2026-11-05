"""YOUR PURPOSE IS CALLING. A 16:9, ~91 s montage in the spirit of the "Be Excellent." edit Will loved.

Mostly black-and-white archival film with grainy color payoffs; Little Dark Age (the original recording,
vocals 6 dB down; or our pipe-organ version) runs lo-fi under nearly everything with real voices over it;
light-touch looks (duotone, echo trails, RGB drift, one mirror, bloom) and signal rings when the phone
rings. No on-screen text until the last line, "Your purpose is calling."

It opens on a ringing phone over 1950s teenagers who haven't had the call yet, and JFK's inaugural
straight away; the phone rings again when he finishes, in the pause between MLK's street sweeper and
its payoff, and at the very end, when a girl answers it.

Seven plot lines are woven through it, each told start to finish, one cut a beat:
  SOLDIER   the oath, recruits, doughboys, Marines, the Navy, the Huey ... the hat toss, the Old Guard
  BUILDER   high steel, Hoover Dam, the Model T line ... the Pike takes off, Falcon lands
  EXPLORER  Lewis and Clark, the wagons, the Wrights ... Apollo, Artemis II, Earthrise
  ATHLETE   Bob Hayes, Ruth, Ali ... the Miracle, the 2026 gold, Alysa Liu
  WORKER    the farmer, the lineman, the street sweeper, the WTC firefighters ... the Coast Guard
  FAMILY    mother and child, grace at the table, the nurse, the preachers ... the girl who answers
  LEGENDS   (under FDR) Washington, Lincoln, TR, Reagan, George Bailey, Peck and Hepburn, Kane

Song bed (make_bed() below; 97.5 BPM, beats of the edit): 0-24 the second half of the third chorus,
24-33 the hook (two bars spliced out), 33-64 the verse, 64-96 the fourth chorus, all lo-fi; 96-128
the final chorus at full fidelity, 128-136 the last sung line, and the song stops dead at 136.
Voices: JFK (3-19), a chorus of American voices low (23-33), MLK's street sweeper (33-46) ... ring ...
the payoff (52-65), FDR (66-78), George Bailey, "I want to live again" (78-82, on screen), "Do you
believe in miracles?" (92-96), "Liftoff!" (96), "Attaboy, Clarence" (137, voice only), the last ring.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'call_'
BPM = 97.5
BEAT = 60 / BPM
SONG_VERSION = os.environ.get('CALL_SONG', 'orig_lift')  # orig_lift | orig | orig_m2 (a whole step down) | orig_p1 | organ
SONG = 'media/call_song_%s.wav' % SONG_VERSION
SONG_START = 0.0
DROP = 104
STOP = 168  # the song's last chord cuts off here (the organ version rings a closing chord instead)
LOFI = dict(until=DROP, cutoff=2300, hp=170)
FX = dict(sat=0.0, chroma=3, shake=4, punch=0.04)  # black-and-white unless a shot says otherwise
COLOR = dict(sat=1.05)

# ---------------------------------------------------------------- the song bed
# Recording beats of Little Dark Age (beat grid phase 0.245 s, the organ was aligned to the same grid):
# from bar 63 (mid third chorus, rec beat 281) to the hook, a two-bar cut inside the hook (308 -> 316,
# the most self-similar pair), on to the end of the final chorus (bar 94 ends at 417), then the last
# sung line (bar 107, 473) to the song's dead stop (bar 109, 481) and its ring-out. The organ version
# goes from the end of the final chorus straight to its closing chord (481).
BED_PHASE = 0.245
STEMS = 'media/organ_cache/1416f0ad1406'  # Demucs stems of media/raw/organ_lda/lda.mp3
BEDS = {
    'orig': dict(segments=[(281, 441), (473, 485)], vocals_db=-6.0, pitch=0),
    'orig_m2': dict(segments=[(281, 441), (473, 485)], vocals_db=-6.0, pitch=-2),
    'orig_p1': dict(segments=[(281, 441), (473, 485)], vocals_db=-6.0, pitch=1),
    # a whole step down until the final chorus, then up to the record's own key on its downbeat (just before
    # "I grieve in stereo"): a key-change lift into the payoff, on the same beat the lo-fi opens up
    'orig_lift': dict(segments=[(281, 441), (473, 485)], vocals_db=-6.0, pitch=-2, pitch_until=104,
                      cosmic=dict(after=104, reverb_db=-7.5, shimmer_db=-12, width=1.6, low_db=3.0, air_db=3.5)),
    'organ': dict(segments=[(281, 441), (481, None)], src='out/lda_score_organ.wav'),
}


def make_bed(version=SONG_VERSION, xfade=0.03):
    import numpy as np
    import soundfile as sf
    cfg = BEDS[version]
    if 'src' in cfg:
        x, sr = sf.read(os.path.join(HERE, cfg['src']), dtype='float32')
    else:
        st = {k: sf.read(os.path.join(HERE, STEMS, k + '.wav'), dtype='float32')[0] for k in ('drums', 'bass', 'other', 'vocals')}
        sr = 44100
        n = min(len(v) for v in st.values())
        x = sum(st[k][:n] for k in ('drums', 'bass', 'other')) + st['vocals'][:n] * 10 ** (cfg['vocals_db'] / 20)
    t = lambda rb: BED_PHASE + rb * BEAT
    nx = int(xfade * sr)
    ramp = np.linspace(0, 1, nx)[:, None]
    y = None
    for a, b in cfg['segments']:
        i0 = int(round(t(a) * sr))
        seg = x[i0:min(len(x), int(round(t(b) * sr))) if b is not None else len(x)]
        if y is None:
            y = seg
        else:  # the outgoing segment fades out over the incoming one's last moments before its bar line
            y = np.concatenate([y[:-nx], y[-nx:] * (1 - ramp) + x[i0 - nx:i0] * ramp, seg])
    pk = np.abs(y).max()
    if pk > 0.98:
        y = y * (0.98 / pk)
    out = os.path.join(HERE, 'media', 'call_song_%s.wav' % version)
    sf.write(out, y, sr, subtype='PCM_24')
    if cfg.get('pitch'):  # key shift, tempo kept (Rubber Band, formants preserved for the voice; it adds < 3 ms)
        tmp = out + '.tmp.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-af',
                        'rubberband=pitch=%f:pitchq=quality:transients=mixed:formant=preserved' % 2 ** (cfg['pitch'] / 12),
                        '-c:a', 'pcm_s24le', tmp], check=True)
        if cfg.get('pitch_until') is not None:  # shifted up to that beat of the edit, the original key after it
            z, _ = sf.read(tmp, dtype='float32')
            z = z[:len(y)]
            k = int(round(cfg['pitch_until'] * BEAT * sr))
            nz = int(0.02 * sr)
            r = np.linspace(0, 1, nz)[:, None]
            y = np.concatenate([z[:k - nz], z[k - nz:k] * (1 - r) + y[k - nz:k] * r, y[k:]])
            sf.write(out, y, sr, subtype='PCM_24')
            os.remove(tmp)
        else:
            os.replace(tmp, out)
    if cfg.get('cosmic'):  # after the key change: a long hall, the hall an octave up, wider, more air and weight
        import sys
        sys.path.insert(0, HERE)
        import organ
        from scipy.signal import butter, sosfiltfilt
        from score_organ import limit
        c = cfg['cosmic']
        y, sr = sf.read(out, dtype='float32')
        k = int(round(c['after'] * BEAT * sr))
        post = y[k:]
        wet = organ.cathedral(post.T.copy(), rt60=6.5, wet=1.0, hp=300.0).T / 2.2
        tw, ts = out + '.wet.wav', out + '.shim.wav'
        sf.write(tw, wet, sr, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tw, '-af', 'rubberband=pitch=2.0:pitchq=quality,highpass=f=900,lowpass=f=12000', ts], check=True)
        shim = sf.read(ts, dtype='float32')[0][:len(wet)]
        os.remove(tw), os.remove(ts)
        z = post + wet * 10 ** (c['reverb_db'] / 20) + shim * 10 ** (c['shimmer_db'] / 20)
        m, sd = (z[:, 0] + z[:, 1]) / 2, (z[:, 0] - z[:, 1]) / 2 * c['width']
        z = np.stack([m + sd, m - sd], 1)
        lo = sosfiltfilt(butter(2, 90, 'lowpass', fs=sr, output='sos'), z, axis=0)
        hi = sosfiltfilt(butter(2, 9000, 'highpass', fs=sr, output='sos'), z, axis=0)
        z = z + lo * (10 ** (c['low_db'] / 20) - 1) + hi * (10 ** (c['air_db'] / 20) - 1)
        r = np.linspace(0, 1, int(0.25 * sr))[:, None]  # it blooms in on the downbeat
        z[:len(r)] = post[:len(r)] * (1 - r) + z[:len(r)] * r
        y = limit(np.concatenate([y[:k], z]).T * 10 ** (-1.5 / 20), ceiling=0.97).T
        sf.write(out, y, sr, subtype='PCM_24')
    return len(y) / sr


# ---------------------------------------------------------------- footage
def _find(key):
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
        path = os.path.join(HERE, 'media', P + key + ext)
        if os.path.exists(path):
            return kind, path
    return None, None


def C(key, beats, alt=None, **kw):
    """Footage from media/call_<key>.*; else the first alternate that exists (alt = key or (key, in)
    or a list of them), else a labeled card."""
    kind, path = _find(key)
    for a in ([alt] if isinstance(alt, (str, tuple)) else alt or []) if not path else []:
        k, i = (a, None) if isinstance(a, str) else a
        kind, path = _find(k)
        if path:
            if i is not None:
                kw['in'] = i
            break
    if path:
        if kind == 'photo':
            for k in ('in', 'speed', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
                kw.pop(k, None)
            kw.setdefault('fit', 'contain')
            kw.setdefault('zoom', (1.0, 1.06))
        return dict({kind: path}, beats=beats, **kw)
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck', 'mg'):
        kw.pop(k, None)
    return dict(shot='slot', beats=beats, p=dict(label=key.upper().replace('_', ' '), desc=key, kind='clip'), **kw)


def have_clip(key):
    return _find(key)[1] is not None


def strobe(*items):
    out = []
    for it in items:
        it = dict(it, beats=0.5)
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=8)
        out.append(it)
    return out


def _dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None


def media(key):
    return 'media/' + P + key + '.m4a'


def have(key):
    return os.path.exists(os.path.join(HERE, media(key)))


RINGS = dict(kind='rings', cx=0.5, cy=0.5, period=0.8, n=3, alpha=0.3)
DUO = dict(duotone=((16, 22, 52), (250, 236, 210)), duo_mix=0.5)

# ---------------------------------------------------------------- voices (beats; the music sits low under each)
VOICEOVER = []


def vo(key, at, src_in=0.0, dur=None, gain=1.0, duck=0.35):
    if have(key):
        VOICEOVER.append(dict(file=media(key), at=at, src_in=src_in, dur=dur or (_dur(os.path.join(HERE, media(key))) - src_in),
                              gain=gain, duck=duck))


# The phone rings, unanswered, the whole way through: in the gaps of JFK's lines and King's sentence, then
# quieter under the music, until the girl picks it up at the end.
RINGS_AT = []


def ring(at, which=0, gain=0.85, duck=0.6):
    """One ring of the bell in media/call_phone_ring.m4a (it holds two: 0.0-1.75 s and 2.0-3.8 s)."""
    src, d = ((0.0, 1.75), (2.0, 1.8))[which]
    vo('phone_ring', at, src_in=src, dur=d, gain=gain, duck=duck)
    RINGS_AT.append(at)


ring(0.0)                                          # the call
vo('jfk_1', 3.0)                                   # "And so, my fellow Americans:"               (to 6.7)
ring(6.9, 1)
vo('jfk_2', 10.0)                                  # "ask not what your country can do for you;"  (to 17.6)
ring(17.9)
vo('jfk_3', 21.0)                                  # "ask what you can do for your country."      (to 25.2)
ring(25.4, 1)
# the chorus of voices: short iconic lines tumbling over each other, low, between JFK and King
_chorus = [k for k in ('v_teddy', 'v_eagle', 'v_ike_2', 'v_jfk_moon', 'v_ali', 'v_macarthur', 'v_sheen', 'v_graham',
                       'v_rockne', 'v_armstrong', 'v_teddy_2', 'v_ike') if have(k)]
_at = 29.0
for k in _chorus:
    d = min(_dur(os.path.join(HERE, media(k))) or 1.5, 2.6)
    if _at + d / BEAT > 41.2:
        break
    VOICEOVER.append(dict(file=media(k), at=_at, src_in=0.0, dur=d, gain=0.32, duck=1.0))
    _at += d / BEAT * 0.6
MLK1 = 41.5
vo('mlk_a', MLK1, gain=1.0, duck=0.4)              # "Even if it falls your lot to be a street sweeper,"   (to 47.1)
ring(47.25)
MLK_B = 50.2
vo('mlk_b', MLK_B, gain=1.0, duck=0.4)             # "go out and sweep streets like Michelangelo painted."  (to 56.2)
ring(56.4, 1)                                      # ... and it cuts him off
# Reagan, in three pieces over the working line (the phone cuts in before the last)
vo('reagan_1', 59.6, gain=1.0, duck=0.4)           # "America is good."                       (to 62.1, on screen)
vo('reagan_2', 64.1, gain=1.0, duck=0.4)           # "And if America ever ceases to be good,"  (to 68.3)
ring(68.6)
vo('reagan_3', 71.5, gain=1.0, duck=0.4)           # "America will cease to be great."         (to 75.2)
# Clinton, one continuous take over the presidents and the legends (his pauses tightened)
vo('clinton', 76.0, gain=1.0, duck=0.4)            # "People the world over have always been more impressed by the power of our example than by the example of our power."  (to 91.1)
vo('bailey_live', 91.3, gain=1.1, duck=0.35)       # "I want to live again!" (George on screen for it)
vo('miracle_call', 95.8, gain=0.9, duck=0.6)       # "Do you believe in miracles? YES!"
vo('sheen_up_b', 100.4, gain=1.05, duck=0.4)      # the end of the black-and-white era, Sheen pointing straight up: "Up, up, to God!" ("God" ends on the downbeat)
for at, which, g in ((113.0, 0, 0.35), (134.7, 1, 0.35), (152.0, 0, 0.35)):
    ring(at, which, gain=g, duck=0.85)             # still ringing, under the music
# the dividing line: Apollo 11's call on the old rocket, then the new one's
vo('liftoff', DROP + 0.05, src_in=5.2, dur=2.3, gain=1.0, duck=0.8)  # "Liftoff! We have a liftoff!"       (to 108.1)
vo('v_artemis_liftoff', DROP + 4.3, gain=1.0, duck=0.6)            # "...and liftoff! The crew of Artemis II, now bound for the Moon."  (to 117.2)
vo('v_finish_line', 117.4, gain=1.0, duck=0.5)                     # Biden, unseen: "And we own the finish line!" (on Lyles' photo finish)
vo('bailey_clarence', 160.6, gain=1.0, duck=0.45)  # "Attaboy, Clarence." under the last sung line (heard, not seen)
# FDR, in two pieces, over the generation answering now
vo('fdr_1', 138.2, gain=1.0, duck=0.45)            # over the instrumental: "This generation of Americans"  (to 142.1)
vo('fdr_2', 145.0, gain=1.0, duck=0.45)            # "has a rendezvous with destiny."          (to 151.0)
END_AT = 169.0
vo('phone_ring', END_AT - 0.3, src_in=0.0, dur=4.05, gain=0.9, duck=1.0)  # the last ring, twice; she reaches, and we stop before she answers

# ---------------------------------------------------------------- picture
LABOR = [k for k in ('miners', 'steel', 'loggers', 'construction', 'railroad', 'roughnecks', 'fishermen', 'truckers',
                     'grocer', 'diner', 'seamstress', 'janitor') if have_clip(k)]


def labor(i, beats, fallback, **kw):
    """The i-th labor shot the sourcing found, else a fallback (key, in)."""
    if i < len(LABOR):
        return C(LABOR[i], beats, **kw)
    return C(fallback[0], beats, **dict(kw, **{'in': fallback[1]}))


SWEEP_ALT = [('janitor', 0.0), ('workers_3', 0.0)]

# ---- 0-28: the phone rings over teenagers who haven't had the call yet, and keeps interrupting JFK
OPEN = [
    C('teens', 1.5),                                                 # 0    ring: a bored boy flops back on his bed
    C('teens_2', 1.5, **{'in': 0.7}),                                # 1.5  the soda fountain
    C('jfk_cbs', 3.9, **{'in': 14.020}),                             # 3    "And so, my fellow Americans:" (lips in sync)
    C('teens_3', 1.5, **{'in': 0.3}),                                # 6.9  ring: a shop student daydreams
    C('teens_4', 1.6, alt=[('teens_alt', 0.0)]),                     # 8.4  a girl alone on the porch steps
    C('jfk_cbs', 6.6, **{'in': 17.025}),                             # 10   "ask not what your country can do for you;" (in sync)
    C('jfk_wide_2', 1.3, fx=dict(trail=0.35)),                       # 16.6 the crowd
    C('teens_alt', 1.5, alt=[('teens', 2.0)]),                       # 17.9 ring: the boy on his bed, waiting
    C('teens', 1.6, **{'in': 2.2}),                                  # 19.4 staring at the ceiling
    C('jfk_cbs', 4.3, **{'in': 21.890}),                             # 21   "ask what you can do for your country." (in sync)
    C('enlist', 1.5, mg=[RINGS], fx=dict(trail=0.3)),                 # 25.3 ring: SOLDIER, the oath
    C('ironworkers', 1.5, mg=[RINGS], fx=dict(DUO)),                 # 26.8 BUILDER: high steel
]
# ---- 28.3-41.5: the lines take their first steps; a chorus of voices low
LINES = [
    C('lewis_clark_2', 1, alt=[('explorers', 0.0)]),                 # 28.3 EXPLORER: the keelboat heads up the Missouri
    C('owens', 1),                                                   # 29.3 ATHLETE: Bob Hayes
    C('babe_ruth', 1),                                               # 30.3 ATHLETE
    C('mother', 1),                                                  # 31.3 FAMILY
    C('enlist_2', 1),                                                # 32.3 SOLDIER: recruits get their caps
    C('ironworkers_2', 1),                                           # 33.3 BUILDER
    C('nd_rockne', 1),                                               # 34.3 ATHLETE: Rockne
    C('farmer', 1, fx=dict(DUO)),                                    # 35.3 WORKER
    C('doughboys', 1, fx=dict(trail=0.35)),                          # 36.3 SOLDIER
    C('wright', 1),                                                  # 37.3 EXPLORER: the Flyer
    C('dad_kid', 1),                                                 # 38.3 FAMILY: grace at the table
    C('explorers', 1),                                               # 39.3 EXPLORER: the wagons
    C('marines_2', 1.2),                                             # 40.3 SOLDIER
]
# ---- 41.5-56.3: King's sentence, each phrase on screen as he says it, the phone cutting in at his pause
M1 = [
    C('mlk_still', 1.5, alt=[('mlk', 0.0)], fit='cover', zoom=(1.0, 1.06)),  # 41.5 King, a still (no lips moving under a different sermon)  "Even if it falls..."
    labor(0, 2.4, ('workers_2', 0.0)),                               # 35   "...your lot to be a"
    C('sweeper', 1.85, alt=SWEEP_ALT, **{'in': 0.4}),                # 37.4 "street sweeper," (St. Louis at dawn)
    C('ford', 1.5, mg=[RINGS]),                                      # 39.25 ring: BUILDER, the line
    C('marines', 1.45, fx=dict(drift=3), mg=[RINGS]),                # 40.75 SOLDIER
    C('sweeper_2', 1.5, alt=[('sweeper', 1.8)] + SWEEP_ALT),         # 42.2 "go out and" (New York's White Wings march out)
    C('sweeper', 1.3, alt=SWEEP_ALT, **{'in': 2.2}),                 # 43.7 "sweep streets" (the broom drives the litter)
    C('michelangelo', 3.3, alt=[('workers_2', 1.0)], zoom=(1.0, 1.12)),  # 45  "like Michelangelo painted."
]
# ---- 56.3-74: Reagan over the working line, the phone still ringing
WORK = [
    C('dam', 1.3, mg=[RINGS]),                                       # 56.3 ring: BUILDER, the high scaler
    C('steel', 2.0),                                                 # 57.6 WORKER
    C('steel_2', 2.0, alt=[('steel', 1.0)]),                         # 59.6 a steelworker in his heat hood  (Reagan, voice only: "America is good.")
    C('loggers', 1.5),                                               # 61.6 WORKER
    C('ali', 1),                                                     # 63.1 ATHLETE
    C('miners_2', 1.5, alt=[('miners', 1.5)]),                       # 64.1 "And if America ever ceases to be good,"
    C('fishermen', 1.5, **{'in': 0.8}),                              # 65.6 WORKER: a gill net hauled in at sunrise
    C('construction', 1.5),                                          # 67.1 WORKER: a carpenter on the frame
    C('railroad', 1.5),                                              # 68.6 ring
    C('nurse', 1),                                                   # 70.1 FAMILY
    C('workers', 1),                                                 # 71.1 WORKER: the lineman
    C('steel_3', 1, alt=[('steel', 2.0)]),                           # 72.1 "America will cease to be great."
    C('navy', 0.9),                                                  # 73.1 SOLDIER
]

# ---- 74-104: the fourth chorus. Reagan finishes, Clinton over the legends; George Bailey; the firefighters go in; the Miracle; Sheen
LEGENDS = [
    C('dc_capitol_alt', 1),                                          # 74  the Washington Monument
    C('washington', 2),                                              # 75
    C('lincoln', 1),                                                 # 77  "People the world over"
    C('teddy', 1, fx=dict(trail=0.3)),                               # 78
    C('reagan_wall', 1),                                             # 79
    C('wright_2', 1),                                                # 80  EXPLORER
    C('sheen', 1),                                                   # 81  FAMILY / faith  "have always been more impressed"
    C('owens_2', 1),                                                 # 82  ATHLETE: Hayes hits the tape
    labor(2, 1, ('workers_3', 3.0)),                                 # 83  WORKER  "by the power of our example"
    C('armstrong_louis', 1.35),                                      # 84  Louis Armstrong, horn raised
    C('mj', 1, alt=[('mr_smith', 0.0)]),                             # 85.35 Michael Jackson, the freeze
    C('peck_hepburn', 1),                                            # 86.35 "than by the example"
    C('vietnam_korea', 1, fx=dict(drift=2)),                         # 87.35 SOLDIER: the Huey
    C('welles_2', 1),                                                # 88.35 "of our power."
    C('lou_gehrig', 0.5),                                            # 89.35 ATHLETE
    C('graham', 0.5),                                                # 89.85 FAMILY / faith
    C('bailey_2', 0.95),                                             # 90.35 George faces the bank run
    C('bailey_live', 1.65, alt=[('bailey', 0.0)]),                   # 91.3 George on the bridge: "I want to live again!"
    C('wtc_fdny', 1.3, alt=[('firefighters_2', 0.0)]),               # 92.95 WORKER: 9/11, Engine 21 down West Street
    C('wtc_fdny_2', 1.3, alt=[('firefighters', 0.0)], **{'in': 1.8}),  # 94.25 a rig heads downtown, the towers ahead
    C('wtc_fdny_3', 1.3, **{'in': 0.3}),                             # 95.55 an Engine 28 firefighter climbs the North Tower stairs
    C('miracle_call', 3.5, **{'in': round((96.85 - 95.8) * BEAT, 3)}),  # 96.85 "Do you believe in miracles? YES!" (black and white, in step with the call)
    C('sheen_up', 3.65, **{'in': round(11.40 - 0.05 * BEAT, 3)}),    # 100.35 the last of the old era: Sheen points straight up, "Up, up, to God!"
]
# ---- 104-168: the final chorus at full fidelity: Americans answering the call now, in color; the instrumental; the last line. The song stops at 168.
FINALE = [
    C('liftoff', 2.5, fx=dict(bloom=0.4, punch=0.12), mg=[dict(RINGS, cy=0.8, alpha=0.22, period=1.1)], **{'in': 2.45}),  # 104 THE MODERN ERA BEGINS: color, the key change, Apollo rises off the pad on the downbeat. "Liftoff! We have a liftoff!"
    C('artemis', 3.5, alt=[('liftoff_2', 0.0)], fx=dict(bloom=0.35, punch=0.12), **{'in': 1.2}),  # 106.5 "...and liftoff! The crew of Artemis II"
    C('artemis_2', 2, **{'in': 2.3}),                                # 110 the crew waves
    C('mach', 2, fx=dict(hue=6)),                                    # 112 the Pike takes off  "now bound for the Moon"
    C('founder', 2, alt=[('jobs', 0.0)]),                            # 114 Ethan Thornton at Mach's all-hands
    C('now_starship', 1, alt=[('spacex', 0.2)]),                     # 116 Starship's booster caught by the tower
    C('gabby_thomas', 2, alt=[('gabby', 0.0)]),                      # 117 Gabby Thomas takes the 200 m  "And we own"
    C('lyles_3', 2, alt=[('lyles', 0.0)]),                           # 119 Lyles' photo finish  "the finish line!"
    C('lyles', 1),                                                   # 121 he roars
    C('olympians_2024', 1),                                          # 122 Simone Biles
    C('now_nurse_2', 1, alt=[('now_nurse', 0.0)]),                   # 123 a young nurse at work
    C('now_lineman', 1),                                             # 124 linemen bring the power back
    C('now_teacher_2', 1, alt=[('now_teacher', 0.0)]),               # 125 a young teacher with her class
    C('now_troops', 1),                                              # 126 a sailor home from the sea
    C('hockey_2026_2', 1, alt=[('hockey_2026', 2.0)]),               # 127 the golden goal
    C('alysa_liu', 1),                                               # 128 Alysa Liu
    C('moh', 1, alt=[('salute', 0.5)]),                              # 129 the Medal of Honor
    C('barron', 1),                                                  # 130 Bishop Barron
    C('prevost_young', 1, alt=[('prevost_young_2', 0.0)]),           # 131 young Fr. Prevost (black and white) ...
    C('pope_leo', 1.5, alt=[('pope_leo_2', 0.0)]),                   # 132 ... Pope Leo XIV
    C('now_science', 1),                                             # 133.5 the Webb team applauds
    C('now_farmer', 0.75),                                           # 134.5 the harvest
    C('cadets', 0.75),                                               # 135.25 the hat toss
    # 136-160: the instrumental, the music opening up: this generation, anonymous, under FDR
    C('anon_welder', 1.5, **{'in': 0.3}),                            # 136 a young welder, the arc lit
    C('anon_wedding', 2, **{'in': 0.4}),                             # 137.5 a wedding kiss under the arbor  "This generation
    C('anon_baby', 1.5),                                             # 140 a father lifts his newborn         of Americans"
    C('anon_citizens', 2),                                           # 141.5 new citizens take the oath
    C('now_firefighters', 1.5, **{'in': 1.2}),                       # 143.5 firefighters on the line
    C('anon_grads', 1.5, **{'in': 0.3}),                             # 145 graduates under the confetti  "has a rendezvous
    C('anon_welder_2', 1.5, **{'in': 1.0}),                          # 146.5 sparks
    C('anon_wedding_2', 1.5),                                        # 148 the toast                          with destiny."
    C('now_police', 1.5),                                            # 149 shopping with a cop
    C('anon_volunteers', 1.5, **{'in': 0.5}),                        # 150.5 neighbors clear the storm
    C('nd_band', 2, alt=[('anon_volunteers', 1.4)]),                 # 152 the Notre Dame Marching Band  (beats 152-154: spliced in when it lands)
    C('anon_family', 1.5, **{'in': 1.4}),                            # 154.5 a Little Leaguer slides in
    C('now_builder', 1.25),                                          # 156 the ironworkers top out
    C('coast_guard', 1.25),                                          # 157.25 the rescue swimmer
    C('topgun_beach', 1.5, **{'in': 0.45}),                          # 158.5 Top Gun: Maverick, the beach game, a diving tackle at sunset
    C('olympians_2024_4', 0.5),                                      # 160 Caroline Marks in the barrel
    # 160-168: the last sung line
    C('fishermen_2', 1.5),                                           # 160 the catch  "Attaboy,"
    C('artemis_3', 2, **{'in': 1.4}),                                # 161.5 Orion's chutes open, home  "Clarence."
    C('bailey_family', 2, alt=[('dad_kid', 2.0)]),                   # 163.5 George home, his family in his arms (black and white)
    C('artemis_earth', 3.5, alt=[('earthrise', 0.0)], fx=dict(bloom=0.3)),  # 165.5 the Earth sets behind the Moon; the song stops dead at 168
]
# ---- the last ring; the girl reaches for the phone (the last shot holds before she picks it up)
END_TEXT = os.environ.get('CALL_TEXT', 'Your purpose is calling.')
END = [
    C('phone_reach', 8, speed=0.6, **{'in': 0.3}, text=[(3.4, END_TEXT, 50, 0.84, 'serif')]),
]

# Black and white until the rocket on the key change; from it on, color, except deliberate old references.
OLD_REFS = {'prevost_young', 'prevost_young_2', 'prevost_young_3', 'bailey_family', 'dad_kid', 'earthrise'}


def era(items):
    for it in items:
        path = it.get('clip') or it.get('photo')
        if not path:
            continue
        key = os.path.splitext(os.path.basename(path))[0][len(P):]
        it['fx'] = dict(it.get('fx', {}), sat=0.0 if key in OLD_REFS else COLOR['sat'])


era(FINALE)
SEQ = OPEN + LINES + M1 + WORK + LEGENDS + FINALE + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed %s: %.2f s' % (SONG_VERSION, make_bed()))
    b = 0.0
    marks = {id(OPEN[0]): 'OPEN', id(LINES[0]): 'LINES', id(M1[0]): 'MLK', id(WORK[0]): 'WORK',
             id(LEGENDS[0]): 'LEGENDS', id(FINALE[0]): 'FINALE', id(END[0]): 'END'}
    for s in SEQ:
        if id(s) in marks:
            print('%6.1f  %s' % (b, marks[id(s)]))
        b += s['beats']
    print('total %.1f beats = %.1f s; missing: %s' % (b, b * BEAT, sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
