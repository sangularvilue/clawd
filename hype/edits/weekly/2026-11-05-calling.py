"""YOUR COUNTRY IS CALLING. A 16:9 montage in the spirit of the "Be Excellent." edit Will loved.

Mostly black-and-white archival film with grainy color payoffs; our pipe-organ Little Dark Age
(organ_songs/little_dark_age_score.json) runs lo-fi under nearly everything with real voices over it;
light-touch looks (duotone, echo trails, RGB drift, one mirror, bloom) and a few motion graphics
(signal rings, a voice trace, a typed caption).

Shape (beats at 97.5 BPM; beat 0 = the song's instrumental hook at 3:07.9):
  0-8    the call: switchboard, a ringing phone, Uncle Sam. "Your country is calling." types on.
  8-32   JFK's inaugural cut back and forth with the phone: "And so, my fellow Americans" / ring /
         "ask not what your country can do for you" / ring / "ask what you can do for your country."
  32-60  the callings, one cut a beat, a one-word serif caption every bar (build, serve, teach, heal,
         invent, compete, protect), a chorus of American voices low underneath.
  60-72  FDR, "This generation of Americans has a rendezvous with destiny," over presidents and families.
  72-78  rapid fire in color: the Olympians and the payoffs, Al Michaels' "Do you believe in miracles?"
  77-80  the shot is up... and the song drops out (silence while the ball is in the air)
  80-97  it goes in: the final chorus at full fidelity (the organ's tutti), "Liftoff! We have a liftoff!",
         Earthrise under "Answer the call.", and a hand picks up the phone.
"""
import glob
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'call_'
SONG = 'media/call_song_lda.wav'
BPM = 97.5
BEAT = 60 / BPM
SONG_START = 187.937  # rec beat 305: the downbeat of the hook (score bar 69); the final chorus lands on edit beat 80
DROP = 80
LOFI = dict(until=DROP, cutoff=2300, hp=170)
SILENCE = [(78, DROP), (96.2, 99)]
FX = dict(sat=0.0, chroma=3, shake=4, punch=0.04)  # black-and-white unless a shot says otherwise
COLOR = dict(sat=1.05)


def _find(key):
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
        path = os.path.join(HERE, 'media', P + key + ext)
        if os.path.exists(path):
            return kind, path
    return None, None


