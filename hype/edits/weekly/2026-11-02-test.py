"""Week 2 (test run, Nov 2): Sabaton - "Primo Victoria", 16:9.

Concept: D-Day to Monday morning. Normandy, the Arsenal of Democracy, modern
American builders (Mach Industries), DC, Chicago and Notre Dame, grit and sports,
ending on "PRIMO VICTORIA." (first victory) at the song's last hit.

Song: 124.17 BPM. The window starts on the downbeat where the band goes full
intensity for the final run (beat 442, 213.81 s) and ends on the last hit
(beat 510, 246.67 s = +68) plus a short ring-out: 71 beats, ~34.3 s.
Footage slots read media/<key>.*; alt=(key, in) borrows another clip until a slot lands.
text entries: (beat, text, size@720p, y[, style, end_beat])"""
import os

SONG = 'media/w1102_song.mp3'
BPM = 124.168
SONG_START = 213.814
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'w1102_'


def _find(key):
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.webm', 'clip'), ('.jpg', 'photo'), ('.png', 'photo')):
        path = os.path.join(HERE, 'media', P + key + ext)
        if os.path.exists(path):
            return kind, path
    return None, None


def C(key, label, desc, beats, alt=None, **kw):
    """Footage from media/w1102_<key>.*; if missing, an alternate clip (alt=(key, in)), else a labeled card."""
    kind, path = _find(key)
    if not path and alt:
        kind, path = _find(alt[0])
        if path:
            kw['in'] = alt[1]
    if path:
        kw.pop('p', None)
        return dict({kind: path}, beats=beats, **kw)
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop'):
        kw.pop(k, None)
    return dict(shot='slot', beats=beats, p=dict(label=label, desc=desc, kind='clip'), **kw)


def strobe(*items):
    """Half-beat cuts."""
    out = []
    for it in items:
        it = dict(it, beats=0.5)
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=10)
        out.append(it)
    return out


SEQ = [
    # +0  full intensity: D-Day, 2-beat holds
    C('dday_craft', 'D-DAY', 'Higgins boats racing in', 2),
    C('dday_ramp', 'D-DAY', 'ramp drops, troops surge out', 2),
    C('paratroopers', 'D-DAY', 'paratroopers jumping', 2),
    C('battleship', 'BATTLESHIP', 'broadside', 2),
    # +8  the Arsenal of Democracy
    C('willow_run', 'WILLOW RUN', 'B-24 assembly line', 2),
    C('liberty_ship', 'LIBERTY SHIP', 'launch down the ways', 2),
    C('rosie', 'ROSIE', 'riveting', 1),
    C('steel_pour_2', 'STEEL', 'molten pour', 1, alt=('steel_pour', 0.0)),
    C('b17', 'B-17', 'formation', 2),
    # +16  today's builders
    C('mach', 'MACH INDUSTRIES', 'test / factory', 2, alt=('rs25', 1.5)),
    C('sr71', 'SR-71', 'afterburner takeoff', 2),
    C('x15', 'X-15', 'drop and ignition', 1),
    C('rs25', 'RS-25', 'hot fire', 1),
    C('b21', 'B-21', 'first flight', 2, alt=('f35', 1.5)),
    # +24  Washington DC
    C('arlington_guard', 'ARLINGTON', 'changing of the guard', 2),
    C('capitol', 'CAPITOL', 'dome', 1),
    C('wash_monument', 'WASHINGTON MONUMENT', 'flags', 1),
    C('marine_one', 'MARINE ONE', 'liftoff', 2),
    C('wwii_memorial', 'WWII MEMORIAL', 'fountains and pillars', 2, alt=('wash_monument', 1.6)),
    # +32  his places
    C('chicago_skyline', 'CHICAGO', 'skyline', 2, crop=(0.0, 0.1, 0.88, 0.88)),
    C('chicago_L', 'CHICAGO', 'the L', 1),
    C('pope_leo', 'POPE LEO XIV', 'balcony', 1),
    C('golden_dome', 'NOTRE DAME', 'Golden Dome', 2, speed=0.75),
    C('nd_play', 'NOTRE DAME', 'big play', 2),
    # +40  half-beat strobe
    *strobe(C('battleship', 'BATTLESHIP', 'broadside', 1, **{'in': 1.5}),
            C('f35', 'F-35', 'afterburner', 1),
            C('steel_pour_2', 'STEEL', 'sparks', 1, **{'in': 1.0}),
            C('monster_truck', 'MONSTER TRUCK', 'backflip', 1),
            C('b17', 'B-17', 'formation', 1, **{'in': 1.5}),
            C('artemis', 'ARTEMIS', 'ignition', 1),
            C('dday_ramp', 'D-DAY', 'surf', 1, **{'in': 1.5}),
            C('rodeo', 'RODEO', 'out of the chute', 1)),
    # +44  grit, sports, space
    C('miracle_ice_2', 'MIRACLE ON ICE', 'the pile-on', 2, alt=('miracle_ice', 0.5)),
    C('cubs_2016', 'CUBS 2016', 'final out', 2),
    C('artemis', 'ARTEMIS', 'liftoff', 2, **{'in': 0.8}),
    C('monster_truck', 'MONSTER TRUCK', 'landing', 2, **{'in': 0.6}),
    C('f35', 'F-35', 'takeoff', 2, **{'in': 1.0}),
    C('mach_2', 'MACH INDUSTRIES', 'second shot', 2, alt=('sr71', 1.5)),
    # +56  one cut per beat
    C('rushmore', 'MOUNT RUSHMORE', 'aerial', 1, alt=('b21_2', 0.5)),
    C('statue_liberty', 'STATUE OF LIBERTY', 'torch', 1),
    C('rodeo', 'RODEO', 'ride', 1, **{'in': 1.0}),
    C('mach_3', 'MACH INDUSTRIES', 'Viper launch', 1, alt=('x15', 1.5), **{'in': 0.6}),
    # +60
    C('normandy_cemetery', 'NORMANDY', 'American Cemetery', 2),
    C('marine_one', 'MARINE ONE', 'second angle', 1, **{'in': 1.6}),
    C('arlington_guard', 'ARLINGTON', 'heel click', 1, **{'in': 1.6}),
    # +64  the flag goes up into the last hit
    C('iwo_flag', 'IWO JIMA', 'flag raising', 4),
    # +68  last hit (beat 510), then ring-out
    C('statue_liberty', 'STATUE OF LIBERTY', 'closing card', 3, dim=0.15, **{'in': 1.2},
      fx=dict(every=4, punch=0.06), text=[(0, 'PRIMO VICTORIA.', 150, 0.5)]),
]
