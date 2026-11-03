"""Play a song's vocal line on pipe organ from a score, aligned to the real singer, over the backing.

    python3 score_organ.py <song> <score_notes.json> <out.wav> --bpm 96 \
        --vocal-bars 5-24,29-48,59-78 --five-four 11,12,35,36,61,62 \
        --medium 63-70 --full 71-78

score_notes.json comes from score_read.py. The right-hand top line of the vocal bars
is the melody. Score time is aligned to the isolated vocal (Demucs stem) with DTW on
chroma (right-hand notes vs. the vocal), so every written note lands where it is
actually sung, even in choir passages where pitch tracking fails.
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


def align(melody, allrh, score_len, vocals_wav, hop=0.04, pyin_cache=None):
    """Map score time -> audio time with DTW. The cost uses the singer's pYIN pitch where it
    is clean (lead vocal) and vocal-stem chroma elsewhere (choir), then each note is nudged
    onto the nearby stretch where its pitch is actually sung."""
    import librosa
    y, sr = librosa.load(vocals_wav, sr=22050)
    h = int(hop * sr)
    A = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=h)
    na = A.shape[1]
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=h)[0][:na]
    voiced_a = rms > np.percentile(rms, 35)
    if pyin_cache and os.path.exists(pyin_cache):
        f0, vflag, vprob = np.load(pyin_cache)
        pt = np.arange(len(f0)) * 0.02
    else:
        y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
        f0, vflag, vprob = librosa.pyin(y16, fmin=80, fmax=1000, sr=16000, frame_length=2048, hop_length=320)
        pt = np.arange(len(f0)) * 0.02
    at = np.arange(na) * hop
    pm = np.interp(at, pt, np.where(vflag > 0, 69 + 12 * np.log2(np.nan_to_num(f0, nan=440) / 440), -1))
    pv = np.interp(at, pt, (vflag > 0).astype(float)) > 0.5
    ns = int(score_len / hop) + 1
    S = np.zeros((12, ns))
    sp = np.full(ns, -1)
    for s, e, m in allrh:
        S[m % 12, int(s / hop):int(e / hop) + 1] += 0.5
    for s, e, m, _ in melody:
        S[m % 12, int(s / hop):int(e / hop) + 1] += 1.0
        sp[int(s / hop):int(e / hop) + 1] = m % 12
    voiced_s = S.sum(0) > 0
    Sn = S / (np.linalg.norm(S, axis=0, keepdims=True) + 1e-9)
    An = A / (np.linalg.norm(A, axis=0, keepdims=True) + 1e-9)
    Cc = 1 - Sn.T @ An
    d = np.abs(sp[:, None] - np.round(pm)[None, :] % 12)
    d = np.minimum(d, 12 - d)
    Cp = np.clip(d / 2.0, 0, 1)
    use_p = (sp[:, None] >= 0) & pv[None, :]
    C = np.where(use_p, 0.7 * Cp + 0.3 * Cc, Cc)
    C[~voiced_s] = 0.9
    C[:, ~voiced_a] = 0.9
    C[np.ix_(~voiced_s, ~voiced_a)] = 0.1
    D, wp = librosa.sequence.dtw(C=C.astype(np.float32), step_sizes_sigma=np.array([[1, 1], [0, 1], [1, 0]]),
                                 weights_add=np.array([0, 0.12, 0.12]))
    cost = float(np.mean(C[wp[:, 0], wp[:, 1]]))
    wp = wp[::-1]
    smap = np.full(ns, np.nan)
    for i, j in wp:
        smap[i] = j * hop if np.isnan(smap[i]) else min(smap[i], j * hop)
    idx = np.arange(ns)
    ok = ~np.isnan(smap)
    smap = np.maximum.accumulate(np.interp(idx, idx[ok], smap[ok]))
    out = []
    for s, e, m, bar in melody:
        out.append([float(np.interp(s / hop, idx, smap)), float(np.interp(e / hop, idx, smap)), m, bar])
    # nudge: start each note where its pitch class first holds for 60 ms near the aligned onset
    sung_pc = np.where(pv, np.round(pm) % 12, -1)
    run = int(0.06 / hop)
    prev_end = 0.0
    for n in out:
        lo = max(prev_end - hop, n[0] - 0.25)
        hi = n[0] + 0.25
        best = None
        for j in range(int(lo / hop), int(hi / hop)):
            if 0 <= j < na - run and all(sung_pc[j:j + run] == n[2] % 12):
                if best is None or abs(j * hop - n[0]) < abs(best - n[0]):
                    best = j * hop
        if best is not None:
            shift = best - n[0]
            n[0] = best
            n[1] = max(n[0] + 0.08, n[1] + shift * 0.5)
        prev_end = n[0] + 0.05
    for i in range(len(out) - 1):  # legato, no overlaps
        if out[i + 1][0] > out[i][0]:
            out[i][1] = min(max(out[i][1], out[i][0] + 0.08), out[i + 1][0] - 0.005)
    return out, cost


def align_sections(melody, allrh, sections, vocals_wav, pyin_cache, beat):
    """Score and recording share a tempo, so each vocal section only needs a time offset:
    slide the section's notes along the singer's pitch track (pYIN where clean, vocal-stem
    chroma for choir passages) to the best match, keep sections in order, then refine
    each 2-bar block by up to +-0.5 s and nudge each note onto its sung pitch."""
    import librosa
    hop = 0.02
    f0, vflag, vprob = np.load(pyin_cache)
    pc = np.where(vflag > 0, np.round(69 + 12 * np.log2(np.nan_to_num(f0, nan=440) / 440)) % 12, -1).astype(int)
    y, sr = librosa.load(vocals_wav, sr=22050)
    A = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=int(hop * sr))[:, :len(pc)]
    A = A / (A.sum(0, keepdims=True) + 1e-9)
    n = min(len(pc), A.shape[1])
    pc, A = pc[:n], A[:, :n]

    def match(notes, off):
        tot = 0.0
        for s, e, m, _ in notes:
            a, b = int((s + off) / hop), int((e + off) / hop)
            a, b = max(0, a), min(n, max(a + 1, b))
            if b <= a:
                tot -= 1
                continue
            seg = pc[a:b]
            v = seg >= 0
            tot += np.sum(seg[v] == m % 12) - 0.35 * np.sum(seg[v] != m % 12) + 0.6 * A[m % 12, a:b].sum()
        return tot

    out, prev_end, prev_off = [], None, None
    for lo_bar, hi_bar in sections:
        sec = [x for x in melody if lo_bar <= x[3] <= hi_bar]
        if not sec:
            continue
        s0, s1 = sec[0][0], sec[-1][1]
        if prev_off is None:
            cands = np.arange(-15, 40, hop)
        else:
            cands = np.arange(prev_off - 6, prev_off + 40, hop)
        cands = [o for o in cands if prev_end is None or s0 + o >= prev_end - 0.2]
        coarse = cands[::5]
        best = max(coarse, key=lambda o: match(sec, o))
        best = max([o for o in cands if abs(o - best) <= 0.12], key=lambda o: match(sec, o))
        # 2-bar block refinement
        blocks = {}
        for x in sec:
            blocks.setdefault((x[3] - lo_bar) // 2, []).append(x)
        for k in sorted(blocks):
            blk = blocks[k]
            offs = np.arange(best - 0.5, best + 0.5 + 1e-9, hop)
            o = max(offs, key=lambda o: match(blk, o) - 2.0 * abs(o - best))
            out.extend([[x[0] + o, x[1] + o, x[2], x[3]] for x in blk])
        prev_end = out[-1][1]
        prev_off = best
    out.sort(key=lambda x: x[0])
    run = int(0.06 / hop)
    prev = 0.0
    for x in out:  # nudge onto the sung pitch, small moves only
        lo, hi = max(prev, x[0] - 0.15), x[0] + 0.15
        cand = [j * hop for j in range(int(lo / hop), int(hi / hop)) if 0 <= j < n - run and np.all(pc[j:j + run] == x[2] % 12)]
        if cand:
            nb = min(cand, key=lambda t: abs(t - x[0]))
            x[1] += nb - x[0]
            x[0] = nb
        prev = x[0] + 0.04
    for i in range(len(out) - 1):
        if out[i + 1][0] > out[i][0]:
            out[i][1] = min(max(out[i][1], out[i][0] + 0.08), out[i + 1][0] - 0.005)
    return out, match(out, 0.0) / max(1, len(out))


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
    aligned, cost = align_sections(melody, allrh, secs, stems['vocals'], os.path.join(cache, 'pyin_f0.npy'), 60 / a.bpm)
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
    print('melody notes %d  mean match score %.2f  registration starts %s  -> %s'
          % (len(notes), cost, {k: (round(v, 1) if v else None) for k, v in first.items()}, a.out))


if __name__ == '__main__':
    main()
