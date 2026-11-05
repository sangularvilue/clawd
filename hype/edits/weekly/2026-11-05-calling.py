"""YOUR COUNTRY IS CALLING. A 16:9, ~92 s montage in the spirit of the "Be Excellent." edit Will loved.

Mostly black-and-white archival film with grainy color payoffs; Little Dark Age (the original recording,
vocals 6 dB down; or our pipe-organ version) runs lo-fi under nearly everything with real voices over it;
light-touch looks (duotone, echo trails, RGB drift, one mirror, bloom) and signal rings when the phone
rings. No on-screen text until the last line.

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
DROP = 96
STOP = 136  # the song's last chord cuts off here (the organ version rings a closing chord instead)
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
    'orig': dict(segments=[(281, 308), (316, 417), (473, 485)], vocals_db=-6.0, pitch=0),
    'orig_m2': dict(segments=[(281, 308), (316, 417), (473, 485)], vocals_db=-6.0, pitch=-2),
    'orig_p1': dict(segments=[(281, 308), (316, 417), (473, 485)], vocals_db=-6.0, pitch=1),
    # a whole step down until the final chorus, then up to the record's own key on its downbeat (just before
    # "I grieve in stereo"): a key-change lift into the payoff, on the same beat the lo-fi opens up
    'orig_lift': dict(segments=[(281, 308), (316, 417), (473, 485)], vocals_db=-6.0, pitch=-2, pitch_until=96),
    'organ': dict(segments=[(281, 308), (316, 417), (481, None)], src='out/lda_score_organ.wav'),
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
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=8, **COLOR)
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


vo('phone_ring', 0.0, src_in=0.0, dur=1.75, gain=0.85, duck=0.6)    # the call
vo('jfk_1', 3.0)                                   # "And so, my fellow Americans:"
vo('jfk_2', 7.2)                                   # "ask not what your country can do for you;"
vo('jfk_3', 15.2)                                  # "ask what you can do for your country."
vo('phone_ring', 19.8, src_in=2.0, dur=1.8, gain=0.85, duck=0.6)   # ... it rings again
MLK1 = 33.5
vo('mlk_part1', MLK1, gain=1.0, duck=0.4)          # "Even if it falls your lot to be a street sweeper, go out and sweep streets like Michelangelo painted pictures."
vo('phone_ring', 47.4, src_in=0.0, dur=1.75, gain=0.8, duck=0.6)   # the pause
MLK2 = 52.3
vo('mlk_part2', MLK2, gain=1.0, duck=0.4)          # "Sweep streets so well that all the hosts of heaven and earth will pause and say, Here lived a great street sweeper who swept his job well."
vo('fdr', 66.3, duck=0.4)                          # "This generation of Americans has a rendezvous with destiny."
vo('bailey_live', 78.0, gain=1.1, duck=0.35)       # "I want to live again!" (George on screen for it)
vo('miracle_call', 91.6, gain=0.9, duck=0.6)       # "Do you believe in miracles? YES!"
vo('liftoff', DROP + 0.4, src_in=5.2, dur=2.3, gain=1.0, duck=0.8)  # "Liftoff! We have a liftoff!"
vo('bailey_clarence', STOP + 0.6, gain=1.0, duck=1.0)  # "Attaboy, Clarence." (heard, not seen)
END_AT = 139.0
vo('phone_ring', END_AT - 0.4, src_in=0.0, dur=2.7, gain=0.9, duck=1.0)  # rings until she lifts the receiver

# the chorus of voices: short iconic lines tumbling over each other, low (hard to pick out on purpose)
_chorus = [k for k in ('v_teddy', 'v_eagle', 'v_ike_2', 'v_jfk_moon', 'v_ali', 'v_macarthur', 'v_sheen', 'v_graham',
                       'v_rockne', 'v_armstrong') if have(k)]
_at = 23.0
for k in _chorus:
    d = min(_dur(os.path.join(HERE, media(k))) or 1.5, 2.6)
    if _at + d / BEAT > MLK1 - 0.3:
        break
    VOICEOVER.append(dict(file=media(k), at=_at, src_in=0.0, dur=d, gain=0.32, duck=1.0))
    _at += d / BEAT * 0.6

# ---------------------------------------------------------------- picture
LABOR = [k for k in ('miners', 'steel', 'loggers', 'construction', 'railroad', 'roughnecks', 'fishermen', 'truckers',
                     'grocer', 'diner', 'seamstress', 'janitor') if have_clip(k)]


def labor(i, beats, fallback, **kw):
    """The i-th labor shot the sourcing found, else a fallback (key, in)."""
    if i < len(LABOR):
        return C(LABOR[i], beats, **kw)
    return C(fallback[0], beats, **dict(kw, **{'in': fallback[1]}))


SWEEP_ALT = [('janitor', 0.0), ('workers_3', 0.0)]

# ---- 0-23: the phone rings over teenagers who haven't had the call yet; JFK straight away; it rings again
OPEN = [
    C('teens', 1.5),                                                 # 0   ring: a bored boy flops back on his bed
    C('teens_2', 1.5, **{'in': 0.7}),                                # 1.5 the soda fountain
    C('jfk_bw', 3.5),                                                # 3   "And so, my fellow Americans:"
    C('teens_3', 1, **{'in': 0.3}),                                  # 6.5 a shop student daydreams
    C('jfk', 5),                                                     # 7.5 "ask not what your country can do for you;"
    C('jfk_wide_2', 2, fx=dict(trail=0.35)),                         # 12.5 the crowd
    C('teens_4', 1, alt=[('teens_alt', 0.0)]),                       # 14.5 a girl alone on the porch steps
    C('jfk_bw', 4, **{'in': 1.6}),                                   # 15.5 "ask what you can do for your country."
    C('enlist', 1.5, mg=[RINGS], fx=dict(trail=0.3)),                 # 19.5 SOLDIER: the oath   (ring)
    C('ironworkers', 1.5, mg=[RINGS], fx=dict(DUO)),                 # 21  BUILDER: high steel
]
# ---- 22.5-33.5: every line takes its first steps; voices tumbling low
LINES = [
    C('lewis_clark_2', 1, alt=[('explorers', 0.0)]),                 # EXPLORER: the keelboat heads up the Missouri
    C('owens', 1),                                                   # ATHLETE: Bob Hayes
    C('farmer', 1, fx=dict(DUO)),                                    # WORKER
    C('mother', 1),                                                  # FAMILY
    C('enlist_2', 1),                                                # SOLDIER: recruits get their caps
    C('dam', 1),                                                     # BUILDER: the high scaler
    C('explorers', 1),                                               # EXPLORER: the wagons
    C('babe_ruth', 1),                                               # ATHLETE
    C('workers', 1),                                                 # WORKER: the lineman
    C('dad_kid', 1),                                                 # FAMILY: grace at the table
    C('doughboys', 1, fx=dict(trail=0.35)),                          # SOLDIER
]
# ---- 33.5-52.3: MLK, the street sweeper, each phrase on screen as he says it ... then a pause, and the phone
M1 = [
    C('mlk', 1.5),                                                   # 33.5 "Even if it falls..."
    labor(0, 2.4, ('workers_2', 0.0)),                               # 35  "...your lot to be a"
    C('sweeper', 1.8, alt=SWEEP_ALT),                                # 37.4 "street sweeper,"
    C('sweeper_2', 1.4, alt=[('sweeper', 1.8)] + SWEEP_ALT),         # 39.2 "go out and"
    C('sweeper', 2.0, alt=SWEEP_ALT, **{'in': 1.8}),                 # 40.6 "sweep streets"
    C('michelangelo', 3.8, alt=[('workers_2', 1.0)], zoom=(1.0, 1.12)),  # 42.6 "like Michelangelo painted pictures."
    C('ford', 1),                                                    # 46.4 BUILDER: the line
    C('marines', 1, fx=dict(drift=3), mg=[RINGS]),                   # 47.4 SOLDIER         (ring)
    C('wright', 1, mg=[RINGS]),                                      # 48.4 EXPLORER
    C('ali', 1),                                                     # 49.4 ATHLETE
    C('nurse', 1),                                                   # 50.4 FAMILY
    C('dam_2', 0.9, fx=dict(mirror='h')),                            # 51.4 BUILDER
]
M2 = [
    C('sweeper_2', 2.1, alt=[('sweeper', 2.5)] + SWEEP_ALT, **{'in': 1.5}),  # 52.3 "Sweep streets so well"
    C('heaven', 1.6, alt=[('dc_capitol', 0.5)]),                     # 54.4 "that all the hosts of heaven"
    C('wayne_alt', 0.9),                                             # 56  "and earth"
    C('pause', 2.1, alt=[('jfk_wide_2', 2.0)]),                      # 56.9 "will pause and say,"
    C('sweeper', 4.2, alt=SWEEP_ALT, **{'in': 0.6}),                 # 59  "Here lived a great street sweeper"
    labor(1, 2.2, ('workers', 2.0)),                                 # 63.2 "who swept his job well."
    C('navy', 0.6),                                                  # 65.4 SOLDIER
]
# ---- 66-96: the fourth chorus. FDR over the legends; George Bailey; the firefighters go in; the Miracle
LEGENDS = [
    C('fdr', 1, alt=[('dc_capitol_alt', 0.0)]),                      # 66
    C('washington', 2),                                              # 67  "This generation of Americans"
    C('wright_2', 1),                                                # 69  EXPLORER
    C('lincoln', 1),                                                 # 70
    C('owens_2', 1),                                                 # 71  ATHLETE: Hayes hits the tape
    C('teddy', 1, fx=dict(trail=0.3)),                               # 72  "has a rendezvous"
    C('sheen', 1),                                                   # 73  FAMILY / faith
    C('reagan_wall', 1),                                             # 74  "with destiny."
    labor(2, 1, ('workers_3', 3.0)),                                 # 75  WORKER
    C('bailey_2', 1),                                                # 76  George faces the bank run
    C('vietnam_korea', 1, fx=dict(drift=2)),                         # 77  SOLDIER: the Huey
    C('bailey_live', 1.65, alt=[('bailey', 0.0)]),                   # 78  George on the bridge: "I want to live again!"
    C('kelly', 1.35),                                                # 79.65
    C('mr_smith', 1),                                                # 81
    C('peck_hepburn', 1),                                            # 82
    C('graham', 1),                                                  # 83  FAMILY / faith
    C('welles_2', 1),                                                # 84
    C('lou_gehrig', 1),                                              # 85  ATHLETE
    C('wtc_fdny', 2, alt=[('firefighters_2', 0.0)]),                 # 86  WORKER: 9/11, Engine 21 down West Street
    C('wtc_fdny_2', 2, alt=[('firefighters', 0.0)], **{'in': 1.8}),  # 88  a rig heads downtown, the towers ahead
    C('wtc_fdny_3', 2, **{'in': 0.3}),                               # 90  an Engine 28 firefighter climbs the North Tower stairs
    C('miracle_call', 1, fx=dict(COLOR)),                            # 92  "Do you believe in miracles?"
    *strobe(C('hockey_2026', 1), C('phelps', 1), C('mach_2', 1),     # 93  "YES!" rapid fire in color
            C('gabby', 1), C('retton', 1), C('us_womens_hockey', 1)),
]
# ---- 96-136: the final chorus, full fidelity, every line pays off in color; the song stops dead at 136
FINALE = [
    C('liftoff', 3, fx=dict(COLOR, hue=8, bloom=0.45, punch=0.12), mg=[dict(RINGS, cy=0.8, alpha=0.22, period=1.1)]),  # 96 "Liftoff!"
    C('mission_control', 1, fx=dict(COLOR)),                         # 99
    C('mach', 2, fx=dict(COLOR, hue=6)),                             # 100 BUILDER: the Pike takes off
    C('hockey_2026_2', 1, alt=[('hockey_2026', 2.0)], fx=dict(COLOR)),  # 102 ATHLETE: the golden goal
    C('salute', 1, fx=dict(COLOR)),                                  # 103 SOLDIER
    C('wtc_fdny', 2, alt=[('firefighters_2', 1.5)], fx=dict(COLOR), **{'in': 2.2}),  # 104 WORKER: Engine 21 roars past
    C('alysa_liu', 1, fx=dict(COLOR)),                               # 106 ATHLETE
    C('kid_flag', 1, fx=dict(COLOR)),                                # 107 FAMILY
    C('artemis', 2, alt=[('liftoff_2', 0.0)], fx=dict(COLOR, bloom=0.35), **{'in': 1.8}),  # 108 EXPLORER: Artemis II lifts off
    C('cadets', 1, fx=dict(COLOR)),                                  # 110 SOLDIER: the hat toss
    C('us_womens_hockey_2', 1, fx=dict(COLOR)),                      # 111 ATHLETE
    C('spacex', 1, fx=dict(COLOR, bloom=0.3), **{'in': 0.2}),        # 112 BUILDER: the booster lands
    C('dad_kid_alt', 1, fx=dict(COLOR)),                             # 113 FAMILY
    C('artemis_2', 2, alt=[('mission_control_2', 0.0)], fx=dict(COLOR), **{'in': 2.3}),  # 114 EXPLORER: the crew waves
    C('hockey_2026', 1, fx=dict(COLOR), **{'in': 1.2}),              # 116 ATHLETE: the goalie's gold
    C('coast_guard', 1, fx=dict(COLOR)),                             # 117 WORKER: the rescue swimmer
    C('phelps_2', 1, fx=dict(COLOR)),                                # 118 ATHLETE
    C('bailey_harry', 1, alt=[('enlist', 2.0)], fx=dict(COLOR)),     # 119 SOLDIER: Harry Bailey home in his Navy uniform
    C('olympic_extra_2', 1, fx=dict(COLOR)),                         # 120 the flag goes up
    C('firefighters_2', 1, fx=dict(COLOR)),                          # 121 WORKER
    C('kid_flag_alt', 1, fx=dict(COLOR)),                            # 122 FAMILY
    C('artemis_3', 1, fx=dict(COLOR), **{'in': 1.4}),                # 123 EXPLORER: Orion's chutes open, home
    C('aldrin', 2, fx=dict(COLOR), zoom=(1.0, 1.08)),                # 124 EXPLORER
    C('gabby_2', 1, fx=dict(COLOR)),                                 # 126 ATHLETE
    C('mission_control_2', 1, fx=dict(COLOR)),                       # 127 EXPLORER: task accomplished
    # 128-136: the last sung line, a slower close on each line's last image
    C('old_guard', 1.5, fx=dict(COLOR), **{'in': 1.5}),              # 128 SOLDIER
    C('sweeper_2', 1.5, alt=[('sweeper', 2.8)] + SWEEP_ALT, fx=dict(COLOR), **{'in': 2.6}),  # 129.5 WORKER
    C('lewis_clark', 1.5, fx=dict(COLOR), fit='cover', zoom=(1.04, 1.0)),  # 131 EXPLORER: Lewis and Clark reach the Pacific
    C('bailey_family', 2, alt=[('dad_kid', 2.0)]),                   # 132.5 FAMILY: George home, his family in his arms
    C('earthrise', END_AT - 134.5, fx=dict(COLOR, bloom=0.3), zoom=(1.0, 1.08)),  # 134.5 Earthrise; the song stops; "Attaboy, Clarence."
]
# ---- the last ring; the girl answers it (the last shot)
END = [
    C('phone_2', 11, speed=0.6, text=[(6.4, 'Your country is calling.', 50, 0.84, 'serif')]),
]
SEQ = OPEN + LINES + M1 + M2 + LEGENDS + FINALE + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed %s: %.2f s' % (SONG_VERSION, make_bed()))
    b = 0.0
    marks = {id(OPEN[0]): 'OPEN', id(LINES[0]): 'LINES', id(M1[0]): 'MLK 1', id(M2[0]): 'MLK 2',
             id(LEGENDS[0]): 'LEGENDS', id(FINALE[0]): 'FINALE', id(END[0]): 'END'}
    for s in SEQ:
        if id(s) in marks:
            print('%6.1f  %s' % (b, marks[id(s)]))
        b += s['beats']
    print('total %.1f beats = %.1f s; missing: %s' % (b, b * BEAT, sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
