"""Play a song's vocal line on pipe organ from a score, aligned to the real singer, over the backing.

    python3 score_organ.py <song> <score_notes.json> <out.wav> --bpm 96 \
        --vocal-bars 5-24,29-48,59-78 --five-four 11,12,35,36,61,62 \
        --medium 63-70 --full 71-78

score_notes.json comes from score_read.py. The right-hand top line of the vocal bars
is the melody. A studio track holds its click tempo exactly, so the score lands on the
recording's drum-derived beat grid by a whole number of beats; each note then snaps
to the 16th where the singer actually starts it (vocal-stem onsets and pitch), and bars
where the arrangement plainly harmonises instead of doubling the singer are moved
onto the sung notes. Every written note is played once: nothing dropped, nothing extra.
"""
import argparse
import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import organ  # noqa: E402
import organ_vocal  # noqa: E402

SR = organ.SR
MEDIUM = [(0, 19, -12, 0.7), (0, 19, 0, 1.0), (0, 19, 12, 0.6), (8, 19, 12, 0.4)]


def ranges(spec):
    out = set()
    for part in filter(None, spec.split(',')):
        a, _, b = part.partition('-')
        out.update(range(int(a), int(b or a) + 1))
    return out


def score_events(bars, vocal, five, bpm):
    """Melody (top RH note per onset) and all RH notes, in score seconds."""
    beat = 60.0 / bpm
    t_bar, melody, allrh = 0.0, [], []
    for b in bars:
        nb = 5 if b['bar'] in five else 4
        if b['bar'] in vocal:
            rh = [n for n in b['notes'] if n['staff'] == 'rh']
            filled_x = [n['x'] for n in rh if n['head'] == 'filled']
            rh = sorted((n for n in rh if n['head'] == 'filled' or
                         not any(abs(n['x'] - fx) < 0.05 for fx in filled_x)), key=lambda n: n['x'])
            clusters = []
            for n in rh:
                if clusters and n['x'] - clusters[-1][-1]['x'] < 0.045:
                    clusters[-1].append(n)
                else:
                    clusters.append([n])
            onsets = []
            for c in clusters:
                filled = [n for n in c if n['head'] == 'filled']
                prev_top = onsets[-1][1] if onsets else (melody[-1][2] if melody else None)
                if not filled and prev_top is not None and any((n['midi'] - prev_top) % 12 == 0 for n in c):
                    continue  # a half note tied from the previous note: hold it, don't re-strike
                c = filled or c  # a hollow "head" beside filled ones is an enclosed gap, not a note
                x = np.mean([n['x'] for n in c])
                onsets.append((x, max(n['midi'] for n in c), [n['midi'] for n in c]))
            # position within the bar -> beats (engraving leaves ~6% left and ~3% right margins)
            for i, (x, top, all_) in enumerate(onsets):
                s = t_bar + max(0.0, (x - 0.06) / 0.91) * nb * beat
                nx = onsets[i + 1][0] if i + 1 < len(onsets) else 0.97
                e = t_bar + max(0.0, (nx - 0.06) / 0.91) * nb * beat
                e = min(e, s + 1.5 * beat)
                melody.append([s, e, top, b['bar']])
                allrh.extend([s, e, m] for m in all_)
        t_bar += nb * beat
    return melody, allrh, t_bar


def beat_grid(drums_wav, bpm):
    """Phase of a fixed-tempo beat grid (studio recordings to a click hold tempo exactly)."""
    import librosa
    y, sr = librosa.load(drums_wav, sr=22050)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=220)
    fps = sr / 220
    per = 60.0 / bpm
    def strength(ph):
        idx = np.round((ph + np.arange(0, len(env) / fps - ph, per)) * fps).astype(int)
        return env[idx[idx < len(env)]].mean()
    best = max((strength(ph), ph) for ph in np.arange(0, per, 0.005))
    return best[1]