def C(key, label, beats, alt=None, **kw):
    """Footage from media/call_<key>.*; else an alternate (alt=(key, in)), else a labeled card."""
    kind, path = _find(key)
    if not path and alt:
        kind, path = _find(alt[0])
        if path:
            kw['in'] = alt[1]
    if path:
        if kind == 'photo':
            for k in ('in', 'speed', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
                kw.pop(k, None)
        return dict({kind: path}, beats=beats, **kw)
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck', 'mg'):
        kw.pop(k, None)
    return dict(shot='slot', beats=beats, p=dict(label=label, desc=key, kind='clip'), **kw)


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


RINGS = dict(kind='rings', cx=0.5, cy=0.52, period=0.8, n=3, alpha=0.42)
SCOPE = dict(kind='scope', y=0.88, amp=0.045, alpha=0.5)
DUO = dict(duotone=((16, 22, 52), (250, 236, 210)), duo_mix=0.5)
CAP = lambda word: [(0, word, 34, 0.86, 'serif')]

# ---------------------------------------------------------------- voices (beats; music sits low under each)
VOICEOVER = []


def vo(key, at, src_in=0.0, dur=None, gain=1.0, duck=0.35):
    if have(key):
        VOICEOVER.append(dict(file=media(key), at=at, src_in=src_in, dur=dur or (_dur(os.path.join(HERE, media(key))) - src_in),
                              gain=gain, duck=duck))


vo('phone_ring', 0.3)
vo('jfk_1', 8.0)
vo('phone_ring', 12.2, src_in=0.0, dur=1.75)
vo('jfk_2', 15.4)
vo('phone_ring', 23.4, src_in=2.0, dur=1.8)
vo('jfk_3', 26.6)
vo('fdr', 60.2, duck=0.4)
vo('miracle_call', 72.2, gain=0.9, duck=0.6)
vo('liftoff', DROP + 0.4, src_in=5.2, dur=2.3, gain=1.0, duck=0.8)

# the chorus of voices: short iconic lines one after another, low under the callings (hard to pick out on purpose)
_chorus = [k for k in ('v_eagle', 'v_ike', 'v_teddy', 'mlk', 'v_ali', 'bailey_line', 'v_valvano', 'v_jfk_moon',
                       'v_sheen', 'v_graham', 'lou_gehrig_line', 'v_armstrong', 'reagan_brave', 'v_lombardi', 'v_macarthur',
                       'v_truman') if have(k)]
_at = 33.0
for k in _chorus:
    d = _dur(os.path.join(HERE, media(k))) or 1.5
    if _at + d / BEAT > 59.5:
        break
    VOICEOVER.append(dict(file=media(k), at=_at, src_in=0.0, dur=min(d, 2.6), gain=0.24, duck=1.0))
    _at += min(d, 2.6) / BEAT * 0.8  # a little overlap, like a crowd of history talking

# ---------------------------------------------------------------- picture
COLD = [
    C('typewriter', 'SWITCHBOARD', 2, **{'in': 0.4}),
    C('phone', 'THE PHONE', 2, **{'in': 0.3}, mg=[RINGS]),
    C('uncle_sam', 'UNCLE SAM', 4, fit='contain', zoom=(1.0, 1.06), mg=[dict(RINGS, cy=0.45, alpha=0.3)],
      text=[(0.3, 'Your country is calling.', 40, 0.9, 'serif-type')]),
]
JFK = [
    C('jfk_bw', 'JFK', 4, mg=[SCOPE]),
    C('phone', 'THE PHONE', 3, **{'in': 1.4}, mg=[RINGS], fx=dict(trail=0.3)),
    C('jfk', 'JFK', 4, mg=[SCOPE]),
    C('jfk_wide_2', 'THE CROWD', 2, fx=dict(trail=0.35)),
    C('jfk_wide', 'THE CAPITOL', 2),
    C('typewriter_2', 'SWITCHBOARD', 3, alt=('typewriter', 1.6), mg=[RINGS]),
    C('enlist', 'THE OATH', 2, fx=dict(trail=0.3)),
    C('enlist_2', 'RECRUITS', 2),
    C('revolution', 'THE DELAWARE', 2, zoom=(1.0, 1.08)),
]
CALLINGS = [
    # build
    C('ironworkers', 'IRONWORKERS', 1, fx=dict(DUO), text=CAP('build.')),
    C('dam_2', 'HOOVER DAM', 1, fx=dict(mirror='h')),
    C('ford', 'MODEL T', 1),
    C('mach', 'MACH', 1, fx=dict(COLOR, hue=6)),
    # serve
    C('doughboys', 'DOUGHBOYS', 1, fx=dict(trail=0.35), text=CAP('serve.')),
    C('marines', 'MARINES', 1, fx=dict(drift=3)),
    C('navy', 'THE NAVY', 1),
    C('vietnam_korea', 'HUEY', 1, fx=dict(drift=2)),
    # teach
    C('teacher', 'TEACHER', 1, text=CAP('teach.')),
    C('sheen', 'SHEEN', 1),
    C('einstein', 'FEYNMAN', 1),
    C('barron', 'BARRON', 1),
    # heal
    C('salk', 'SALK', 1, text=CAP('heal.')),
    C('salk_2', 'VACCINES', 1),
    C('nurse', 'NURSES', 1),
    C('chaplain', 'CHAPLAIN', 1, fx=dict(DUO)),
    # invent
    C('wright', 'THE WRIGHTS', 1, text=CAP('invent.')),
    C('edison', 'EDISON', 1),
    C('jobs', 'JOBS', 1),
    C('spacex', 'FALCON', 1, fx=dict(COLOR, bloom=0.35), **{'in': 2.4}),
    # compete
    C('babe_ruth', 'BABE RUTH', 1, text=CAP('compete.')),
    C('ali', 'ALI', 1),
    C('owens', 'BOB HAYES', 1),
    C('secretariat', 'SECRETARIAT', 1, fx=dict(COLOR)),
    # protect
    C('police', 'POLICE', 1, text=CAP('protect.')),
    C('firefighters', 'FIREFIGHTERS', 1),
    C('old_guard', 'THE OLD GUARD', 1),
    C('coast_guard', 'COAST GUARD', 1),
]
GENERATIONS = [  # FDR: "This generation of Americans has a rendezvous with destiny." Presidents, families, the movies
    C('washington', 'WASHINGTON', 1, fit='contain', zoom=(1.0, 1.05), mg=[SCOPE]),
    C('lincoln', 'LINCOLN', 1, fit='contain', zoom=(1.0, 1.05)),
    C('teddy', 'TEDDY', 1, fx=dict(trail=0.3)),
    C('reagan_wall', 'REAGAN', 1),
    C('dad_kid', 'GRACE', 1),
    C('workers', 'LINEMAN', 1),
    C('farmer', 'FARMER', 1, fx=dict(DUO)),
    C('bailey', 'GEORGE BAILEY', 1.5),
    C('peck_hepburn', 'ROMAN HOLIDAY', 1),
    C('mr_smith', 'MR. SMITH', 1),
    C('kelly', 'SINGIN IN THE RAIN', 1),
    C('kid_flag', 'THE FLAG', 0.5),
]
RAPID = strobe(
    C('hockey_2026', 'HOCKEY 2026', 1), C('alysa_liu', 'ALYSA LIU', 1), C('miracle_call', 'MIRACLE', 1),
    C('phelps', 'PHELPS', 1), C('gabby', 'GABBY', 1), C('cadets', 'CADETS', 1),
    C('mach_2', 'MACH', 1, **{'in': 0.6}), C('us_womens_hockey', 'GOLD 2018', 1), C('retton', 'RETTON', 1),
    C('mission_control_2', 'MISSION CONTROL', 1),
)
SHOT = [C('buzzer', 'THE SHOT', 3, fx=dict(COLOR))]  # 77-80: release, then the silence while it's in the air
FINALE = [
    C('buzzer', 'IT GOES IN', 2, fx=dict(COLOR, punch=0.12), **{'in': 2.0}),
    C('liftoff', 'LIFTOFF', 3, fx=dict(COLOR, hue=8, bloom=0.45), mg=[dict(RINGS, cy=0.8, alpha=0.25, period=1.1)]),
    C('mission_control', 'MISSION CONTROL', 2, fx=dict(COLOR)),
    C('hockey_2026_2', 'HOCKEY 2026', 2, alt=('hockey_2026', 2.0), fx=dict(COLOR)),
    C('aldrin', 'ALDRIN', 2, fit='contain', zoom=(1.0, 1.08), fx=dict(COLOR)),
    C('earthrise', 'EARTHRISE', 4.2, fit='contain', zoom=(1.0, 1.06), fx=dict(COLOR, bloom=0.3),
      text=[(0.6, 'Answer the call.', 44, 0.86, 'serif')]),
    C('phone_2', 'PICK UP', 2, **{'in': 0.5}),
]
SEQ = COLD + JFK + CALLINGS + GENERATIONS + RAPID + SHOT + FINALE
