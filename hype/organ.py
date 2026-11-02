"""Reimagine a song on a pipe organ.

    python3 organ.py <song> <out.wav> [--start SEC --dur SEC]

Tracks the lead melody, chords and bass on a 16th-note grid locked to the
song's beat, then plays them on an additive pipe organ (trumpet reed melody,
pumping full-organ chords, 16' pedal) in a synthetic cathedral. The organ's
dynamics follow the original's loudness, so choruses swell.
"""
import argparse
import math
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio  # noqa: E402

SR = 44100
AN_SR = 22050
MIDI = np.arange(36, 97)  # C2..C7

PEDAL = [(0.5, 0.9), (1, 0.75), (2, 0.25), (3, 0.08)]
CHORD = [(0.5, 0.35), (1, 1.0), (2, 0.6), (3, 0.3), (4, 0.33), (6, 0.18), (8, 0.14)]
REED = [(1, 1.0), (2, 0.85), (3, 0.65), (4, 0.5), (5, 0.42), (6, 0.32), (7, 0.22), (8, 0.18), (10, 0.1)]


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def analyze(x, sr, bpm, phase):
    step = 60 / bpm / 4
    n = int((len(x) / sr - phase) / step) - 1
    nfft = 8192
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    W = np.zeros((len(MIDI), len(freqs)), np.float32)
    for i, m in enumerate(MIDI):
        f = mtof(m)
        W[i, (freqs >= f * 2 ** (-0.5 / 12)) & (freqs < f * 2 ** (0.5 / 12))] = 1
    win = np.hanning(nfft).astype(np.float32)
    E = np.zeros((n, len(MIDI)), np.float32)
    rms = np.zeros(n, np.float32)
    for k in range(n):
        c = int((phase + (k + 0.5) * step) * sr)
        seg = x[max(0, c - nfft // 2):c + nfft // 2]
        if len(seg) < nfft:
            seg = np.pad(seg, (0, nfft - len(seg)))
        S = np.abs(np.fft.rfft(seg * win))
        E[k] = W @ S
        rms[k] = np.sqrt(np.mean(seg ** 2) + 1e-12)
    sal = np.zeros_like(E)
    for h in range(1, 6):
        sh = int(round(12 * math.log2(h)))
        sal[:, :len(MIDI) - sh] += 0.85 ** (h - 1) * E[:, sh:]
    return step, E, sal, rms


def melody(sal):
    lo, hi = 57 - 36, 84 - 36
    band = sal[:, lo:hi + 1]
    peak = band.max(1)
    pitch = band.argmax(1) + 57
    voiced = (peak > np.percentile(peak, 35)) & (peak > 1.6 * np.median(band, 1))
    p = np.where(voiced, pitch, 0)
    out = p.copy()
    for k in range(1, len(p) - 1):  # median-of-3 on voiced runs
        w = [v for v in p[k - 1:k + 2] if v]
        if p[k] and len(w) == 3:
            out[k] = int(np.median(w))
    return out


TEMPL = []
for r in range(12):
    for q, iv in (('maj', (0, 4, 7)), ('min', (0, 3, 7))):
        t = np.zeros(12)
        t[[(r + i) % 12 for i in iv]] = 1
        TEMPL.append((r, q, (t - t.mean()) / t.std()))


MAJ_PROF = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN_PROF = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_of(chroma):
    tot = chroma.sum(0)
    best = max(((np.corrcoef(np.roll(p, k), tot)[0, 1], k, mode) for k in range(12)
                for p, mode in ((MAJ_PROF, 'maj'), (MIN_PROF, 'min'))))
    return best[1], best[2]


def diatonic(tonic, mode):
    """Triads that belong to the key (minor also allows the major V)."""
    if mode == 'maj':
        degs = [(0, 'maj'), (2, 'min'), (4, 'min'), (5, 'maj'), (7, 'maj'), (9, 'min')]
    else:
        degs = [(0, 'min'), (3, 'maj'), (5, 'min'), (7, 'min'), (7, 'maj'), (8, 'maj'), (10, 'maj')]
    return {((tonic + d) % 12, q) for d, q in degs}


def chords(E, beats_per=2):
    pcs = MIDI % 12
    band = (MIDI >= 40) & (MIDI <= 76)
    chroma = np.zeros((len(E), 12))
    for i in np.where(band)[0]:
        chroma[:, pcs[i]] += E[:, i]
    allowed = diatonic(*key_of(chroma))
    cand = [j for j, (r, q, _) in enumerate(TEMPL) if (r, q) in allowed]
    spb = 4 * beats_per
    nwin = len(E) // spb
    best = []
    for w in range(nwin):
        c = chroma[w * spb:(w + 1) * spb].sum(0)
        c = (c - c.mean()) / (c.std() + 1e-9)
        best.append(max(cand, key=lambda j: float(c @ TEMPL[j][2])))
    sm = best[:]
    for w in range(1, nwin - 1):  # majority of 3 windows
        trio = best[w - 1:w + 2]
        sm[w] = max(set(trio), key=trio.count)
    return [TEMPL[j][:2] for j in sm], spb


_cache = {}


def note(m, nsteps, step, stops, attack=0.035, release=0.18):
    key = (m, nsteps, id(stops))
    if key in _cache:
        return _cache[key]
    dur = nsteps * step
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    f = mtof(m)
    rng = np.random.default_rng(m * 131 + nsteps)
    sig = np.zeros(n)
    for mult, amp in stops:
        ff = f * mult
        if ff > SR * 0.45:
            continue
        for det in (-1.2, 1.2):  # two slightly detuned ranks
            sig += 0.5 * amp * np.sin(2 * np.pi * ff * 2 ** (det / 1200) * t + rng.uniform(0, 6.28))
    env = np.minimum(1, t / attack)
    tail = t > dur
    env[tail] *= np.exp(-(t[tail] - dur) / (release / 3))
    chiff = rng.normal(0, 1, n) * np.exp(-t / 0.012) * 0.15
    out = (sig * env + chiff * (t < 0.06)) / max(1.0, sum(a for _, a in stops))
    _cache[key] = out.astype(np.float32)
    return _cache[key]


def place(buf, sig, at, gain, pan):
    i = int(at * SR)
    if i >= buf.shape[1]:
        return
    j = min(buf.shape[1], i + len(sig))
    s = sig[:j - i] * gain
    buf[0, i:j] += s * math.cos((pan + 1) * math.pi / 4)
    buf[1, i:j] += s * math.sin((pan + 1) * math.pi / 4)


def cathedral(buf, rt60=3.4, wet=0.55):
    n = int(rt60 * 1.3 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    out = np.zeros_like(buf)
    L = buf.shape[1] + n
    nfft = 1 << int(math.ceil(math.log2(L)))
    for ch in range(2):
        ir = rng.normal(0, 1, n) * np.exp(-6.91 * t / rt60)
        spec = np.fft.rfft(ir)
        fr = np.fft.rfftfreq(n, 1 / SR)
        spec *= 1 / (1 + (fr / 3500) ** 2)  # darker tail
        ir = np.fft.irfft(spec, n)
        ir[:int(0.025 * SR)] = 0  # pre-delay
        ir /= np.sqrt(np.sum(ir ** 2))
        wetsig = np.fft.irfft(np.fft.rfft(buf[ch], nfft) * np.fft.rfft(ir, nfft), nfft)[:buf.shape[1]]
        out[ch] = buf[ch] * (1 - wet * 0.5) + wetsig * wet * 6
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('out')
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--dur', type=float)
    a = ap.parse_args()
    x, sr = audio.load_mono(a.song, sr=AN_SR, start=a.start or None, dur=a.dur)
    env, fps = audio.onset_env(x, sr)
    bpm, phase = audio.tempo_and_phase(env, fps)
    step, E, sal, rms = analyze(x, sr, bpm, phase)
    mel = melody(sal)
    chs, spb = chords(E)
    db = 20 * np.log10(rms + 1e-9)
    beat_db = np.array([db[k:k + 4].mean() for k in range(0, len(db), 4)])
    gain = np.clip(10 ** ((beat_db - np.percentile(beat_db, 95)) / 20 * 0.9), 0.2, 1.0)
    total = phase + len(E) * step + 2.0
    buf = np.zeros((2, int(total * SR)), np.float32)

    nbeats = len(E) // 4
    for b in range(nbeats):
        w = min(len(chs) - 1, (b * 4) // spb)
        root, q = chs[w]
        g = float(gain[min(b, len(gain) - 1)])
        t0 = phase + b * 4 * step
        bass = 36 + root
        place(buf, note(bass + (12 if b % 2 else 0), 3, step, PEDAL), t0, 0.55 * g, 0.0)
        tones = [root, root + (4 if q == 'maj' else 3), root + 7]
        for tn in tones:
            m = 55 + ((tn - 55) % 12)
            place(buf, note(m, 3, step, CHORD), t0, 0.22 * g, -0.35 + 0.35 * tones.index(tn))
    k = 0
    while k < len(mel):
        if not mel[k]:
            k += 1
            continue
        j = k
        while j + 1 < len(mel) and mel[j + 1] == mel[k] and j - k < 7:
            j += 1
        g = float(gain[min(k // 4, len(gain) - 1)])
        place(buf, note(int(mel[k]) + 12 if mel[k] < 64 else int(mel[k]), j - k + 1, step, REED),
              phase + k * step, 0.34 * g, 0.05)
        k = j + 1

    out = cathedral(buf)
    out = np.tanh(out / (np.max(np.abs(out)) + 1e-9) * 1.4)
    out = out / np.max(np.abs(out)) * 0.89
    pcm = (out.T * 32767).astype(np.int16)
    with wave.open(a.out, 'wb') as wv:
        wv.setnchannels(2)
        wv.setsampwidth(2)
        wv.setframerate(SR)
        wv.writeframes(pcm.tobytes())
    voiced = (mel > 0).mean()
    print('bpm %.2f  steps %d  chords %d  melody voiced %.0f%%  -> %s' % (bpm, len(E), len(chs), voiced * 100, a.out))


if __name__ == '__main__':
    main()