def slot_features(vocals_wav, pyin_cache, phase, slot, path):
    """Per-16th-note features of the vocal stem: chroma, pYIN pitch-class share, onset
    strength at the slot start, loudness."""
    if os.path.exists(path):
        z = np.load(path)
        if 'phase' in z and abs(float(z['phase']) - phase) < 1e-6 and abs(float(z['slot']) - slot) < 1e-9:
            return z['CH'], z['PC'], z['ON'], z['R']
    import librosa
    y, sr = librosa.load(vocals_wav, sr=22050)
    hop = 220
    fps = sr / hop
    ch = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    on = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    f0, vflag, _ = np.load(pyin_cache)
    pm = np.where(vflag > 0, 69 + 12 * np.log2(np.nan_to_num(f0, nan=440) / 440), np.nan)
    ns = int((len(y) / sr - phase) / slot)
    CH, PC, ON, R = np.zeros((ns, 12)), np.zeros((ns, 12)), np.zeros(ns), np.zeros(ns)
    for j in range(ns):
        t0 = phase + j * slot
        a, b = int(t0 * fps), int((t0 + slot) * fps)
        CH[j] = ch[:, a:b].mean(1)
        R[j] = rms[a:b].mean()
        ON[j] = on[max(0, a - 3):a + 4].max()
        seg = pm[int(t0 / 0.02):int((t0 + slot) / 0.02)]
        seg = seg[~np.isnan(seg)]
        for x in seg:
            PC[j, int(round(x)) % 12] += 1
        PC[j] /= max(1.0, slot / 0.02)
    ON /= np.percentile(ON, 99)
    R /= np.percentile(R, 95)
    np.savez(path, CH=CH, PC=PC, ON=ON, R=R, phase=phase, slot=slot)
    return CH, PC, ON, R


def align_grid(melody, sections, feats, phase, beat, window=4, sustain=True):
    """Score and recording share an exact tempo, so the score maps onto the recording's
    beat grid by a whole number of beats (searched globally, per section only when a
    section clearly prefers another). Within a section each note then snaps to a 16th
    slot near its engraved position by dynamic programming over: the singer's onset
    strength, the sung pitch (pYIN, chroma) holding the note's pitch until the next
    note, a mild preference for beats and 8ths, and distance from the engraved spot."""
    CH, PC, ON, R = feats
    CHn = CH / (CH.max(1, keepdims=True) + 1e-9)
    slot = beat / 4
    ns = len(R)

    def fit(j0, j1, pc):  # how well slots j0..j1-1 carry pitch class pc
        if j1 <= j0 or j0 < 0 or j1 > ns:
            return -3.0
        p = PC[j0:j1]
        return float(np.sum(2 * p[:, pc] - 0.6 * (p.sum(1) - p[:, pc]) + 0.8 * CHn[j0:j1, pc] - 0.3
                            + 0.5 * np.minimum(R[j0:j1], 1)))

    def match(notes, k):
        return sum(fit(int(round(s / slot)) + 4 * k, max(int(round(s / slot)) + 4 * k + 1,
                                                          int(round(e / slot)) + 4 * k), m % 12)
                   for s, e, m, _ in notes)

    secs = [[x for x in melody if lo <= x[3] <= hi] for lo, hi in sections]
    secs = [s for s in secs if s]
    ks = range(-8, 41)
    kg = max(ks, key=lambda k: sum(match(s, k) for s in secs))
    out, report = [], []
    for sec in secs:
        scores = {k: match(sec, k) for k in ks}
        kb = max(scores, key=scores.get)
        k = kb if scores[kb] > 1.25 * max(scores[kg], 1e-9) else kg
        report.append((sec[0][3], sec[-1][3], k, kb))
        p = [s / slot + 4 * k for s, _, _, _ in sec]
        pe = [e / slot + 4 * k for _, e, _, _ in sec]
        cand = [list(range(int(np.floor(x)) - window, int(np.ceil(x)) + window + 1)) for x in p]
        grid = lambda j: 0.35 if j % 4 == 0 else 0.15 if j % 2 == 0 else 0.0
        unary = [[1.2 * (ON[j] if 0 <= j < ns else 0) + grid(j) - 0.25 * abs(j - x) for j in c]
                 for c, x in zip(cand, p)]
        n = len(sec)
        best = [np.array(unary[0])]
        back = []
        for i in range(1, n):
            cur, bk = [], []
            for jb, b in enumerate(cand[i]):
                opts = [(best[i - 1][ja] + 0.5 * fit(a, b, sec[i - 1][2] % 12), ja)
                        for ja, a in enumerate(cand[i - 1]) if a < b]
                if not opts:
                    cur.append(-1e9)
                    bk.append(0)
                    continue
                v, ja = max(opts)
                cur.append(v + unary[i][jb])
                bk.append(ja)
            best.append(np.array(cur))
            back.append(bk)
        last = [best[-1][j] + 0.5 * fit(c, max(c + 1, int(round(pe[-1]))), sec[-1][2] % 12)
                for j, c in enumerate(cand[-1])]
        ji = [int(np.argmax(last))]
        for i in range(n - 1, 0, -1):
            ji.append(back[i - 1][ji[-1]])
        ji = ji[::-1]
        js = [cand[i][j] for i, j in enumerate(ji)]
        for i, (j, x) in enumerate(zip(js, sec)):
            shift = j - p[i]
            end = pe[i] + shift
            if i + 1 < n:
                end = min(max(end, j + 1), js[i + 1])
            out.append([phase + j * slot, phase + max(j + 1, end) * slot, x[2], x[3]])
    out.sort(key=lambda x: x[0])
    for i, x in enumerate(out if sustain else []):  # hold through the singer's sustain (ties across barlines aren't read)
        nxt = out[i + 1][0] if i + 1 < len(out) else x[1] + 4 * beat
        j = int(round((x[1] - phase) / slot))
        while j < ns and phase + j * slot < min(nxt, x[1] + 2 * beat) and R[j] > 0.3:
            j += 1
        x[1] = max(x[1], min(nxt, phase + j * slot))
    for i in range(len(out) - 1):  # legato, with a breath before repeated notes
        nxt = out[i + 1][0]
        if out[i][1] > nxt - 0.005:
            out[i][1] = nxt - (0.04 if out[i + 1][2] == out[i][2] else 0.005)
    return out, kg, report


