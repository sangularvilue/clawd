"""Week 4 (Nov 9): "PLAY LIKE A CHAMPION." Sousa's "The Stars and Stripes Forever", 16:9.

Concept: Reagan as George Gipp (Knute Rockne, All American, 1940) over the march's break strain, low:
"Rock... Someday when the team's up against it, the breaks are beating the boys, ask them to go in there
with all they've got." Then the grandioso slams in (piccolo on top, trombones standing up halfway): Notre
Dame in November, Sousa-sized America (the Marine Band, the flag, flyovers, Iwo Jima, Rushmore, fireworks),
the builders (Mach, the shipyard, the compute), Chicago, grit (Rocky, Rudy, strongmen); the Catholic
images only as flashes in the strobe run. The card lands on Sousa's stinger, and the Gipper gets the
last word: "Win just one for the Gipper."

Song: the U.S. Marine Band's recording (public domain, archive.org StarsAndStripesForever), 118.6 BPM.
media/w1109_bed.wav = song beats 327-416 (24 beats of the break strain, the 64-beat grandioso from song
beat 351, the stinger at 415) with a hall ring-out added to the stinger and the level brought up.
This edit starts 8 beats into the bed, so the drop (the grandioso) is edit beat 16 and the stinger 80.
Footage slots read media/w1109_<key>.*; alt=(key, in) borrows another clip until a slot lands;
text entries: (beat, text, size@720p, y[, style, end_beat]).
"""
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'w1109_'
BPM = 118.58531976744177
BEAT = 60 / BPM
SONG = 'media/' + P + 'bed.wav'
SONG_START = 8 * BEAT  # the bed's beat 8 is this edit's beat 0
DROP = 16
STINGER = DROP + 64


def _find(key):
    for ext, kind in (('.mp4', 'clip'), ('.mov', 'clip'), ('.jpg', 'photo'), ('.png', 'photo'), ('.webp', 'photo')):
        path = os.path.join(HERE, 'media', P + key + ext)
        if os.path.exists(path):
            return kind, path
    return None, None


