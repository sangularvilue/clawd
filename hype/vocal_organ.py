"""Swap a song's lead vocal for a pipe organ when there's no sheet music.

    python3 vocal_organ.py <song> <out.wav> --config organ_songs/<song>.json [--stems] [--dump]

The vocal line is transcribed straight onto the song's beat grid: a studio track holds
its click tempo, so every note starts on a 16th. A Viterbi pass over 16th slots picks, for
each slot, a pitch from the song's key (or a rest), weighing the singer's pYIN pitch, the
vocal stem's chroma where pitch tracking drops out, its loudness, and its syllable onsets.
New notes cost something, so wobble, scoops and breaths don't become extra notes; onsets and
beats make them cheap, so real syllables aren't dropped. The organ then plays that line
with score_organ.py's registration plan, rooms, limiter and closing chord, plus a pedal
that follows the bass stem beat by beat and, in the big sections, triads under the tune.

Bars in the config count from the first downbeat of the recording's beat grid (bar 1).
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import organ  # noqa: E402
import organ_vocal  # noqa: E402
import score_organ as so  # noqa: E402

KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def pyin(path, cache, fmin=70, fmax=1000, sr=16000, hop=320):
    if os.path.exists(cache):
        return np.load(cache)
    import librosa
    y, _ = librosa.load(path, sr=sr)
    f0, vflag, vprob = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr, frame_length=2048, hop_length=hop)
    z = np.stack([f0, vflag.astype(float), vprob])
    np.save(cache, z)
    return z


def key_of(midi):
    """Krumhansl key from a list of sung MIDI values: (tonic pc, 'major'|'minor', scale pcs)."""
    h = np.bincount(np.round(midi).astype(int) % 12, minlength=12).astype(float)
    best = max(((np.corrcoef(h, np.roll(prof, t))[0, 1], t, mode)
                for prof, mode in ((KK_MAJOR, 'major'), (KK_MINOR, 'minor')) for t in range(12)))
    _, t, mode = best
    steps = [0, 2, 4, 5, 7, 9, 11] if mode == 'major' else [0, 2, 3, 5, 7, 8, 10]
    return t, mode, sorted((t + s) % 12 for s in steps)


def fold_octaves(m, half):
    """Pitch trackers (and gang vocals) jump an octave; fold any frame that sits ~an octave
    off the phrase's running median back onto it."""
    out = m.copy()
    idx = np.where(~np.isnan(m))[0]
    if not len(idx):
        return out
    v = m[idx]
    for _ in range(2):
        med = np.array([np.median(v[max(0, i - half):i + half + 1]) for i in range(len(v))])
        d = v - med
        v = np.where(d > 8.5, v - 12, np.where(d < -8.5, v + 12, v))
    out[idx] = v
    return out


def transcribe(f0z, feats, phase, slot, scale, sing, hop=0.02):
    """16th-slot Viterbi over {rest} + MIDI pitches. sing: bool per slot, where the organ may play.
    Returns notes [start, end, midi] in seconds."""
    f0, vflag, _ = f0z
    m = np.where(vflag > 0, 69 + 12 * np.log2(np.nan_to_num(f0, nan=440) / 440), np.nan)
    m = fold_octaves(m, int(0.6 / hop))
    CH, _, ON, R = feats
    CHn = CH / (CH.max(1, keepdims=True) + 1e-9)
    ns = min(len(R), len(sing))
    sung = m[~np.isnan(m)]
    lo, hi = int(np.floor(np.percentile(sung, 1))), int(np.ceil(np.percentile(sung, 99)))
    P = np.arange(lo, hi + 1)
    inscale = np.isin(P % 12, scale)
    S = len(P) + 1  # state 0 = rest
    E = np.zeros((ns, S))
    for j in range(ns):
        a = int((phase + j * slot) / hop)
        b = int((phase + (j + 1) * slot) / hop)
        fr = m[a:b]
        v = fr[~np.isnan(fr)]
        nu = len(fr) - len(v)
        if len(v):
            d = v[:, None] - P[None, :]
            E[j, 1:] = np.sum(2.0 * np.exp(-(d / 0.5) ** 2) - 0.6, axis=0)
        loud = R[j] > 0.3
        E[j, 1:] += -(0.05 if loud else 0.15) * nu - 1.6 * ~inscale
        if loud:  # pitch tracking dropped out while someone is singing: lean on the stem's chroma
            E[j, 1:] += (1.0 if not len(v) else 0.3) * (CHn[j, P % 12] - 0.5)
        E[j, 0] = -0.5 * len(v) + (0.05 if loud else 0.25) * nu + (0.6 if R[j] < 0.12 else -0.5 if R[j] > 0.35 else 0.0)
        if not sing[j]:
            E[j, 1:] = -1e6
    dist = np.abs(P[:, None] - P[None, :])
    best = E[0].copy()
    back = np.zeros((ns, S), int)
    restrike = np.zeros((ns, S), bool)
    for j in range(1, ns):
        g = 0.3 if j % 4 == 0 else 0.15 if j % 2 == 0 else 0.0
        on = ON[j] if j < len(ON) else 0.0
        T = np.empty((S, S))
        T[0, 0] = 0.0
        T[0, 1:] = -0.4 + 1.0 * on + g
        T[1:, 0] = -0.4
        T[1:, 1:] = -0.8 - 0.06 * dist + 1.2 * on + g
        rs = -1.5 + 2.0 * on + g
        diag = max(0.0, rs)
        T[np.arange(1, S), np.arange(1, S)] = diag
        cand = best[:, None] + T
        back[j] = np.argmax(cand, 0)
        restrike[j] = (back[j] == np.arange(S)) & (rs > 0) & (np.arange(S) > 0)
        best = cand[back[j], np.arange(S)] + E[j]
    st = [int(np.argmax(best))]
    for j in range(ns - 1, 0, -1):
        st.append(back[j][st[-1]])
    st = st[::-1]
    notes, cur = [], None
    for j, s in enumerate(st):
        new = s > 0 and (cur is None or cur[2] != P[s - 1] or restrike[j][s])
        if cur is not None and (s == 0 or new):
            notes.append(cur)
            cur = None
        if s > 0 and cur is None:
            cur = [phase + j * slot, phase + (j + 1) * slot, int(P[s - 1])]
        elif s > 0:
            cur[1] = phase + (j + 1) * slot
    if cur is not None:
        notes.append(cur)
    return clean_blips(notes, slot)


