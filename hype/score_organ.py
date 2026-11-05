"""Play a song's vocal line on pipe organ from a score, aligned to the real singer, over the backing.

    python3 score_organ.py <song> <score_notes.json> <out.wav> --config organ_songs/<song>.json [--stems]

The config holds the song's bar plan (tempo, vocal bars, 5/4 bars), the registration plan
(which bars get which stops), any rhythms read by hand, a pedal line, a closing chord, and
each part's room and level; see organ_songs/soldier_of_heaven.json.
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


def play_order(n_bars, repeats=()):
    """Bar numbers in performance order, with each (first, last) repeat played twice."""
    order, b = [], 1
    reps = {lo: hi for lo, hi in repeats}
    while b <= n_bars:
        if b in reps:
            seg = list(range(b, reps[b] + 1))
            order += seg + seg
            b = reps[b] + 1
        else:
            order.append(b)
            b += 1
    return order


def score_events(bars, vocal, five, bpm, repeats=(), hollow_ties=True):
    """Melody (top RH note per onset), the RH chord under each melody note, all RH notes,
    and each bar's start (the last pass, for repeated bars), in score seconds."""
    beat = 60.0 / bpm
    t_bar, melody, allrh, chords, starts = 0.0, [], [], [], {}
    by_num = {b['bar']: b for b in bars}
    for bn in play_order(len(bars), repeats):
        b = by_num[bn]
        nb = 5 if b['bar'] in five else 4
        starts[b['bar']] = t_bar
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
                if hollow_ties and not filled and prev_top is not None and any((n['midi'] - prev_top) % 12 == 0 for n in c):
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
                chords.append(sorted(set(all_)))
                allrh.extend([s, e, m] for m in all_)
        t_bar += nb * beat
    starts[len(bars) + 1] = t_bar
    return melody, allrh, chords, starts


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