def follow_singer(notes, sections, pyin_cache, min_voiced=30):
    """Where a bar of the arrangement clearly isn't what the singer sings (piano
    arrangements sometimes harmonise the tune instead of doubling it), move that bar's
    notes along the section's scale by the whole-bar step shift that best matches the
    singer's pitch track. Note count and rhythm stay the score's."""
    f0, vflag, _ = np.load(pyin_cache)
    pc = np.where(vflag > 0, np.round(69 + 12 * np.log2(np.nan_to_num(f0, nan=440) / 440)) % 12, -1)

    def score(ns):
        tot = vox = 0
        for s, e, m, _ in ns:
            seg = pc[int(s / 0.02):int(e / 0.02)]
            v = seg >= 0
            tot += np.sum(seg[v] == m % 12) - 0.3 * np.sum(seg[v] != m % 12)
            vox += v.sum()
        return tot, vox

    changed = []
    for lo, hi in sections:
        sec = [x for x in notes if lo <= x[3] <= hi]
        if not sec:
            continue
        hist = np.bincount([x[2] % 12 for x in sec], minlength=12)
        scale = sorted(int(v) for v in np.argsort(hist)[::-1][:7])

        for b in range(lo, hi + 1):
            ns = [x for x in sec if x[3] == b]
            base, vox = score(ns)
            if not ns or vox < min_voiced:
                continue
            r = {k: score([[s, e, scale_step(m, k, scale), bb] for s, e, m, bb in ns])[0]
                 for k in (-3, -2, -1, 1, 2, 3)}
            k = max(r, key=r.get)
            if r[k] - base > max(15, 0.5 * abs(base)):
                changed.append((b, k, scale))
    return changed


