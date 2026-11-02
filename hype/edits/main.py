"""The main edit, 16:9, cut to the final chorus of Night of Passion (The Poodles).

The window starts on the downbeat where the band slams back in after the
breakdown (142.65 s), hits the key change 16 beats in (149.5 s), and ends on
the song's last hit (173.07 s, beat +71) with a short ring-out: 74 beats, ~31.7 s.

Footage slots are keyed to files in media/: media/<key>.mp4 (or .jpg/.png) renders
in place of its stand-in card. AI(...) slots use hype/generated/<key>.mp4 from
gen_video.py and fall back to the drawn shot.
text entries: (beat, text, size@720p, y[, style, end_beat])"""
import os

SONG = 'media/song.mp3'
BPM = 139.995
SONG_START = 142.646
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def C(key, label, desc, beats, fallback=None, **kw):
    """Footage from media/<key>.*; until it exists, the drawn `fallback` shot or a labeled card."""
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.webm', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
        path = os.path.join(HERE, 'media', key + ext)
        if os.path.exists(path):
            kw.pop('photo', None)
            kw.pop('p', None)
            return dict({kind: path}, beats=beats, **kw)
    kind = 'photo' if kw.pop('photo', False) else 'clip'
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop'):
        kw.pop(k, None)
    if fallback:
        return dict(shot=fallback, beats=beats, **kw)
    return dict(shot='slot', beats=beats, p=dict(label=label, desc=desc, kind=kind), **kw)


def AI(key, fallback, beats, **kw):
    """A generated-video clip (hype/generated/<key>.mp4) if it exists, otherwise the drawn shot."""
    path = os.path.join(HERE, 'generated', key + '.mp4')
    if os.path.exists(path):
        kw.pop('p', None)
        return dict(clip=path, beats=beats, **kw)
    kw.pop('in', None)
    return dict(shot=fallback, beats=beats, **kw)


def G(shot, beats, **kw):
    return dict(shot=shot, beats=beats, **kw)


def strobe(*items):
    """Half-beat cuts."""
    out = []
    for it in items:
        it = dict(it, beats=0.5)
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=10)
        out.append(it)
    return out


SEQ = [
    # +0  the slam back in after the breakdown: 2-beat holds
    C('rocky_summit', 'ROCKY IV', 'summit in the snow, arms up', 2, speed=0.6),
    C('nd_tunnel', 'NOTRE DAME', 'team storms out of the tunnel', 2),
    C('saturn_v', 'SATURN V', 'ignition + liftoff', 2),
    C('moon_flag', 'APOLLO', 'planting the flag on the Moon', 2),
    # +8
    C('flyover', 'FLYOVER', 'jets over a packed stadium', 2),
    C('nd_sign', 'NOTRE DAME', 'slapping the Play Like a Champion sign', 1),
    C('rocky_punch', 'ROCKY IV', 'haymaker on Drago', 1),
    C('ice', 'ICE', 'agents moving in, official footage', 1),
    C('drone', 'DRONE STRIKE', 'thermal footage, official release', 1),
    C('starship', 'STARSHIP', 'booster caught by the chopsticks', 2),
    # +16  KEY CHANGE: Washington
    AI('washington_trex', 'trex', 4, fx=dict(every=2, punch=0.06)),
    # +20
    C('b2', 'B-2', 'flyover, official footage', 1),
    C('bodybuilder_2', 'BODYBUILDER', 'second posing/lifting shot', 1),
    C('touchdown_jesus', 'NOTRE DAME', 'Touchdown Jesus', 2),
    # +24  frontier AI compute, then the extractions
    C('datacenter', 'AI LAB', 'server aisle / data center campus', 2, fallback='datacenter'),
    C('datacenter_2', 'AI LAB', 'GPU racks close-up', 2, fallback='datacenter'),
    C('maduro', 'MADURO', 'capture photo, official release', 2, photo=True, fit='contain', zoom=(1.0, 1.12),
      center=(0.5, 0.0)),
    C('saddam', 'SADDAM', 'spider-hole briefing diagram', 2, photo=True, fit='contain', zoom=(1.0, 1.1),
      center=(0.5, 0.5)),
    # +32  Lincoln
    AI('lincoln_chopper', 'chopper', 4, fx=dict(every=2, punch=0.05)),
    # +36
    C('top_gun', 'TOP GUN', 'carrier launch, afterburner at sunset', 2),
    C('rudy', 'RUDY', 'carried off the field', 2),
    # +40  half-beat strobe
    *strobe(C('nd_sign', 'NOTRE DAME', 'sign slap', 1, **{'in': 0.25}),
            C('flag', 'FLAG', 'giant flag', 1, fallback='flag'),
            C('drone_2', 'DRONE STRIKE', 'impact', 1),
            C('boom', 'EXPLOSION', 'huge fireball', 1, fallback='boom'),
            C('rocky_punch_2', 'ROCKY IV', 'punch', 1),
            C('flag_2', 'FLAG', 'giant flag, second shot', 1, fallback='flag'),
            C('shuttle', 'SHUTTLE', 'launch', 1),
            C('boom_2', 'EXPLOSION', 'second fireball', 1, fallback='boom')),
    # +44
    C('eagle', 'BALD EAGLE', 'talons out, slow-mo', 2, speed=0.85, crop=(0.3, 0.02, 0.6, 0.6), **{'in': 1.75}),
    C('creed', 'ROCKY IV', "Apollo's Living in America entrance", 2),
    C('iss', 'ISS', 'the station over Earth', 2),
    C('rocky_steps', 'ROCKY', 'top of the steps, arms raised', 2),
    # +52  Reagan
    AI('reagan_samurai', 'duel', 4, fx=dict(punch=0.05)),
    # +56  one cut per beat, then two-beat holds
    C('ice_2', 'ICE', 'second angle', 1),
    C('bodybuilder', 'BODYBUILDER', 'Arnold flexing on stage', 1),
    C('drago', 'ROCKY IV', 'Drago goes down', 1),
    C('nd_band', 'NOTRE DAME', 'band hits the Victory March', 1),
    C('t1000', 'T-1000', 'walks out of the fire', 2),
    C('rocky_beach', 'ROCKY III', 'Rocky and Apollo running on the beach', 2),
    # +64
    C('rocky_flag', 'ROCKY IV', 'wrapped in the flag', 3),
    # +67  end card over the fireworks; "NO BRAKES." lands on the song's last hit (+71), then rings out
    C('fireworks', 'FIREWORKS', 'finale barrage', 7, fallback='endcard', dim=0.1, stack=True,
      fx=dict(every=4, punch=0.05),
      text=[(0, '250 YEARS.', 150, 0.38), (4, 'NO BRAKES.', 150, 0.62)]),
]