def align_grid(melody, sections, feats, phase, beat, window=4, sustain=True, fixed=None, starts=None, offsets=None,
               repeat_gap=0.04, gap=0.005):
    """Score and recording share an exact tempo, so the score maps onto the recording's
    beat grid by a whole number of beats (searched globally, per section only when a
    section clearly prefers another). Within a section each note then snaps to a 16th
    slot near its engraved position by dynamic programming over: the singer's onset
    strength, the sung pitch (pYIN, chroma) holding the note's pitch until the next
    note, a mild preference for beats and 8ths, and distance from the engraved spot.
    fixed: {bar: [(16th slot in bar, length in 16ths), ...]} pins bars whose rhythm has been
    read by hand (needs starts, the score's bar starts). Output notes carry their melody index."""
    fixed = fixed or {}
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

    index = {id(x): i for i, x in enumerate(melody)}
    secs = [[x for x in melody if lo <= x[3] <= hi] for lo, hi in sections]
    secs = [s for s in secs if s]
    ks = range(-8, 41)
    kg = max(ks, key=lambda k: sum(match(s, k) for s in secs))
    out, report, pinned, tied = [], [], set(), set()
    offsets = offsets or {}  # {first bar of a section: beats}, for arrangements that cut or stretch sections
    for sec in secs:
        scores = {k: match(sec, k) for k in ks}
        kb = max(scores, key=scores.get)
        k = kb if scores[kb] > 1.25 * max(scores[kg], 1e-9) else kg
        if sec[0][3] in offsets:
            k = offsets[sec[0][3]]
        report.append((sec[0][3], sec[-1][3], k, kb))
        p = [s / slot + 4 * k for s, _, _, _ in sec]
        pe = [e / slot + 4 * k for _, e, _, _ in sec]
        cand = [list(range(int(np.floor(x)) - window, int(np.ceil(x)) + window + 1)) for x in p]
        for b in sorted({x[3] for x in sec} & set(fixed)):
            idx = [i for i, x in enumerate(sec) if x[3] == b]
            if len(idx) != len(fixed[b]):
                print('  bar %d: %d notes read but %d rhythm slots given; left to the aligner'
                      % (b, len(idx), len(fixed[b])))
                continue
            b0 = starts[b] / slot + 4 * k
            prev_end = None
            for i, ent in zip(idx, fixed[b]):
                if ent[0] == 'tie':  # a tied note: held on from the previous one, not struck again
                    sl, ln = prev_end, ent[1]
                    tied.add(id(sec[i]))
                else:
                    sl, ln = ent
                prev_end = sl + ln
                p[i], pe[i], cand[i] = b0 + sl, b0 + sl + ln, [int(round(b0 + sl))]
                pinned.add(id(sec[i]))
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
            if id(x) in tied and out:
                out[-1][1] = phase + max(j + 1, pe[i] + shift) * slot
                continue
            out.append([phase + j * slot, phase + max(j + 1, end) * slot, x[2], x[3], index[id(x)]])
    out.sort(key=lambda x: x[0])
    for i, x in enumerate(out if sustain else []):  # hold through the singer's sustain (ties across barlines aren't read)
        if id(melody[x[4]]) in pinned:
            continue
        nxt = out[i + 1][0] if i + 1 < len(out) else x[1] + 4 * beat
        j = int(round((x[1] - phase) / slot))
        while j < ns and phase + j * slot < min(nxt, x[1] + 2 * beat) and R[j] > 0.3:
            j += 1
        x[1] = max(x[1], min(nxt, phase + j * slot))
    for i in range(len(out) - 1):  # legato, with a lift of the key before a repeated note (else they blur into one)
        nxt = out[i + 1][0]
        g = min(repeat_gap, 0.3 * (nxt - out[i][0])) if out[i + 1][2] == out[i][2] else gap
        if out[i][1] > nxt - g:
            out[i][1] = nxt - g
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
        for s, e, m in (x[:3] for x in ns):
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
            r = {k: score([[x[0], x[1], scale_step(x[2], k, scale)] for x in ns])[0]
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


def render(notes, stacks, sf2, swell, length):
    """notes: (start, end, midi, stack name). Every rank of every stack gets its own channel."""
    import tinysoundfont
    syn = tinysoundfont.Synth(samplerate=SR, gain=-8)
    sfid = syn.sfload(sf2)
    chans, ch = {}, 0
    for name, stack in stacks.items():
        for i, (bank, preset, _, _) in enumerate(stack):
            if ch == 9:  # GM drum channel
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
    n = max(int(2 * SR), int(round((length - t) * SR)))
    chunks.append(np.frombuffer(syn.generate(n), np.float32).copy())
    x = np.concatenate(chunks).reshape(-1, 2).T
    return x[:, :int(length * SR)]


def limit(x, ceiling=0.97, lookahead=0.005, release=0.15):
    """Look-ahead peak limiter: gain falls over a few ms just before a peak and recovers
    exponentially, so sustained organ chords don't pump on every drum hit."""
    from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
    blk = int(SR / 1000)  # 1 ms control rate
    nb = x.shape[1] // blk + 1
    env = np.abs(x).max(0)
    env = np.pad(env, (0, nb * blk - len(env))).reshape(nb, blk).max(1)
    la = max(1, int(lookahead * 1000))
    env = maximum_filter1d(env, 2 * la + 1, origin=-la)  # sees peaks coming
    target = np.minimum(1.0, ceiling / np.maximum(env, 1e-9))
    g = np.empty(nb)
    r = 1 - np.exp(-0.001 / release)
    prev = 1.0
    for k in range(nb):
        prev = min(target[k], prev + (1 - prev) * r)
        g[k] = prev
    g = uniform_filter1d(minimum_filter1d(g, la, origin=-(la // 2)), la)
    gs = np.interp(np.arange(x.shape[1]), np.arange(nb) * blk + blk / 2, g)
    return np.clip(x * gs, -ceiling, ceiling)


def mix_parts(out, stems, notes, final_notes, final_t0, final_gain_db, parts, swell, stacks, sf2,
              organ_db=1.0, master_db=0.0, write_stems=False, tail=0.0):
    """Render the organ part by part over the Demucs backing and write the limited mix.
    Each part (dict: label, t0, t1 or None for 'to the end', reverb [rt60, wet, hp], boost_db,
    final) gets its own room and level: the organ's RMS over the sung notes there matches
    the singer's, plus the part's boost. The closing chord (final_notes, from final_t0) is
    levelled on its own so it crowns the band instead of crushing it."""
    from scipy.signal import butter, sosfiltfilt
    backing = sum(organ.load_stereo(stems[k]) for k in ('drums', 'bass', 'other'))
    vocal = organ.load_stereo(stems['vocals'])
    n = min(backing.shape[1], vocal.shape[1])
    pad = int(tail * SR)  # room for the organ's last reverb past the end of the recording
    backing = np.pad(backing[:, :n], ((0, 0), (0, pad)))
    vocal = np.pad(vocal[:, :n], ((0, 0), (0, pad)))
    n += pad
    length = n / SR
    organ_x = np.zeros((2, n), np.float32)
    for part in parts:
        t0, t1 = part['t0'], part['t1'] if part['t1'] is not None else length
        sel = [x for x in notes if t0 <= x[0] < t1]
        if not sel:
            continue
        dry = render(sel, stacks, sf2, swell, length)
        if part.get('final') and final_notes:
            dry += render(final_notes, stacks, sf2, swell, length) * 10 ** (final_gain_db / 20)
        dry = sosfiltfilt(butter(2, 25, 'highpass', fs=SR, output='sos'), dry, axis=1)  # sample DC, rumble
        rt, wet, hp = part['reverb']
        x = organ.cathedral(dry, rt60=rt, wet=wet, hp=hp)
        voiced = np.zeros(n, bool)
        for s, e, _, r in sel:
            if r not in ('chord', 'pedal') and (final_t0 is None or s < final_t0):
                voiced[int(s * SR):min(n, int(e * SR))] = True
        rms = lambda z: np.sqrt(np.mean(z[:, :n][:, voiced] ** 2)) + 1e-9
        g = rms(vocal) / rms(x) * 10 ** ((organ_db + part.get('boost_db', 0)) / 20)
        organ_x += x[:, :n] * g
        print('  %s: reverb %.1f s, organ %+.1f dB vs. the vocal' % (part['label'], rt, organ_db + part.get('boost_db', 0)))
    mix = backing[:, :n] + organ_x
    if write_stems:  # the organ alone and the backing alone, at the mix's scale, for video editing
        import soundfile as sf
        sf.write(out[:-4] + '.organ.wav', organ_x.T, SR, subtype='FLOAT')
        sf.write(out[:-4] + '.backing.wav', backing[:, :n].T, SR, subtype='FLOAT')
    pk = np.abs(mix).max(0)
    w = SR // 2
    loud = sorted(((pk[i:i + w].max(), i / SR) for i in range(0, n - w, w)), reverse=True)[:5]
    print('  limiter: loudest peaks %s' % ', '.join('%+.1f dB at %.1f s' % (20 * np.log10(v / 0.97), t) for v, t in loud))
    organ.write_wav(out, limit(mix * 10 ** (master_db / 20)))


def note_midi(name):
    letters = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    m = letters[name[0]]
    rest = name[1:]
    while rest and rest[0] in 'b#':
        m += -1 if rest[0] == 'b' else 1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + m


def bar_set(spec):
    return ranges(str(spec))


def main():
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('score')
    ap.add_argument('out')
    ap.add_argument('--config', help='song JSON: bars, registration plan, hand-read rhythms, pedal, final chord')
    ap.add_argument('--bpm', type=float)
    ap.add_argument('--vocal-bars')
    ap.add_argument('--five-four', default='')
    ap.add_argument('--sections', default='', help='alignment sections (default: the vocal-bar ranges)')
    ap.add_argument('--transpose', type=int, default=0)
    ap.add_argument('--no-follow-singer', dest='follow_singer', action='store_false',
                    help='play the arrangement as written even where the singer sings other notes')
    ap.add_argument('--lead', type=float, default=0.02, help='start organ notes this early (pipe attack)')
    ap.add_argument('--organ-db', type=float, default=1.0, help='organ level vs. the original vocal')
    ap.add_argument('--sf2', default=organ.SF2)
    ap.add_argument('--stems', action='store_true', help='also write the organ and the backing on their own')
    ap.add_argument('--final-release', type=float, help="override the closing chord's release time (s)")
    a = ap.parse_args()
    cfg = json.load(open(a.config)) if a.config else {}
    for k in ('bpm', 'vocal_bars', 'five_four', 'sections'):
        if k in cfg and not getattr(a, k):
            setattr(a, k, cfg[k])
    if not a.bpm or not a.vocal_bars:
        ap.error('--bpm and --vocal-bars (or a --config with them) are required')

    h = hashlib.sha1(open(a.song, 'rb').read()).hexdigest()[:12]
    cache = os.path.join(organ.CACHE, h)
    os.makedirs(cache, exist_ok=True)
    stems = organ.separate(a.song, cache)
    bars = json.load(open(a.score))
    melody, allrh, chords, starts = score_events(bars, ranges(a.vocal_bars), ranges(a.five_four), a.bpm,
                                                 [tuple(r) for r in cfg.get('repeats', [])], cfg.get('hollow_ties', True))
    secs = []
    for part in filter(None, (a.sections or a.vocal_bars).split(',')):
        lo, _, hi = part.partition('-')
        secs.append((int(lo), int(hi or lo)))
    fixed = {}
    for spec, slots in cfg.get('rhythm', {}).items():
        for b in bar_set(spec):
            fixed[b] = [tuple(s) for s in slots]
    beat = 60 / a.bpm
    phase = beat_grid(stems['drums'], a.bpm)
    feats = slot_features(stems['vocals'], os.path.join(cache, 'pyin_f0.npy'), phase, beat / 4,
                          os.path.join(cache, 'slotfeat.npz'))
    offs = {int(str(b).split('-')[0]): int(k) for b, k in cfg.get('section_offsets', {}).items()}
    grid = lambda **kw: align_grid(melody, secs, feats, phase, beat, fixed=fixed, starts=starts, offsets=offs,
                                   repeat_gap=cfg.get('repeat_gap', 0.04), gap=cfg.get('gap', 0.005), **kw)
    aligned, kg, report = grid()
    changed = []
    if a.follow_singer:  # fix bars the arrangement harmonises, then re-snap them with the right pitches
        rough, _, _ = grid(sustain=False)
        changed = follow_singer(rough, secs, os.path.join(cache, 'pyin_f0.npy'))
        for b, k, scale in changed:
            for x in melody:
                if x[3] == b:
                    x[2] = scale_step(x[2], k, scale)
        if changed:
            aligned, kg, report = grid()
    print('beat grid phase %.3f s, score -> recording offset %d beats' % (phase, kg))
    for lo, hi, k, kb in report:
        print('  bars %d-%d: offset %d beats (section alone prefers %d)' % (lo, hi, k, kb))
    for b, k, _ in changed:
        print('  bar %d: arrangement differs from the singer, melody moved %+d scale steps' % (b, k))
    sec_k = sorted((lo, offs.get(lo, kg)) for lo, _ in secs)

    def k_at(b):  # the offset in force at bar b: its section's, else the last section's before it
        ks_ = [k for lo, k in sec_k if lo <= b]
        return ks_[-1] if ks_ else kg

    def bar_time(b, beats=0.0):  # recording time of a score bar (+ beats)
        b = min(b, max(starts))
        return phase + (starts[b] / beat + k_at(b) + beats) * beat

    # registration plan: [[bars, stack name], ...]; stacks: built-ins or the config's own
    stacks = {'simple': organ_vocal.SIMPLE, 'medium': MEDIUM, 'full': organ_vocal.FULL}
    stacks.update({k: [tuple(r) for r in v] for k, v in cfg.get('stacks', {}).items()})
    plan = [(bar_set(b), name) for b, name in cfg.get('registration', [])]
    reg_of = lambda bar: next((name for bs, name in plan if bar in bs), 'simple')
    shifted = {b for b, _, _ in changed}
    chord_bars = bar_set(cfg.get('chords', '')) - shifted
    notes = []
    for s, e, p, bar, i in aligned:
        s, e, r = s - a.lead, e - a.lead, reg_of(bar)
        notes.append((s, e, p + a.transpose, r))
        if bar in chord_bars:  # the arranger's chord under the tune, on lighter ranks
            notes += [(s, e, c + a.transpose, 'chord') for c in chords[i] if c < p and (p - c) % 12]
    pedal = cfg.get('pedal', {})
    pev = sorted((bar_time(int(b), bt) - a.lead, note_midi(nm), int(b)) for b, evs in pedal.items() for bt, nm in evs
                 if int(b) in starts)
    fc = cfg.get('final_chord')
    if fc and fc['bar'] not in starts:
        print('  closing chord bar %d is not in this score; skipped' % fc['bar'])
        fc = None
    if fc and a.final_release:
        fc = dict(fc, release=a.final_release)
    end_t, final_notes = None, []
    if fc:
        t0 = bar_time(fc['bar']) - a.lead
        end_t = fc['release']
        r = reg_of(fc['bar'])
        final_notes = [(t0, end_t, note_midi(nm) + a.transpose, r) for nm in fc['notes']]
        if fc.get('pedal'):
            final_notes.append((t0, end_t, note_midi(fc['pedal']) + a.transpose, 'pedal'))
    for j, (t, m, b) in enumerate(pev):
        e = pev[j + 1][0] - 0.01 if j + 1 < len(pev) else (
            bar_time(fc['bar']) - a.lead - 0.01 if fc else bar_time(b + 1) - a.lead - 0.01)
        notes.append((t, e, m + a.transpose, 'pedal'))
    notes.sort()

    # swell follows the singer, with a floor per bar range (flat out in the big sections)
    swell = organ_vocal.expression(stems['vocals'], [(s, e, p, 1) for s, e, p, r in notes if r not in ('chord', 'pedal')])
    floors = [(bar_time(min(bar_set(b))), bar_time(max(bar_set(b)) + 1), v) for b, v in cfg.get('swell_floor', [])]
    if fc:
        floors.append((bar_time(fc['bar']), end_t + 1, 127))
    swell = [(t, max([v] + [fv for t0, t1, fv in floors if t0 <= t < t1])) for t, v in swell]

    final_t0 = bar_time(fc['bar']) - 0.1 if fc else None
    parts = []
    for part in cfg.get('parts', [{'bars': '1-999', 'reverb': [1.8, 0.25, 250.0], 'boost_db': 0}]):
        bs = bar_set(part['bars'])
        has_final = bool(fc and fc['bar'] in bs)
        parts.append(dict(part, label='bars ' + str(part['bars']), t0=bar_time(min(bs)) - 0.3,
                          t1=None if has_final else bar_time(min(max(bs) + 1, max(starts))) - 0.3, final=has_final))
    mix_parts(a.out, stems, notes, final_notes, final_t0, fc.get('gain_db', 0) if fc else 0, parts, swell,
              stacks, a.sf2, a.organ_db, cfg.get('master_db', 0), a.stems, cfg.get('tail', 0.0))
    json.dump([dict(start=s, end=e, midi=int(p), reg=r) for s, e, p, r in notes + final_notes], open(a.out + '.notes.json', 'w'))
    print('notes %d (melody %d)  -> %s' % (len(notes), len(aligned), a.out))


if __name__ == '__main__':
    main()
