"""Song analysis (tempo, beat grid, highest-energy window) and a placeholder
drum track for drafts before the real song is in."""
import subprocess
import sys
import wave

import numpy as np

SR = 44100


def load_mono(path, sr=22050, start=None, dur=None):
    cmd = ['ffmpeg', '-v', 'error']
    if start is not None:
        cmd += ['-ss', str(start)]
    cmd += ['-i', path]
    if dur is not None:
        cmd += ['-t', str(dur)]
    cmd += ['-ac', '1', '-ar', str(sr), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32), sr


def onset_env(x, sr, hop=256, n=1024):
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    S = np.abs(np.fft.rfft(fr * np.hanning(n), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(S * 10), axis=0)).sum(1)
    flux = np.concatenate([[0], flux])
    return flux / (flux.max() + 1e-9), sr / hop


def tempo_and_phase(env, fps, lo=70, hi=200):
    e = env - env.mean()
    ac = np.correlate(e, e, 'full')[len(e) - 1:]
    lags = np.arange(len(ac)) / fps
    m = (lags > 60 / hi) & (lags < 60 / lo)
    period = lags[m][np.argmax(ac[m])]
    best = (-1, 0, 0)
    for bpm in np.arange(60 / period - 2, 60 / period + 2, 0.02):
        P = 60 / bpm * fps
        for o in np.arange(0, P, 0.5):
            idx = (o + np.arange(0, (len(env) - o) / P) * P).astype(int)
            s = env[idx].mean()
            if s > best[0]:
                best = (s, bpm, o / fps)
    return best[1], best[2]


def analyze(path, window=30.0):
    x, sr = load_mono(path)
    env, fps = onset_env(x, sr)
    bpm, phase = tempo_and_phase(env, fps)
    hop = sr // 2
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2) + 1e-12) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(rms)
    ons = np.array([env[int(i / sr * fps):int((i + hop) / sr * fps)].mean() for i in range(0, len(x) - hop, hop)])
    score = (db - db.max()) / 6 + ons / (ons.max() + 1e-9)
    n = int(window * 2)
    win = np.convolve(score, np.ones(n) / n, 'valid')
    beat = 60 / bpm
    order = np.argsort(win)[::-1]
    picks = []
    for i in order:
        t = i / 2
        if all(abs(t - q) > window / 2 for q, _ in picks):
            picks.append((t, win[i]))
        if len(picks) == 3:
            break
    snapped = [(round((t - phase) / beat) * beat + phase, s) for t, s in picks]
    return dict(bpm=float(bpm), phase=float(phase), duration=len(x) / sr, windows=snapped,
                loudness_by_sec=db[::2].round(1).tolist())


# ---------------------------------------------------------------- placeholder drums

def _env(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def _hp(x, a=0.9):
    y = np.empty_like(x)
    prev_x = prev_y = 0.0
    for i, v in enumerate(x):
        prev_y = a * (prev_y + v - prev_x)
        prev_x = v
        y[i] = prev_y
    return y


def drums(bpm, dur, path, braams=(), screech=None, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR) + SR
    out = np.zeros(n, np.float32)
    t = np.arange(int(0.45 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-t / 0.035)) / SR) * _env(len(t), 0.22)
    kick[:120] += rng.normal(0, 0.6, 120) * np.linspace(1, 0, 120)
    sn_n = int(0.3 * SR)
    snare = _hp(rng.normal(0, 1, sn_n).astype(np.float32), 0.8) * _env(sn_n, 0.09) * 0.9
    snare += np.sin(2 * np.pi * 190 * np.arange(sn_n) / SR) * _env(sn_n, 0.05) * 0.6
    hh_n = int(0.06 * SR)
    hat = _hp(rng.normal(0, 1, hh_n).astype(np.float32), 0.6) * _env(hh_n, 0.015) * 0.35
    cr_n = int(1.6 * SR)
    crash = _hp(rng.normal(0, 1, cr_n).astype(np.float32), 0.7) * _env(cr_n, 0.5) * 0.4

    def put(s, at, g=1.0):
        i = int(at * SR)
        if i < n:
            m = min(len(s), n - i)
            out[i:i + m] += s[:m] * g

    beat = 60 / bpm
    nb = int(dur / beat) + 1
    for b in range(nb):
        tb = b * beat
        if b % 2 == 0:
            put(kick, tb, 1.0)
        else:
            put(snare, tb, 0.9)
        if b % 4 == 2:
            put(kick, tb + beat / 2, 0.8)
        put(hat, tb + beat / 2, 1.0)
        put(hat, tb, 0.6)
    tt = np.arange(int(1.8 * SR)) / SR
    for at in braams:
        saw = sum(((tt * f) % 1 * 2 - 1) for f in (41.2, 61.7, 82.4, 123.5))
        br = np.tanh(saw * 1.6) * np.minimum(1, tt / 0.01) * np.exp(-tt / 0.7) * 0.45
        put(br.astype(np.float32), at)
        put(crash, at)
    if screech is not None:
        st = np.arange(int(0.9 * SR)) / SR
        fr = 2900 - 1100 * (st / 0.9) ** 0.6 + 140 * np.sin(2 * np.pi * 31 * st)
        sc = np.tanh(3 * np.sin(2 * np.pi * np.cumsum(fr) / SR)) * np.minimum(1, st / 0.03) * np.exp(-st / 0.35) * 0.3
        put(sc.astype(np.float32), screech)
    out = np.tanh(out * 1.3) * 0.85
    pcm = (np.clip(out[:int(dur * SR)], -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.repeat(pcm[:, None], 2, 1).tobytes())


if __name__ == '__main__':
    import json
    r = analyze(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 30.0)
    print(json.dumps({k: v for k, v in r.items() if k != 'loudness_by_sec'}, indent=1))
    print('loudness dB by second:', r['loudness_by_sec'])
