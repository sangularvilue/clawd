"""YOUR COUNTRY CALLS YOU. A 16:9, ~90 s montage in the spirit of the "Be Excellent." edit Will loved.

Mostly black-and-white archival film with grainy color payoffs; our pipe-organ Little Dark Age
(organ_songs/little_dark_age_score.json) runs lo-fi under nearly everything with real voices over it;
light-touch looks (duotone, echo trails, RGB drift, one mirror, bloom) and a few motion graphics
(signal rings on the phone rings, a voice trace). No on-screen text until the last line.

Seven plot lines are woven through it, each told start to finish ("soup to nuts"), one cut a beat
and coming back every few cuts:
  SOLDIER   the oath, recruits, doughboys, Marines, the Navy, the Huey ... the hat toss, the Old Guard
  BUILDER   high steel, Hoover Dam, the Model T line, welders ... the Pike takes off, Falcon lands
  EXPLORER  Lewis and Clark, the wagons, the Wrights, Edison, Feynman ... Apollo, Artemis, Earthrise
  ATHLETE   Bob Hayes, Ruth, Rockne, Ali ... the Miracle, the shot, the 2026 gold, Alysa Liu
  WORKER    the farmer, the lineman, the sweeper, miners, the WTC firefighters ... the Coast Guard
  FAMILY    mother and child, grace at the table, the teacher, the nurse, the preachers ... the girl
            who answers the phone (the last shot)
  LEGENDS   (under FDR) Washington, Lincoln, TR, Reagan, George Bailey, Mr. Smith, Kelly, Kane

Song bed (media/call_song_bed.wav, cut from the organ mix by make_bed() below; 97.5 BPM, beats):
  0-32 the third chorus (light registration), 32-41 the hook (two of its four bars spliced out),
  41-72 the verse, 72-104 the fourth chorus (plenum), all lo-fi; 102-104 silence while the shot is
  in the air; 104-136 the final chorus at full fidelity (tutti), 136- the closing chord rings out.
Voices: JFK's inaugural cut with a ringing phone (0-29), a chorus of American voices low (29-41),
MLK's street sweeper (41-72), FDR's rendezvous with destiny (73-85), George Bailey (86-92),
"Do you believe in miracles?" (97-102), Apollo 11's "Liftoff!" (106).
"""
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'call_'
BPM = 97.5
BEAT = 60 / BPM
SONG = 'media/call_song_bed.wav'
SONG_START = 0.0
DROP = 104
LOFI = dict(until=DROP, cutoff=2300, hp=170)
SILENCE = [(DROP - 2, DROP)]
FX = dict(sat=0.0, chroma=3, shake=4, punch=0.04)  # black-and-white unless a shot says otherwise
COLOR = dict(sat=1.05)

# the bed: recording beats of out/lda_score_organ.wav (beat grid phase 0.245 s): the third chorus
# (score bar 61, rec beat 273) to the hook, a two-bar cut inside the hook (308 -> 316, the closest
# self-similar pair), on to the end of the final chorus (bar 94 ends at 417), then the closing chord
# (bar 109, rec beat 481) to the end of the file.
BED_SRC = 'out/lda_score_organ.wav'
BED_SEGMENTS = [(273, 308), (316, 417), (481, None)]
BED_PHASE = 0.245


def make_bed(src=BED_SRC, out=SONG, xfade=0.03):
    import numpy as np
    import soundfile as sf
    x, sr = sf.read(os.path.join(HERE, src), dtype='float32')
    t = lambda rb: BED_PHASE + rb * BEAT
    nx = int(xfade * sr)
    ramp = np.linspace(0, 1, nx)[:, None]
    y = None
    for a, b in BED_SEGMENTS:
        i0 = int(round(t(a) * sr))
        seg = x[i0:int(round(t(b) * sr)) if b is not None else len(x)]
        if y is None:
            y = seg
        else:  # the outgoing segment fades out over the incoming one's last moments before its bar line
            lead = x[i0 - nx:i0]
            y = np.concatenate([y[:-nx], y[-nx:] * (1 - ramp) + lead * ramp, seg])
    sf.write(os.path.join(HERE, out), y, sr, subtype='PCM_24')
    return len(y) / sr


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
SCOPE = dict(kind='scope', y=0.88, amp=0.045, alpha=0.45)
DUO = dict(duotone=((16, 22, 52), (250, 236, 210)), duo_mix=0.5)

# ---------------------------------------------------------------- voices (beats; the music sits low under each)
VOICEOVER = []