def clean_blips(notes, slot):
    """A one-16th note a step or less from a neighbour it touches is a scoop or a fall-off,
    not a note: fold it into that neighbour."""
    out = [list(n) for n in notes]
    changed = True
    while changed:
        changed = False
        for i, n in enumerate(out):
            if n[1] - n[0] > slot * 1.5:
                continue
            nxt = out[i + 1] if i + 1 < len(out) else None
            prv = out[i - 1] if i > 0 else None
            if nxt and abs(nxt[0] - n[1]) < 1e-6 and abs(nxt[2] - n[2]) <= 2:
                nxt[0] = n[0]
            elif prv and abs(prv[1] - n[0]) < 1e-6 and abs(prv[2] - n[2]) <= 2:
                prv[1] = n[1]
            else:
                continue
            del out[i]
            changed = True
            break
    return out


def bass_line(bass_wav, cache, phase, beat, nbeats):
    """The bass stem's most common pitch on each beat (MIDI or None)."""
    z = pyin(bass_wav, cache, fmin=30, fmax=300, sr=22050, hop=512)
    f0, vflag, _ = z
    hop = 512 / 22050
    m = np.where(vflag > 0, 69 + 12 * np.log2(np.nan_to_num(f0, nan=440) / 440), np.nan)
    import librosa
    y, sr = librosa.load(bass_wav, sr=22050)
    ch = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512, fmin=librosa.note_to_hz('C1'), n_octaves=4)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    loud = np.percentile(rms, 90)
    out = []
    for k in range(nbeats):
        a, b = int((phase + k * beat) / hop), int((phase + (k + 1) * beat) / hop)
        v = m[a:b]
        v = np.round(v[~np.isnan(v)]).astype(int)
        if len(v) >= 3:
            vals, c = np.unique(v, return_counts=True)
            out.append(int(vals[np.argmax(c)]))
            continue
        c = ch[:, a:b].mean(1) if b > a else np.zeros(12)
        if rms[a:b].mean() > 0.2 * loud and c.max() > 1.6 * np.sort(c)[-2]:  # distorted bass: a clear chroma peak
            out.append(int(np.argmax(c)) + 36)
        else:
            out.append(None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('out')
    ap.add_argument('--config', required=True)
    ap.add_argument('--stems', action='store_true')
    ap.add_argument('--dump', action='store_true', help='print the transcribed line bar by bar')
    ap.add_argument('--final-release', type=float)
    ap.add_argument('--sf2', default=organ.SF2)
    a = ap.parse_args()
    cfg = json.load(open(a.config))

    h = hashlib.sha1(open(a.song, 'rb').read()).hexdigest()[:12]
    cache = os.path.join(organ.CACHE, h)
    os.makedirs(cache, exist_ok=True)
    stems = organ.separate(a.song, cache)
    bpm = float(cfg['bpm'])
    beat = 60 / bpm
    slot = beat / 4
    phase = so.beat_grid(stems['drums'], bpm)
    down = phase + cfg.get('downbeat_offset_beats', 0) * beat  # bar 1, beat 1
    bar_time = lambda b, bt=0.0: down + ((b - 1) * 4 + bt) * beat
    f0z = pyin(stems['vocals'], os.path.join(cache, 'pyin_f0.npy'))
    feats = so.slot_features(stems['vocals'], os.path.join(cache, 'pyin_f0.npy'), down, slot,
                             os.path.join(cache, 'slotfeat_%.3f.npz' % down))
    ns = len(feats[3])
    bar_of_slot = lambda j: j // 16 + 1
    mel_bars = so.ranges(cfg['melody_bars'])
    sing = np.array([bar_of_slot(j) in mel_bars for j in range(ns)])
    sung = f0z[0][f0z[1] > 0]
    tonic, mode, scale = key_of(69 + 12 * np.log2(sung / 440))
    if 'key' in cfg:
        tonic, mode = cfg['key']
        tonic = NAMES.index(tonic)
        steps = [0, 2, 4, 5, 7, 9, 11] if mode == 'major' else [0, 2, 3, 5, 7, 8, 10]
        scale = sorted((tonic + s) % 12 for s in steps)
    print('tempo %.2f BPM, grid phase %.3f s, bar 1 at %.3f s, key %s %s' % (bpm, phase, down, NAMES[tonic], mode))
    line = transcribe(f0z, feats, down, slot, scale, sing)
    shift = 12 * round((cfg.get('center', 70) - np.median([n[2] for n in line])) / 12)
    print('vocal line: %d notes, organ octave shift %+d' % (len(line), shift))
    if a.dump:
        for b in sorted(mel_bars):
            ns_ = [n for n in line if bar_time(b) - 1e-6 <= n[0] < bar_time(b + 1) - 1e-6]
            print('  bar %3d %6.2f: %s' % (b, bar_time(b), ' '.join(
                '%s%d@%d(%d)' % (NAMES[n[2] % 12], n[2] // 12 - 1, round((n[0] - bar_time(b)) / slot),
                                 round((n[1] - n[0]) / slot)) for n in ns_)))

    stacks = {'simple': organ_vocal.SIMPLE, 'medium': so.MEDIUM, 'full': organ_vocal.FULL}
    stacks.update({k: [tuple(r) for r in v] for k, v in cfg.get('stacks', {}).items()})
    plan = [(so.ranges(str(b)), name) for b, name in cfg.get('registration', [])]
    reg_of = lambda bar: next((name for bs, name in plan if bar in bs), 'simple')
    bar_at = lambda t: int(np.floor((t - down) / (4 * beat) + 1e-6)) + 1
    lead = cfg.get('lead', 0.02)

    # pedal: the bass stem's note per beat, held while it stays, re-struck each downbeat
    nbeats = int((ns * slot) / beat)
    bl = bass_line(stems['bass'], os.path.join(cache, 'bass_f0.npy'), down, beat, nbeats)
    ped_bars = so.ranges(cfg.get('pedal_bars', ''))
    chord_bars = so.ranges(cfg.get('chords', ''))
    manual = sorted((((int(b) - 1) * 4 + bt, so.note_midi(nm)) for b, evs in cfg.get('pedal', {}).items() for bt, nm in evs))
    ped, prev = [], None
    for i, (k, m) in enumerate(manual):  # a hand-read pedal line: also the chord roots there
        k1 = manual[i + 1][0] if i + 1 < len(manual) and manual[i + 1][0] - k <= 8 else k + 4
        ped.append([bar_time(1, k) - lead, bar_time(1, k1) - lead - 0.01, m, 'pedal'])
        for kk in range(int(k), int(np.ceil(k1))):
            if kk < len(bl):
                bl[kk] = m
    for k, mb in enumerate(bl):
        b = k // 4 + 1
        if manual or b not in ped_bars or mb is None:
            prev = None
            continue
        p = mb % 12 + 36  # C2..B2, voiced to stay near the previous pedal note
        if prev is not None and abs(p + 12 - prev[2]) < abs(p - prev[2]) and p + 12 <= 50:
            p += 12
        t = bar_time(1, k) - lead
        if prev is not None and prev[2] == p and k % 4 and abs(prev[1] - t) < 1e-6:
            prev[1] = t + beat
            continue
        prev = [t, t + beat, p, 'pedal']
        ped.append(prev)
    for i in range(len(ped) - 1):
        ped[i][1] = min(ped[i][1], ped[i + 1][0]) - 0.01

    import librosa
    yo, sr = librosa.load(stems['other'], sr=22050)
    cho = librosa.feature.chroma_cqt(y=yo, sr=sr, hop_length=512)
    # each chord root gets one quality for the whole song: the third the band plays most
    # over every beat on that root in the chord and pad bars (single beats are ambiguous)
    harm_bars = chord_bars | so.ranges(cfg.get('pad_bars', ''))
    votes = np.zeros((12, 2))
    for k, mb in enumerate(bl):
        if mb is None or (k // 4 + 1) not in harm_bars:
            continue
        r = mb % 12
        a_, b_ = int(bar_time(1, k) * sr / 512), int(bar_time(1, k + 1) * sr / 512)
        c = cho[:, a_:b_].mean(1)
        votes[r] += [c[(r + 3) % 12], c[(r + 4) % 12]]
    quality = {r: (3 if votes[r, 0] > votes[r, 1] else 4) for r in range(12)}
    quality.update({NAMES.index(k): {'minor': 3, 'major': 4}[v] for k, v in cfg.get('chord_quality', {}).items()})

    def triad(k):  # pitch classes of the chord on beat k: bass root + its third + fifth
        r = bl[k] % 12 if k < len(bl) and bl[k] is not None else None
        if r is None:
            return None
        return [r, (r + quality[r]) % 12, (r + 7) % 12]

    notes = []
    for s, e, p in line:
        b = bar_at(s + 0.01)
        mp = p + shift
        notes.append((s - lead, e - lead, mp, reg_of(b)))
        if b in chord_bars:
            k = int(round((s - down) / beat - 0.5 + 1e-6))
            tri = triad(max(0, k))
            if tri:
                notes += [(s - lead, e - lead, c, 'chord') for c in range(mp - 12, mp) if c % 12 in tri and c % 12 != mp % 12]
    notes += [tuple(x) for x in ped]

    # pad: where the vocal is just ad-libs, the organ sustains the band's chords instead
    pad_bars = so.ranges(cfg.get('pad_bars', ''))
    pad_reg = cfg.get('pad_stack', 'plenum')
    cur = None
    for k in range(nbeats + 1):
        tri = triad(k) if k < nbeats and (k // 4 + 1) in pad_bars else None
        if cur is not None and (tri != cur[1] or k % 8 == 0):
            t0, t1 = bar_time(1, cur[0]) - lead, bar_time(1, k) - lead - 0.01
            lo_ = cfg.get('pad_low', 55)
            tones = [c for c in range(lo_, lo_ + 12) if c % 12 in cur[1]]
            tones.append(min(c for c in range(lo_ + 12, lo_ + 24) if c % 12 == cur[1][0]))
            notes += [(t0, t1, c, pad_reg) for c in tones]
            cur = None
        if tri is not None and cur is None:
            cur = (k, tri)

    fc = cfg.get('final_chord')
    final_notes, final_t0, end_t = [], None, None
    if fc:
        if a.final_release:
            fc = dict(fc, release=a.final_release)
        final_t0 = bar_time(fc['bar'], fc.get('beat', 0)) - lead
        end_t = fc['release']
        notes = [n for n in notes if n[0] < final_t0 - 0.05]
        notes = [(s, min(e, final_t0 - 0.01), p, r) for s, e, p, r in notes]
        r = reg_of(fc['bar'])
        final_notes = [(final_t0, end_t, so.note_midi(nm), r) for nm in fc['notes']]
        if fc.get('pedal'):
            final_notes.append((final_t0, end_t, so.note_midi(fc['pedal']), 'pedal'))
    notes.sort()

    swell = organ_vocal.expression(stems['vocals'], [(s, e, p, 1) for s, e, p, r in notes if r not in ('chord', 'pedal')])
    floors = [(bar_time(min(so.ranges(str(b)))), bar_time(max(so.ranges(str(b))) + 1), v) for b, v in cfg.get('swell_floor', [])]
    if fc:
        floors.append((final_t0, end_t + 1, 127))
    swell = [(t, max([v] + [fv for t0, t1, fv in floors if t0 <= t < t1])) for t, v in swell]

    parts = []
    for part in cfg.get('parts', [{'bars': '1-999', 'reverb': [1.8, 0.25, 250.0], 'boost_db': 0}]):
        bs = so.ranges(str(part['bars']))
        has_final = bool(fc and fc['bar'] in bs)
        parts.append(dict(part, label='bars ' + str(part['bars']), t0=bar_time(min(bs)) - 0.3,
                          t1=None if has_final else bar_time(max(bs) + 1) - 0.3, final=has_final))
    so.mix_parts(a.out, stems, notes, final_notes, final_t0, fc.get('gain_db', 0) if fc else 0, parts, swell,
                 stacks, a.sf2, cfg.get('organ_db', 1.0), cfg.get('master_db', 0), a.stems, cfg.get('tail', 0.0))
    json.dump([dict(start=s, end=e, midi=int(p), reg=r) for s, e, p, r in notes + final_notes], open(a.out + '.notes.json', 'w'))
    print('notes %d (vocal line %d, pedal %d)  -> %s' % (len(notes) + len(final_notes), len(line), len(ped), a.out))


if __name__ == '__main__':
    main()
