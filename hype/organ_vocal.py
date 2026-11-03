"""Swap a song's lead vocal for a pipe organ, over the song's real backing track.

    python3 organ_vocal.py <song> <out.wav> [--intense START END] [--center MIDI]

1. Demucs splits the song; drums + bass + other become the backing track.
2. The isolated vocal is transcribed to notes (pYIN pitch track split at syllable
   onsets, gaps filled by Basic Pitch), keeping the singer's own timing.
3. The organ plays only that vocal line, an octave placement chosen so it sits like
   a lead (median around A4 by default). Normal sections use a simple registration
   (8' with a soft 4'); the song's most intense stretch pulls out all the stops
   (16', two 8' ranks, 4', 2 2/3', 2', 1 1/3'). The organ's swell follows the
   singer's own loudness.
4. The organ gets a light hall and is mixed over the backing at the vocal's level.
"""
import argparse
import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio  # noqa: E402
import organ  # noqa: E402

SR = organ.SR
# (bank, preset, semitone offset, velocity scale)
SIMPLE = [(0, 19, 0, 1.0), (8, 19, 12, 0.45)]
FULL = [(0, 19, -12, 0.8), (0, 19, 0, 1.0), (8, 19, 0, 0.9), (0, 19, 12, 0.85),
        (8, 19, 19, 0.5), (0, 19, 24, 0.55), (8, 19, 31, 0.3)]


def intense_region(song, beat_times, min_len=16.0):
    """The loudest contiguous stretch of the full mix, snapped to bars."""
    y, sr = audio.load_mono(song, sr=22050)
    hop = sr // 2
    db = np.array([20 * np.log10(np.sqrt(np.mean(y[i:i + hop] ** 2)) + 1e-9) for i in range(0, len(y) - hop, hop)])
    k = 20  # 10 s window
    sm = np.convolve(db, np.ones(k) / k, 'same')
    c = int(np.argmax(sm))
    lo = hi = c
    while lo > 0 and sm[lo - 1] >= sm[c] - 1.5:
        lo -= 1
    while hi < len(sm) - 1 and sm[hi + 1] >= sm[c] - 1.5:
        hi += 1
    t0, t1 = lo * 0.5, (hi + 1) * 0.5
    if t1 - t0 < min_len:
        t1 = min(len(y) / sr, t0 + min_len)
    bars = beat_times[::4]
    t0 = bars[np.argmin(np.abs(bars - t0))]
    t1 = bars[np.argmin(np.abs(bars - t1))]
    return float(t0), float(t1)


def expression(vocals, notes):
    """CC11 swell values every 30 ms following the singer's loudness."""
    y, sr = audio.load_mono(vocals, sr=22050)
    hop = int(0.03 * sr)
    rms = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2)) for i in range(0, len(y) - hop, hop)])
    voiced = np.zeros(len(rms), bool)
    for s, e, _, _ in notes:
        voiced[int(s / 0.03):int(e / 0.03) + 1] = True
    ref = np.percentile(rms[voiced], 95) if voiced.any() else rms.max()
    x = np.clip(rms / (ref + 1e-9), 0, 1)
    x = np.convolve(x, np.ones(4) / 4, 'same')
    return [(i * 0.03, int(48 + 79 * v ** 0.7)) for i, v in enumerate(x)]