def C(key, beats, alt=None, **kw):
    """Footage from media/w1109_<key>.*; else the first alternate that exists (alt = list of (key, in)), else a card."""
    kind, path = _find(key)
    for k, i in ([] if path else alt or []):
        kind, path = _find(k)
        if path:
            kw['in'] = i
            break
    if path:
        if kind == 'photo':
            for k in ('in', 'speed', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
                kw.pop(k, None)
            kw.setdefault('zoom', (1.0, 1.08))
        return dict({kind: path}, beats=beats, **kw)
    for k in ('zoom', 'center', 'speed', 'in', 'fit', 'dim', 'crop', 'voice', 'voice_gain', 'voice_tail', 'duck'):
        kw.pop(k, None)
    return dict(shot='slot', beats=beats, p=dict(label=key.upper().replace('_', ' '), desc=key, kind='clip'), **kw)


def M(name, beats, **kw):
    """A still from the inspiration board (memes keep their own captions)."""
    return dict(photo=os.path.join(HERE, 'inspiration', name), beats=beats, fit='contain', **kw)


def strobe(*items):
    out = []
    for it in items:
        it = dict(it, beats=0.5)
        it['fx'] = dict(it.get('fx', {}), punch=0.08, chroma=10)
        out.append(it)
    return out


def _dur(path):
    try:
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                    capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None


# ---- the speech. media/w1109_gipper_pre.m4a is the line with its long pauses tightened (7.50 s; "got" ends at 7.29 s);
# its last piece (from 5.15 s in the file) is the original's 8.80 s onward, so Reagan can be on screen in sync there.
PRE = 'media/' + P + 'gipper_pre.m4a'
PRE_AT = DROP - (7.29 + 0.5) / BEAT  # the grandioso lands half a second after "got"
SYNC_AT = PRE_AT + 5.15 / BEAT       # "ask them to go in there with all they've got" (original 8.80 s)
VOICEOVER = [dict(file=PRE, at=PRE_AT, src_in=0.0, dur=_dur(os.path.join(HERE, PRE)) or 7.5, gain=1.0, duck=0.18)]
BTN = 'media/' + P + 'gipper_btn.m4a'
BTN_AT = STINGER + 6
VOICEOVER.append(dict(file=BTN, at=BTN_AT, src_in=0.0, dur=_dur(os.path.join(HERE, BTN)) or 2.1, gain=1.0, duck=1.0))

PRE_ROLL = [
    C('nd_dome_night', 3.5, fx=dict(punch=0.0)),                                  # "Rock,"
    C('rockne_film', SYNC_AT - 3.5 - 3.6, fx=dict(punch=0.0)),                   # "someday when the team's up against it,"
    C('touchdown_jesus', 3.6, fx=dict(punch=0.0)),                                # "the breaks are beating the boys,"
    C('gipper', DROP - SYNC_AT, **{'in': 8.80}),                                  # Reagan: "ask them to go in there with all they've got."
]

# ---- the grandioso (edit beat 16): piccolo on top for 32 beats, then the trombones stand up
GRANDIOSO = [
    C('fireworks', 2, alt=[('marine_band', 0.0)], fx=dict(punch=0.12)),          # 16 the drop
    C('marine_band', 1),                                                          # 18 The President's Own
    C('flag_stadium', 2, alt=[('marine_band_2', 0.0)]),                          # 19
    C('nd_tunnel', 1.5),                                                          # 21 Play Like A Champion Today
    C('mach_stratos', 1.5, **{'in': 1.0}),                                        # 22.5 the Earth's curve
    C('b2_flyover', 2, alt=[('mach_atlas', 0.0)]),                               # 24
    C('eagle', 1, alt=[('mach_glide', 0.0)]),                                     # 26
    C('rushmore', 1, alt=[('shipyard', 1.0)]),                                    # 27
    C('nd_win', 2),                                                               # 28 the Orange Bowl kick
    C('datacenter', 1),                                                           # 30
    C('shipyard', 1),                                                             # 31
    C('mach_atlas', 2),                                                           # 32
    C('sousa', 1, alt=[('marine_band_2', 1.0)]),                                  # 34 the March King
    C('nascar', 1, alt=[('mach_viper', 0.0)]),                                    # 35
    M('05_ship_in_harbor.webp', 2, zoom=(1.0, 1.06)),                             # 36
    C('wrigley', 1, alt=[('datacenter_2', 0.0)]),                                 # 38
    C('chicago_night', 1, alt=[('datacenter_2', 1.5)]),                           # 39
    C('rocky', 2, alt=[('rudy', 0.0)]),                                           # 40
    C('mach_glide', 1, **{'in': 1.3}),                                            # 42 the strike blooms
    C('iwo_jima', 2, alt=[('marine_band', 2.0)]),                                 # 43
    C('bodybuilder', 1, alt=[('nd_win_2', 0.0)]),                                 # 45
    C('strongman', 1, alt=[('mach_viper', 1.5)]),                                 # 46
    C('rudy', 1),                                                                 # 47
    # 48: the trombones
    C('b2_flyover_2', 2, alt=[('flag_stadium_2', 0.0), ('b2_flyover', 1.5), ('mach_stratos', 2.0)], fx=dict(punch=0.1)),  # 48
    C('marine_band_2', 1),                                                        # 50
    C('mach_viper', 1),                                                           # 51
    C('nd_win_2', 2),                                                             # 52 the student section
    C('fireworks_2', 1, alt=[('fireworks', 2.0), ('nd_dome_night', 1.0)]),        # 54
    C('datacenter_2', 1),                                                         # 55
    C('rockne_film', 1, **{'in': 2.0}),                                           # 56
    M('02_hamster_u_a_diva_keep_going.webp', 2, zoom=(1.0, 1.06)),                # 57
    C('nd_tunnel', 1, **{'in': 1.2}),                                             # 59
    C('shipyard', 1, **{'in': 2.2}),                                              # 60
    C('rocky', 1, alt=[('rudy', 1.5)], **{'in': 2.0}),                            # 61
    C('mach_stratos', 2, **{'in': 2.0}),                                          # 62
    # 64: rapid fire, the Catholic images only as flashes
    *strobe(C('marine_band', 1, **{'in': 1.0}), C('touchdown_jesus', 1, **{'in': 1.0}), C('mach_glide', 1, **{'in': 1.5}),
            C('nd_dome_night', 1, **{'in': 2.0}), C('fireworks', 1, alt=[('marine_band_2', 2.0)], **{'in': 1.0}),
            C('rudy', 1, **{'in': 1.0}), C('mach_atlas', 1, **{'in': 2.0}), C('flag_stadium', 1, alt=[('nd_win', 2.5)], **{'in': 1.0}),
            C('nascar', 1, alt=[('datacenter', 2.0)], **{'in': 1.0}), C('iwo_jima', 1, alt=[('shipyard', 3.0)], **{'in': 1.5}),
            C('datacenter', 1, **{'in': 2.5}), C('wrigley', 1, alt=[('nd_win_2', 2.0)], **{'in': 1.5}),
            C('eagle', 1, alt=[('mach_viper', 2.5)], **{'in': 1.5}), C('bodybuilder', 1, alt=[('marine_band', 3.0)], **{'in': 1.0}),
            C('nd_win', 1, **{'in': 1.0}), C('mach_viper', 1, **{'in': 3.0})),
    # 72: the last eight beats to the stinger
    C('rushmore', 2, alt=[('nd_dome_night', 2.5)], **{'in': 1.0}),               # 72
    C('flag_stadium_2', 2, alt=[('flag_stadium', 2.0), ('marine_band_2', 2.5)]),  # 74
    C('fireworks', 2, alt=[('marine_band', 2.5)], **{'in': 2.0}),                 # 76
    C('nd_win', 2, **{'in': 0.3}),                                                # 78
]
# ---- the stinger (edit beat 80): the card while the hall rings out; then the Gipper's last word
END = [
    C('nd_tunnel', 6, dim=0.45, speed=0.5, fx=dict(punch=0.12), text=[(0, 'PLAY LIKE A CHAMPION.', 96, 0.5)]),  # 80
    C('gipper', 4.4, **{'in': 11.52}),                                            # 86 "Win just one for the Gipper."
]
SEQ = PRE_ROLL + GRANDIOSO + END

if __name__ == '__main__':
    b = 0.0
    for name, part in (('PRE', PRE_ROLL), ('GRANDIOSO', GRANDIOSO), ('END', END)):
        print('%6.2f  %s' % (b, name))
        b += sum(s['beats'] for s in part)
    print('total %.2f beats = %.1f s; voice: pre at %.2f, sync at %.2f, button at %.2f; cuts %d; missing: %s' % (
        b, b * BEAT, PRE_AT, SYNC_AT, BTN_AT, len(SEQ), sorted({s['p']['desc'] for s in SEQ if s.get('shot') == 'slot'})))
