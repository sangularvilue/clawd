"""The main edit: 30 s, 16:9. Durations are in beats.

Footage slots are keyed to files in media/: drop in media/<key>.mp4 (or .jpg/.png)
and that slot renders the footage instead of its stand-in card. Clips are trimmed
to start on the moment, so in= defaults to 0.
text entries: (beat, text, size@720p, y, style[, end_beat])"""
import os

BPM = 160  # placeholder until the song is in; the structure gets re-fit to its tempo
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def C(key, label, desc, beats, **kw):
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.webm', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
        path = os.path.join(HERE, 'media', key + ext)
        if os.path.exists(path):
            return dict({kind: path}, beats=beats, **kw)
    kind = 'photo' if kw.pop('photo', False) else 'clip'
    kw.pop('zoom', None), kw.pop('center', None), kw.pop('speed', None), kw.pop('in', None)
    return dict(shot='slot', beats=beats, p=dict(label=label, desc=desc, kind=kind), **kw)


def G(shot, beats, **kw):
    return dict(shot=shot, beats=beats, **kw)


def strobe(*items):
    """Half-beat cuts. Each item is a slot/shot dict; beats are overwritten."""
    out = []
    for it in items:
        it = dict(it)
        it['beats'] = 0.5
        it.setdefault('fx', {})
        it['fx'] = dict(it['fx'], punch=0.08, chroma=10)
        out.append(it)
    return out


USA = [(0, 'USA', 260, 0.5, 'usa')]
TERM_SHORT = [
    '$ ./train FREEDOM-1',
    'step 1776  loss 2.48',
    'step 1969  loss 0.00',
    'step 2026  loss -inf',
    'FREEDOM ACHIEVED',
]

SEQ = [
    # ---- the build: 2-beat holds
    C('rocky_summit', 'ROCKY IV', 'summit in the snow, arms up', 2, braam=True),
    C('nd_tunnel', 'NOTRE DAME', 'team storms out of the tunnel', 2),
    C('saturn_v', 'SATURN V', 'ignition + liftoff', 2),
    C('moon_flag', 'APOLLO', 'planting the flag on the Moon', 2,
      text=[(0.3, "THE MOON? WE'VE BEEN.", 96, 0.84, 'usa')]),

    # ---- first wave
    G('trex', 4, braam=True, fx=dict(every=2, punch=0.05),
      text=[(1, 'I CANNOT TELL A LIE', 92, 0.86, 'usa'), (2.5, 'THIS RULES', 130, 0.84, 'usa')]),
    C('flyover', 'FLYOVER', 'jets over a packed stadium', 2,
      text=[(0.5, 'SKY: CLAIMED', 130, 0.5, 'usa')]),
    C('nd_sign', 'NOTRE DAME', 'slapping the Play Like a Champion sign', 1),
    C('rocky_punch', 'ROCKY IV', 'haymaker on Drago', 1),
    G('chopper', 4, fx=dict(every=2, punch=0.05),
      text=[(0.5, 'FOUR SCORE AND', 92, 0.18, 'usa'), (2, 'SEVEN GEARS AGO', 104, 0.18, 'usa')]),
    C('ice', 'ICE', 'agents moving in, official footage', 1),
    C('drone', 'DRONE STRIKE', 'thermal footage, official release', 1),
    C('starship', 'STARSHIP', 'booster caught by the chopsticks', 2,
      text=[(0.4, 'WE CATCH ROCKETS NOW', 92, 0.84, 'usa')]),

    # ---- the AI section
    G('datacenter', 2, braam=True, fx=dict(punch=0.04, chroma=8),
      text=[(0.25, 'WE TAUGHT ROCKS\nTO THINK', 120, 0.5, 'usa')]),
    G('terminal', 3, p=dict(lines=TERM_SHORT, size=0.1, y=0.12), fx=dict(punch=0.02, shake=4, flash=0.3)),
    C('maduro', 'MADURO', 'capture photo, official release', 2, photo=True, zoom=(1.0, 1.25),
      text=[(0.4, 'EXTRACTION: COMPLETE', 100, 0.86, 'usa')]),
    G('boom', 1),

    # ---- second wave
    C('eagle', 'BALD EAGLE', 'talons out, slow-mo', 2, speed=0.5),
    C('fireworks', 'FIREWORKS', 'finale barrage', 2),
    C('game', 'VIDEO GAME', 'Senator Armstrong, Metal Gear Rising', 2,
      text=[(0.5, 'NANOMACHINES, SON.', 110, 0.84, 'usa')]),
    C('b2', 'B-2', 'flyover, official footage', 2),
    C('rudy', 'RUDY', 'carried off the field', 2,
      text=[(0.3, 'RUDY! RUDY! RUDY!', 110, 0.84, 'usa')]),
    C('creed', 'ROCKY IV', "Apollo's Living in America entrance", 2),

    # ---- peak: half-beat strobe, then the presidents again
    *strobe(C('nd_sign_2', 'NOTRE DAME', 'sign slap', 1), G('flag', 1, text=USA),
            C('drone', 'DRONE STRIKE', 'impact', 1, **{'in': 1.5}), G('boom', 1, text=USA),
            C('rocky_punch_2', 'ROCKY IV', 'punch', 1), G('flag', 1, p=dict(t0=2), text=USA),
            C('shuttle', 'SHUTTLE', 'launch', 1, **{'in': 1.0}), G('boom', 1, p=dict(booms=[(0.3, 0.6, 260, 0), (0.75, 0.5, 300, 0.05)]))),
    G('trex', 2, p=dict(), fx=dict(punch=0.07)),
    G('chopper', 2, fx=dict(punch=0.07)),

    # ---- third wave: one cut per beat
    C('touchdown_jesus', 'NOTRE DAME', 'Touchdown Jesus', 2, braam=True),
    C('ice_2', 'ICE', 'second angle', 1),
    C('blue_angels', 'BLUE ANGELS', 'diamond formation', 1),
    C('rocky_steps', 'ROCKY', 'top of the steps, arms raised', 2),
    C('shuttle_2', 'SHUTTLE', 'liftoff, wide', 2),
    C('drago', 'ROCKY IV', 'Drago goes down', 1),
    C('nd_band', 'NOTRE DAME', 'band hits the Victory March', 1),
    C('starship_2', 'STARSHIP', 'second angle', 1),
    C('drone_2', 'DRONE STRIKE', 'second strike', 1),
    C('game_2', 'VIDEO GAME', 'boss fight', 1),
    C('b2_2', 'B-2', 'second pass', 1),
    G('datacenter', 1, fx=dict(chroma=10)),
    C('moon_flag_2', 'APOLLO', 'moonwalk', 1),
    *strobe(G('flag', 1, text=USA), G('boom', 1, text=USA), G('flag', 1, p=dict(t0=1), text=USA), G('boom', 1)),

    # ---- finale
    C('rocky_flag', 'ROCKY IV', 'wrapped in the flag', 4, braam=True, fx=dict(every=2),
      text=[(1, 'YO ADRIAN.', 120, 0.84, 'usa'), (2.5, 'WE DID IT.', 130, 0.84, 'usa')]),
    G('endcard', 6, braam=True, screech=0.5, stack=True, fx=dict(every=2, punch=0.04),
      text=[(0, '250 YEARS.', 170, 0.36, 'usa'), (2, 'NO BRAKES.', 170, 0.64, 'usa')]),
]