def render(notes, region, swell, center, sf2):
    import tinysoundfont
    syn = tinysoundfont.Synth(samplerate=SR, gain=-8)
    sfid = syn.sfload(sf2)
    layers = [('s', i, l) for i, l in enumerate(SIMPLE)] + [('f', i, l) for i, l in enumerate(FULL)]
    chans = {}
    for ch, (reg, i, (bank, preset, _, _)) in enumerate(c for c in layers):
        ch = ch if ch < 9 else ch + 1  # skip the GM drum channel
        syn.program_select(ch, sfid, bank, preset)
        syn.control_change(ch, 7, 112)
        chans[(reg, i)] = ch
    shift = 12 * round((center - np.median([n[2] for n in notes])) / 12)
    ev = []
    for s, e, p, _ in notes:
        reg, stack = ('f', FULL) if region[0] <= s < region[1] else ('s', SIMPLE)
        for i, (_, _, off, vs) in enumerate(stack):
            key = p + shift + off
            if 21 <= key <= 108:
                ev.append((s, 2, 'on', chans[(reg, i)], key, int(100 * vs)))
                ev.append((max(s + 0.05, e - 0.01), 0, 'off', chans[(reg, i)], key, 0))
    last = -1
    for t, v in swell:
        if abs(v - last) >= 2:
            for ch in chans.values():
                ev.append((t, 1, 'cc', ch, 11, v))
            last = v
    ev.sort(key=lambda e: (e[0], e[1]))
    chunks, t = [], 0.0
    for et, _, kind, ch, key, val in ev:
        n = int(round((et - t) * SR))
        if n > 0:
            chunks.append(np.frombuffer(syn.generate(n), np.float32).copy())
            t += n / SR
        if kind == 'on':
            syn.noteon(ch, key, val)
        elif kind == 'off':
            syn.noteoff(ch, key)
        else:
            syn.control_change(ch, key, val)
    syn.notes_off()
    chunks.append(np.frombuffer(syn.generate(int(2 * SR)), np.float32).copy())
    return np.concatenate(chunks).reshape(-1, 2).T, shift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('out')
    ap.add_argument('--intense', nargs=2, type=float, metavar=('START', 'END'))
    ap.add_argument('--center', type=float, default=69, help='target median MIDI pitch of the organ line')
    ap.add_argument('--organ-db', type=float, default=1.0, help='organ level relative to the original vocal')
    ap.add_argument('--sf2', default=organ.SF2)
    a = ap.parse_args()

    h = hashlib.sha1(open(a.song, 'rb').read()).hexdigest()[:12]
    cache = os.path.join(organ.CACHE, h)
    os.makedirs(cache, exist_ok=True)
    stems = organ.separate(a.song, cache)

    d, sr = audio.load_mono(stems['drums'], sr=22050)
    env, fps = audio.onset_env(d, sr)
    bpm, phase = audio.tempo_and_phase(env, fps)
    beat_times = np.arange(phase, len(d) / sr, 60 / bpm)

    f0 = organ.melody_from_f0(stems['vocals'], os.path.join(cache, 'vocals_f0.json'))
    bp = organ.transcribe(stems['vocals'], os.path.join(cache, 'vocals.json'), 80, 1100, 0.5, 0.3, 110)
    fill = [n for n in bp if not any(m[0] < n[1] and n[0] < m[1] for m in f0)]
    notes = organ.monophonic(f0 + fill, 0.08)

    region = tuple(a.intense) if a.intense else intense_region(a.song, beat_times)
    organ_x, shift = render(notes, region, expression(stems['vocals'], notes), a.center, a.sf2)
    organ_x = organ.cathedral(organ_x, rt60=1.8, wet=0.25, hp=250.0)

    backing = sum(organ.load_stereo(stems[n]) for n in ('drums', 'bass', 'other'))
    vocal = organ.load_stereo(stems['vocals'])
    n = min(backing.shape[1], organ_x.shape[1], vocal.shape[1])
    voiced = np.zeros(n, bool)
    for s, e, _, _ in notes:
        voiced[int(s * SR):min(n, int(e * SR))] = True
    rms = lambda x: np.sqrt(np.mean(x[:, :n][:, voiced] ** 2)) + 1e-9
    g = rms(vocal) / rms(organ_x) * 10 ** (a.organ_db / 20)
    mix = backing[:, :n] + organ_x[:, :n] * g
    peak = np.max(np.abs(mix))
    if peak > 0.95:  # gentle limiter only where needed
        mix = np.tanh(mix / peak * 1.6) / np.tanh(1.6) * 0.95
    organ.write_wav(a.out, mix)
    print('bpm %.1f  vocal notes %d  octave shift %+d  all-stops section %.1f-%.1f s  -> %s'
          % (bpm, len(notes), shift, region[0], region[1], a.out))


if __name__ == '__main__':
    main()