def scale_step(m, k, scale):
    """Move MIDI note m by k steps along a 7-note scale (pitch classes)."""
    o, p = divmod(m, 12)
    if p not in scale:
        return m
    i = scale.index(p) + k
    return 12 * (o + i // 7) + scale[i % 7]


def render(notes, stacks, sf2, swell):
    import tinysoundfont
    syn = tinysoundfont.Synth(samplerate=SR, gain=-8)
    sfid = syn.sfload(sf2)
    chans, ch = {}, 0
    for name, stack in stacks.items():
        for i, (bank, preset, _, _) in enumerate(stack):
            if ch == 9:
                ch += 1
            syn.program_select(ch, sfid, bank, preset)
            syn.control_change(ch, 7, 112)
            chans[(name, i)] = ch
            ch += 1
    ev = []
    for s, e, p, reg in notes:
        for i, (_, _, off, vs) in enumerate(stacks[reg]):
            k = p + off
            if 21 <= k <= 108:
                ev.append((s, 2, 'on', chans[(reg, i)], k, int(100 * vs)))
                ev.append((e, 0, 'off', chans[(reg, i)], k, 0))
    last = -1
    for t, v in swell:
        if abs(v - last) >= 2:
            for c in chans.values():
                ev.append((t, 1, 'cc', c, 11, v))
            last = v
    ev.sort(key=lambda x: (x[0], x[1]))
    chunks, t = [], 0.0
    for et, _, kind, c, k, v in ev:
        n = int(round((et - t) * SR))
        if n > 0:
            chunks.append(np.frombuffer(syn.generate(n), np.float32).copy())
            t += n / SR
        if kind == 'on':
            syn.noteon(c, k, v)
        elif kind == 'off':
            syn.noteoff(c, k)
        else:
            syn.control_change(c, k, v)
    syn.notes_off()
    chunks.append(np.frombuffer(syn.generate(int(2 * SR)), np.float32).copy())
    return np.concatenate(chunks).reshape(-1, 2).T


def main():
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('score')
    ap.add_argument('out')
    ap.add_argument('--bpm', type=float, required=True)
    ap.add_argument('--vocal-bars', required=True)
    ap.add_argument('--five-four', default='')
    ap.add_argument('--medium', default='', help='bars that get a fuller registration')
    ap.add_argument('--full', default='', help='bars that get all the stops')
    ap.add_argument('--sections', default='', help='alignment sections (default: the vocal-bar ranges)')
    ap.add_argument('--transpose', type=int, default=0)
    ap.add_argument('--no-follow-singer', dest='follow_singer', action='store_false',
                    help='play the arrangement as written even where the singer sings other notes')
    ap.add_argument('--lead', type=float, default=0.02, help='start organ notes this early (pipe attack)')
    ap.add_argument('--organ-db', type=float, default=1.0)
    ap.add_argument('--sf2', default=organ.SF2)
    a = ap.parse_args()

    h = hashlib.sha1(open(a.song, 'rb').read()).hexdigest()[:12]
    cache = os.path.join(organ.CACHE, h)
    os.makedirs(cache, exist_ok=True)
    stems = organ.separate(a.song, cache)
    bars = json.load(open(a.score))
    melody, allrh, score_len = score_events(bars, ranges(a.vocal_bars), ranges(a.five_four), a.bpm)
    secs = []
    for part in filter(None, a.vocal_bars.split(',')):
        lo, _, hi = part.partition('-')
        secs.append((int(lo), int(hi or lo)))
    if a.sections:
        secs = []
        for part in filter(None, a.sections.split(',')):
            lo, _, hi = part.partition('-')
            secs.append((int(lo), int(hi or lo)))
    beat = 60 / a.bpm
    phase = beat_grid(stems['drums'], a.bpm)
    feats = slot_features(stems['vocals'], os.path.join(cache, 'pyin_f0.npy'), phase, beat / 4,
                          os.path.join(cache, 'slotfeat.npz'))
    aligned, kg, report = align_grid(melody, secs, feats, phase, beat)
    changed = []
    if a.follow_singer:  # fix bars the arrangement harmonises, then re-snap them with the right pitches
        rough, _, _ = align_grid(melody, secs, feats, phase, beat, sustain=False)
        changed = follow_singer(rough, secs, os.path.join(cache, 'pyin_f0.npy'))
        for b, k, scale in changed:
            for x in melody:
                if x[3] == b:
                    x[2] = scale_step(x[2], k, scale)
        if changed:
            aligned, kg, report = align_grid(melody, secs, feats, phase, beat)
    aligned = [[s - a.lead, e - a.lead, p, bar] for s, e, p, bar in aligned]
    print('beat grid phase %.3f s, score -> recording offset %d beats' % (phase, kg))
    for lo, hi, k, kb in report:
        print('  bars %d-%d: offset %d beats (section alone prefers %d)' % (lo, hi, k, kb))
    for b, k, _ in changed:
        print('  bar %d: arrangement differs from the singer, melody moved %+d scale steps' % (b, k))
    med, full = ranges(a.medium), ranges(a.full)
    notes = [(s, e, p + a.transpose, 'full' if bar in full else 'medium' if bar in med else 'simple')
             for s, e, p, bar in aligned]
    stacks = {'simple': organ_vocal.SIMPLE, 'medium': MEDIUM, 'full': organ_vocal.FULL}
    swell = organ_vocal.expression(stems['vocals'], [(s, e, p, 1) for s, e, p, _ in notes])
    x = organ.cathedral(render(notes, stacks, a.sf2, swell), rt60=1.8, wet=0.25, hp=250.0)

    backing = sum(organ.load_stereo(stems[k]) for k in ('drums', 'bass', 'other'))
    vocal = organ.load_stereo(stems['vocals'])
    n = min(backing.shape[1], x.shape[1], vocal.shape[1])
    voiced = np.zeros(n, bool)
    for s, e, _, _ in notes:
        voiced[int(s * SR):min(n, int(e * SR))] = True
    rms = lambda z: np.sqrt(np.mean(z[:, :n][:, voiced] ** 2)) + 1e-9
    g = rms(vocal) / rms(x) * 10 ** (a.organ_db / 20)
    mix = backing[:, :n] + x[:, :n] * g
    peak = np.max(np.abs(mix))
    if peak > 0.95:
        mix = np.tanh(mix / peak * 1.6) / np.tanh(1.6) * 0.95
    organ.write_wav(a.out, mix)
    json.dump([dict(start=s, end=e, midi=p, reg=r) for s, e, p, r in notes], open(a.out + '.notes.json', 'w'))
    first = {r: min((s for s, _, _, rr in notes if rr == r), default=None) for r in stacks}
    print('melody notes %d  registration starts %s  -> %s'
          % (len(notes), {k: (round(v, 1) if v else None) for k, v in first.items()}, a.out))


if __name__ == '__main__':
    main()