def vo(key, at, src_in=0.0, dur=None, gain=1.0, duck=0.35):
    if have(key):
        VOICEOVER.append(dict(file=media(key), at=at, src_in=src_in, dur=dur or (_dur(os.path.join(HERE, media(key))) - src_in),
                              gain=gain, duck=duck))


vo('jfk_1', 6.0)                                   # "And so, my fellow Americans:"
vo('phone_ring', 10.2, src_in=0.0, dur=1.75, gain=0.8)
vo('jfk_2', 13.4)                                  # "ask not what your country can do for you;"
vo('phone_ring', 21.2, src_in=2.0, dur=1.8, gain=0.8)
vo('jfk_3', 24.4)                                  # "ask what you can do for your country."
SWEEP_AT = 41.5
vo('mlk_sweeper_short', SWEEP_AT, gain=1.0, duck=0.4)   # "...a street sweeper, ... like Michelangelo painted pictures."
PAYOFF_AT = 58.4
vo('mlk_sweeper_payoff', PAYOFF_AT, dur=8.45, gain=1.0, duck=0.4)  # "...Here lived a great street sweeper who swept his job well."
vo('fdr', 73.0, duck=0.4)                          # "This generation of Americans has a rendezvous with destiny."
vo('bailey_line', 86.4, gain=0.85, duck=0.5)       # "Merry Christmas, you wonderful old Building and Loan!"
vo('miracle_call', 97.3, gain=0.9, duck=0.6)       # "Do you believe in miracles? YES!"
vo('liftoff', DROP + 2.2, src_in=5.2, dur=2.3, gain=1.0, duck=0.8)  # "Liftoff! We have a liftoff!"

# the chorus of voices: short iconic lines tumbling over each other, low under the hook (hard to pick out on purpose)
_chorus = [k for k in ('v_teddy', 'v_eagle', 'v_ike_2', 'v_jfk_moon', 'v_ali', 'v_macarthur', 'v_sheen', 'v_graham',
                       'v_rockne', 'v_armstrong', 'lou_gehrig_line') if have(k)]
_at = 29.0
for k in _chorus:
    d = min(_dur(os.path.join(HERE, media(k))) or 1.5, 2.6)
    if _at + d / BEAT > SWEEP_AT - 0.3:
        break
    VOICEOVER.append(dict(file=media(k), at=_at, src_in=0.0, dur=d, gain=0.32, duck=1.0))
    _at += d / BEAT * 0.6

# ---------------------------------------------------------------- the plot lines (queues, in story order)
LABOR = [k for k in ('miners', 'steel', 'loggers', 'construction', 'railroad', 'roughnecks', 'fishermen', 'truckers',
                     'grocer', 'diner', 'seamstress', 'janitor', 'workers_3') if have_clip(k)]


def labor(i, beats, fallback, **kw):
    """The i-th labor shot the sourcing found, else a fallback."""
    if i < len(LABOR):
        return C(LABOR[i], beats, **kw)
    return C(fallback[0], beats, **dict(kw, **({'in': fallback[1]} if len(fallback) > 1 else {})))


SWEEPER = ('sweeper', 'janitor', ('workers_3', 0.0))

# ---- 0-6: dawn. No phone: the Capitol, and three lines wake up
COLD = [
    C('dc_capitol', 2, zoom=(1.0, 1.05)),
    C('farmer', 1.5, fx=dict(DUO)),                                  # WORKER
    C('lewis_clark', 1.5, alt=[('explorers', 0.0)]),                 # EXPLORER
    C('mother', 1),                                                  # FAMILY
]
# ---- 6-29: JFK, cut with the ringing phone (heard, never seen)
JFK = [
    C('jfk_bw', 4, mg=[SCOPE]),                                      # "And so, my fellow Americans"
    C('enlist', 1.5, mg=[RINGS], fx=dict(trail=0.3)),                 # SOLDIER: the oath   (ring)
    C('ironworkers', 2, fx=dict(DUO)),                               # BUILDER: high steel
    C('jfk', 5.5, mg=[SCOPE]),                                       # "ask not what your country can do for you"
    C('jfk_wide_2', 2, fx=dict(trail=0.35)),                         # the crowd
    C('owens', 1.5, mg=[RINGS]),                                     # ATHLETE: Bob Hayes  (ring)
    C('teacher', 1.5),                                               # FAMILY: the schoolroom
    C('jfk_bw', 3, **{'in': 1.6}, mg=[SCOPE]),                     # "ask what you can do for your country"
    C('jfk_wide', 2),                                                # the Capitol
]
# ---- 29-41: the hook, voices tumbling low; every line takes a step
HOOK = [
    C('enlist_2', 1),                                                # SOLDIER: recruits get their caps
    C('dam', 1),                                                     # BUILDER: the high scaler
    C('explorers', 1, alt=[('lewis_clark_2', 0.0)]),                 # EXPLORER: the wagons
    C('babe_ruth', 1),                                               # ATHLETE
    C('workers', 1),                                                 # WORKER: the lineman
    C('dad_kid', 1),                                                 # FAMILY: grace at the table
    C('doughboys', 1, fx=dict(trail=0.35)),                          # SOLDIER
    C('ironworkers_2', 1),                                           # BUILDER
    C('wright', 1),                                                  # EXPLORER: the Flyer, straight at us
    C('nd_rockne', 1),                                               # ATHLETE: Rockne
    labor(0, 1, ('workers_2', 0.0)),                                 # WORKER
    C('nurse', 1),                                                   # FAMILY
]
# ---- 41-72: MLK's street sweeper over the labor line, the other lines in between
s0 = SWEEP_AT
SWEEP = [
    labor(1, 2, ('workers_2', 1.0)),                                 # 41  "Even if it falls your lot..."
    C('ford', 1),                                                    # 43  BUILDER: the line
    C(SWEEPER[0], 2.5, alt=list(SWEEPER[1:]), mg=[SCOPE]),           # 44  "...to be a street sweeper,"
    C('edison', 1),                                                  # 46.5 EXPLORER
    labor(2, 2, ('workers_3', 1.5)),                                 # 47.5 "go out and sweep streets"
    C('marines', 1, fx=dict(drift=3)),                               # 49.5 SOLDIER
    C('workers_2', 2),                                               # 50.5 "like Michelangelo painted pictures": the welder's arc
    C('ali', 1),                                                     # 52.5 ATHLETE
    labor(3, 2, ('farmer', 2.0)),                                    # 53.5
    C('salk', 1),                                                    # 55.5 FAMILY: the healer
    labor(4, 2, ('workers', 2.0)),                                   # 56.5
    C(SWEEPER[0], 2, alt=list(SWEEPER[1:]), **{'in': 2.0}),          # 58.5 "Sweep streets so well..."
    C('dam_2', 1, fx=dict(mirror='h')),                              # 60.5 BUILDER
    labor(5, 2, ('workers_3', 2.5)),                                 # 61.5 "...the hosts of heaven and earth"
    C('einstein', 1),                                                # 63.5 EXPLORER: Feynman at the board
    labor(6, 1.5, ('farmer', 0.5)),                                  # 64.5 "will have to pause and say,"
    C('workers', 2, **{'in': 0.3}),                                  # 66  "Here lived a great..." the lineman against the sky
    C(SWEEPER[0], 2.5, alt=list(SWEEPER[1:]), **{'in': 1.0}),        # 68  "...street sweeper who swept his job well."
    C('navy', 1.5),                                                  # 70.5 SOLDIER
]
# ---- 72-104: the fourth chorus. FDR over the legends; George Bailey; the firefighters go in; the Miracle
LEGENDS = [
    C('fdr', 1, alt=[('dc_capitol_alt', 0.0)]),                      # 72
    C('washington', 2, mg=[SCOPE]),                                  # 73  "This generation of Americans"
    C('wright_2', 1),                                                # 75  EXPLORER
    C('lincoln', 1),                                                 # 76
    C('owens_2', 1),                                                 # 77  ATHLETE: Hayes hits the tape
    C('teddy', 1, fx=dict(trail=0.3)),                               # 78  "has a rendezvous"
    C('sheen', 1),                                                   # 79  FAMILY / faith
    C('reagan_wall', 1),                                             # 80  "with destiny."
    labor(7, 1, ('workers_3', 3.0)),                                 # 81  WORKER
    C('bailey_2', 1),                                                # 82  George faces the bank run
    C('vietnam_korea', 1, fx=dict(drift=2)),                         # 83  SOLDIER: the Huey
    C('peck_hepburn', 1),                                            # 84
    C('graham', 1),                                                  # 85  FAMILY / faith
    C('bailey', 3),                                                  # 86  "Merry Christmas, you wonderful old Building and Loan!"
    C('kelly', 1),                                                   # 89
    C('mr_smith', 1),                                                # 90
    C('welles_2', 1),                                                # 91
]
CALL = [  # 92-104: the call answered
    C('wtc_fdny', 2, alt=[('firefighters_2', 0.0)]),                 # 92  WORKER: toward the towers
    C('old_guard', 1),                                               # 94  SOLDIER
    C('wtc_fdny_2', 2, alt=[('firefighters', 0.0)]),                 # 95  WORKER
    C('mlk', 1),                                                     # 97  FAMILY / faith
    *strobe(C('miracle_call', 1),                                    # 98  "Do you believe in miracles? YES!" rapid fire in color
            C('hockey_2026', 1), C('phelps', 1), C('mach_2', 1), C('gabby', 1), C('retton', 1)),
    C('buzzer', 3, fx=dict(COLOR)),                                  # 101 the shot goes up ... 102-104 silence in the air
]
# ---- 104-136: the final chorus, full fidelity, every line pays off in color
FINALE = [
    C('buzzer', 2, fx=dict(COLOR, punch=0.12), **{'in': 2.0}),       # 104 ATHLETE: it goes in
    C('liftoff', 3, fx=dict(COLOR, hue=8, bloom=0.45), mg=[dict(RINGS, cy=0.8, alpha=0.22, period=1.1)]),  # 106 "Liftoff!"
    C('mission_control', 1, fx=dict(COLOR)),                         # 109
    C('mach', 2, fx=dict(COLOR, hue=6)),                             # 110 BUILDER: the Pike takes off
    C('hockey_2026_2', 1, alt=[('hockey_2026', 2.0)], fx=dict(COLOR)),  # 112 ATHLETE: the golden goal
    C('salute', 1, fx=dict(COLOR)),                                  # 113 SOLDIER
    C('wtc_fdny_3', 2, alt=[('firefighters_2', 1.5)], fx=dict(COLOR)),  # 114 WORKER
    C('alysa_liu', 1, fx=dict(COLOR)),                               # 116 ATHLETE
    C('kid_flag', 1, fx=dict(COLOR)),                                # 117 FAMILY
    C('artemis', 2, alt=[('liftoff_2', 0.0)], fx=dict(COLOR, bloom=0.35)),  # 118 EXPLORER: Artemis
    C('cadets', 1, fx=dict(COLOR)),                                  # 120 SOLDIER: the hat toss
    C('us_womens_hockey_2', 1, fx=dict(COLOR)),                      # 121 ATHLETE
    C('spacex', 1, fx=dict(COLOR, bloom=0.3), **{'in': 0.2}),        # 122 BUILDER: the booster lands
    C('dad_kid_alt', 1, fx=dict(COLOR)),                             # 123 FAMILY
    C('artemis_2', 2, alt=[('mission_control_2', 0.0)], fx=dict(COLOR)),  # 124 EXPLORER: the crew
    C('hockey_2026', 1, fx=dict(COLOR), **{'in': 1.2}),              # 126 ATHLETE: the goalie's gold
    C('coast_guard', 1, fx=dict(COLOR)),                             # 127 WORKER: the rescue swimmer
    C('aldrin', 2, fx=dict(COLOR), zoom=(1.0, 1.08)),                # 128 EXPLORER
    C('olympic_extra_2', 1, fx=dict(COLOR)),                         # 130 the flag goes up
    C('lewis_clark_2', 1, alt=[('artemis_3', 0.0), ('wright_2', 1.5)], fx=dict(COLOR)),  # 131 EXPLORER
    C('old_guard', 1, fx=dict(COLOR), **{'in': 1.5}),                # 132 SOLDIER
    C('earthrise', 3, fx=dict(COLOR, bloom=0.3), zoom=(1.0, 1.06)),  # 133 EXPLORER: Earthrise
]
# ---- 136-: the closing chord rings out; the girl answers the phone (the last shot)
END = [
    C('phone_2', 11, speed=0.6, **{'in': 0.3},
      text=[(4.2, 'Your Country Calls You.', 50, 0.84, 'serif')]),
]
SEQ = COLD + JFK + HOOK + SWEEP + LEGENDS + CALL + FINALE + END

if __name__ == '__main__':
    import sys
    if 'bed' in sys.argv:
        print('bed: %.2f s' % make_bed())
    b = 0.0
    marks = {id(COLD[0]): 'COLD', id(JFK[0]): 'JFK', id(HOOK[0]): 'HOOK', id(SWEEP[0]): 'SWEEP',
             id(LEGENDS[0]): 'LEGENDS', id(CALL[0]): 'CALL', id(FINALE[0]): 'FINALE', id(END[0]): 'END'}
    for s in SEQ:
        if id(s) in marks:
            print('%6.1f  %s' % (b, marks[id(s)]))
        b += s['beats']
    print('total %.1f beats = %.1f s; missing: %s' % (b, b * BEAT, sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
