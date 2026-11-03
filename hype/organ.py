"""Reimagine a pop song on a sampled pipe organ.

    python3 organ.py <song> <out.wav> [--start SEC --dur SEC] [--sf2 PATH]

1. Demucs (htdemucs) separates the song into drums / bass / other / vocals.
2. Basic Pitch transcribes the vocal stem (the melody) and the bass stem to notes.
3. Chords come from the harmony stems (other + bass): CQT chroma per half-bar,
   limited to the song's key and smoothed with a Viterbi pass.
4. An organ arrangement on the song's beat grid: the melody on a solo stop above
   the chords, full-organ chords that pulse in 8ths when the drums are driving and
   hold when they're not, a 16' pedal line from the transcribed bass, and a swell
   pedal that follows the original's loudness.
5. Rendered with the GeneralUser GS sampled pipe organs, into a cathedral reverb.

Stems and transcriptions are cached next to the SoundFont (media/organ_cache/),
so re-renders with different settings are fast.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio  # noqa: E402

SR = 44100
SF2 = os.path.join(HERE, 'media', 'raw', 'sf2', 'GeneralUser-GS.sf2')
CACHE = os.path.join(HERE, 'media', 'organ_cache')
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# channel: (bank, preset, channel volume)
MELODY, CHORDS, PEDAL, MEL_LO = 0, 1, 2, 3
VOICES = {MELODY: (8, 19, 118), CHORDS: (0, 19, 92), PEDAL: (0, 19, 112), MEL_LO: (0, 19, 70)}


def load_stereo(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '2', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy()


def write_wav(path, x, sr=SR):
    import soundfile as sf
    sf.write(path, np.asarray(x).T, sr, subtype='PCM_16')


# ---------------------------------------------------------------- 1. separation

def separate(song, cache):
    stems = {n: os.path.join(cache, n + '.wav') for n in ('drums', 'bass', 'other', 'vocals')}
    if all(os.path.exists(p) for p in stems.values()):
        return stems
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    torch.set_num_threads(os.cpu_count() or 4)
    model = get_model('htdemucs')
    model.eval()
    wav = torch.from_numpy(load_stereo(song, model.samplerate))
    ref = wav.mean(0)
    m, s = ref.mean(), ref.std()
    with torch.no_grad():
        out = apply_model(model, ((wav - m) / s)[None], device='cpu', shifts=1, split=True, overlap=0.25,
                          progress=False)[0]
    out = out * s + m
    for i, n in enumerate(model.sources):
        write_wav(stems[n], out[i].numpy(), model.samplerate)
    return stems


# ---------------------------------------------------------------- 2. transcription

def transcribe(path, cache_json, fmin, fmax, onset, frame, minlen):
    if os.path.exists(cache_json):
        return [tuple(n) for n in json.load(open(cache_json))]
    import logging
    logging.disable(logging.WARNING)
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import Model, predict
    _, _, notes = predict(path, Model(ICASSP_2022_MODEL_PATH), onset_threshold=onset, frame_threshold=frame,
                          minimum_note_length=minlen, minimum_frequency=fmin, maximum_frequency=fmax,
                          melodia_trick=True)
    out = sorted((float(s), float(e), int(p), float(a)) for s, e, p, a, _ in notes)
    json.dump(out, open(cache_json, 'w'))
    return out


def monophonic(notes, min_dur=0.09):
    """One note at a time: on overlaps keep the louder note, trimming the earlier one."""
    out = []
    for s, e, p, a in sorted(notes, key=lambda n: (n[0], -n[3])):
        if e - s < min_dur:
            continue
        if out and s < out[-1][1]:
            ps, pe, pp, pa = out[-1]
            if s - ps <= 0.06:
                if a > pa:
                    out[-1] = (s, e, p, a)
                continue
            if a >= pa * 0.8:
                out[-1] = (ps, s, pp, pa)
                out.append((s, e, p, a))
            continue
        out.append((s, e, p, a))
    # fold octave glitches back toward the local median pitch
    ps = np.array([n[2] for n in out], float)
    fixed = []
    for i, (s, e, p, a) in enumerate(out):
        med = np.median(ps[max(0, i - 6):i + 7])
        while p - med > 7:
            p -= 12
        while med - p > 7:
            p += 12
        fixed.append((s, e, p, a))
    return fixed


# ---------------------------------------------------------------- 3. chords

TEMPL = []
for _r in range(12):
    for _q, _iv in (('maj', (0, 4, 7)), ('min', (0, 3, 7))):
        _t = np.zeros(12)
        _t[[(_r + i) % 12 for i in _iv]] = [1.0, 0.8, 0.9]
        TEMPL.append((_r, _q, _t / np.linalg.norm(_t)))
MAJ_PROF = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN_PROF = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_of(chroma_total):
    return max(((np.corrcoef(np.roll(p, k), chroma_total)[0, 1], k, mode) for k in range(12)
                for p, mode in ((MAJ_PROF, 'maj'), (MIN_PROF, 'min'))))[1:]


def diatonic(tonic, mode):
    if mode == 'maj':
        degs = [(0, 'maj'), (2, 'min'), (4, 'min'), (5, 'maj'), (7, 'maj'), (9, 'min')]
    else:
        degs = [(0, 'min'), (3, 'maj'), (5, 'min'), (7, 'min'), (7, 'maj'), (8, 'maj'), (10, 'maj')]
    return {((tonic + d) % 12, q) for d, q in degs}


def chords(stems, beat_times, beats_per=2):
    import librosa
    y = sum(librosa.load(stems[n], sr=22050, mono=True)[0] for n in ('other', 'bass'))
    hop = 512
    C = librosa.feature.chroma_cqt(y=y, sr=22050, hop_length=hop)
    ft = librosa.frames_to_time(np.arange(C.shape[1]), sr=22050, hop_length=hop)
    tonic, mode = key_of(C.sum(1))
    cand = [j for j, (r, q, _) in enumerate(TEMPL) if (r, q) in diatonic(tonic, mode)]
    bounds = beat_times[::beats_per]
    seg = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        m = (ft >= a) & (ft < b)
        c = C[:, m].mean(1) if m.any() else np.zeros(12)
        seg.append(c / (np.linalg.norm(c) + 1e-9))
    # Viterbi: emissions = template similarity, sticky transitions
    E = np.array([[float(c @ TEMPL[j][2]) for j in cand] for c in seg]) * 8
    stay, n = math.log(0.7), len(cand)
    move = math.log(0.3 / max(1, n - 1))
    V = E[0].copy()
    back = []
    for t in range(1, len(E)):
        trans = V[:, None] + np.where(np.eye(n, dtype=bool), stay, move)
        back.append(trans.argmax(0))
        V = trans.max(0) + E[t]
    path = [int(V.argmax())]
    for bk in reversed(back):
        path.append(int(bk[path[-1]]))
    path.reverse()
    return [(bounds[i], bounds[i + 1], TEMPL[cand[j]][0], TEMPL[cand[j]][1]) for i, j in enumerate(path)], (tonic, mode)


# ---------------------------------------------------------------- 4. arrangement

def voicing(root, q, prev):
    """Close triad (+ doubled root) in F3..A4, choosing the inversion nearest the last chord."""
    pcs = [root % 12, (root + (4 if q == 'maj' else 3)) % 12, (root + 7) % 12]
    options = []
    for base in range(53, 66):
        notes = sorted({base + ((pc - base) % 12) for pc in pcs})
        if notes[-1] <= 72:
            options.append(notes)
    if prev is None:
        return min(options, key=lambda v: abs(np.mean(v) - 61))
    return min(options, key=lambda v: sum(min(abs(a - b) for b in prev) for a in v))


def arrange(notes_mel, notes_bass, chord_segs, beat_times, drums_db, loud_db, step):
    ev = []  # (time, order, kind, chan, key, val); order: 0 noteoff, 1 cc, 2 noteon

    def note(ch, t0, t1, key, vel):
        if t1 - t0 > 0.02:
            ev.append((t0, 2, 'on', ch, int(key), int(vel)))
            ev.append((t1, 0, 'off', ch, int(key), 0))

    beat = float(np.median(np.diff(beat_times)))
    q = beat / 2  # 8th

    def snap(t, grid):
        k = round((t - beat_times[0]) / grid)
        return beat_times[0] + k * grid

    # melody: solo stop, centered around D5, doubled softly an octave below
    if notes_mel:
        med = np.median([n[2] for n in notes_mel])
        shift = 12 * round((74 - med) / 12)
        for s, e, p, a in notes_mel:
            s2, e2 = snap(s, step), max(snap(e, step), snap(s, step) + step)
            note(MELODY, s2, e2 - 0.01, p + shift, 112)
            note(MEL_LO, s2, e2 - 0.01, p + shift - 12, 85)

    # chords: pulse 8ths when the drums drive, otherwise hold
    thr = np.percentile(drums_db, 60)
    prev = None
    for t0, t1, root, qq in chord_segs:
        v = voicing(root, qq, prev)
        prev = v
        bi = int(np.searchsorted(beat_times, t0))
        driving = drums_db[min(bi, len(drums_db) - 1)] >= thr
        if driving:
            t = t0
            while t < t1 - 0.01:
                for k in v:
                    note(CHORDS, t, t + q * 0.82, k, 96)
                t += q
        else:
            for k in v:
                note(CHORDS, t0, t1 - 0.02, k, 90)

    # pedal: transcribed bass in the 16' octave; fall back to chord roots where the bass is silent
    covered = np.zeros(len(chord_segs), bool)
    for s, e, p, a in notes_bass:
        while p > 43:
            p -= 12
        while p < 24:
            p += 12
        s2 = snap(s, q)
        e2 = max(snap(e, q), s2 + q)
        note(PEDAL, s2, e2 - 0.01, p, 110)
        for i, (t0, t1, _, _) in enumerate(chord_segs):
            if t0 <= s2 < t1:
                covered[i] = True
    for i, (t0, t1, root, _) in enumerate(chord_segs):
        if not covered[i]:
            p = 24 + (root % 12)
            p += 12 if p < 28 else 0
            note(PEDAL, t0, t1 - 0.02, p, 104)

    # swell pedal (CC11) per beat, following the original's loudness
    lo, hi = np.percentile(loud_db, 10), np.percentile(loud_db, 97)
    for i, t in enumerate(beat_times[:len(loud_db)]):
        x = np.clip((loud_db[i] - lo) / max(1e-6, hi - lo), 0, 1)
        val = int(62 + 65 * x ** 0.8)
        for ch in VOICES:
            ev.append((t, 1, 'cc', ch, 11, val))
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev


# ---------------------------------------------------------------- 5. render

def render(ev, t_start, t_end, sf2):
    import tinysoundfont
    syn = tinysoundfont.Synth(samplerate=SR, gain=-6)
    sfid = syn.sfload(sf2)
    for ch, (bank, preset, vol) in VOICES.items():
        syn.program_select(ch, sfid, bank, preset)
        syn.control_change(ch, 7, vol)
        syn.control_change(ch, 91, 0)
    chunks, t = [], t_start
    held = set()
    for et, _, kind, ch, key, val in ev:
        if et < t_start:
            if kind == 'cc':
                syn.control_change(ch, key, val)
            continue
        if et > t_end:
            break
        n = int(round((et - t) * SR))
        if n > 0:
            chunks.append(np.frombuffer(syn.generate(n), np.float32).copy())
            t += n / SR
        if kind == 'on':
            syn.noteon(ch, key, val)
            held.add((ch, key))
        elif kind == 'off':
            syn.noteoff(ch, key)
            held.discard((ch, key))
        else:
            syn.control_change(ch, key, val)
    for ch, key in held:
        syn.noteoff(ch, key)
    chunks.append(np.frombuffer(syn.generate(int(1.5 * SR)), np.float32).copy())
    return np.concatenate(chunks).reshape(-1, 2).T


def cathedral(x, rt60=3.2, wet=0.42):
    n = int(rt60 * 1.2 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    out = np.zeros_like(x)
    nfft = 1 << int(math.ceil(math.log2(x.shape[1] + n)))
    fr = np.fft.rfftfreq(n, 1 / SR)
    for ch in range(2):
        ir = rng.normal(0, 1, n) * np.exp(-6.91 * t / rt60)
        spec = np.fft.rfft(ir) / (1 + (fr / 4000) ** 2)
        ir = np.fft.irfft(spec, n)
        ir[:int(0.03 * SR)] = 0
        for d, g in ((0.011, 0.5), (0.019, 0.35), (0.027, 0.3)):  # early reflections
            ir[int(d * SR)] += g * (1 if ch else -1)
        ir /= np.sqrt(np.sum(ir ** 2))
        w = np.fft.irfft(np.fft.rfft(x[ch], nfft) * np.fft.rfft(ir, nfft), nfft)[:x.shape[1]]
        out[ch] = x[ch] * (1 - wet) + w * wet * 2.2
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('out')
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--dur', type=float)
    ap.add_argument('--sf2', default=SF2)
    ap.add_argument('--no-reverb', action='store_true')
    a = ap.parse_args()

    h = hashlib.sha1(open(a.song, 'rb').read()).hexdigest()[:12]
    cache = os.path.join(CACHE, h)
    os.makedirs(cache, exist_ok=True)
    stems = separate(a.song, cache)
    print('stems ready', flush=True)

    d, sr = audio.load_mono(stems['drums'], sr=22050)
    env, fps = audio.onset_env(d, sr)
    bpm, phase = audio.tempo_and_phase(env, fps)
    full = len(d) / sr
    beat = 60 / bpm
    beat_times = np.arange(phase, full, beat)
    step = beat / 4

    mel = monophonic(transcribe(stems['vocals'], os.path.join(cache, 'vocals.json'), 80, 1100, 0.5, 0.3, 110))
    bas = monophonic(transcribe(stems['bass'], os.path.join(cache, 'bass.json'), 30, 330, 0.45, 0.3, 120), 0.12)
    segs, (tonic, mode) = chords(stems, beat_times)

    def beat_db(path):
        y, s2 = audio.load_mono(path, sr=22050)
        hop = int(beat * s2)
        return np.array([20 * np.log10(np.sqrt(np.mean(y[int(t * s2):int(t * s2) + hop] ** 2)) + 1e-9)
                         for t in beat_times])

    drums_db = beat_db(stems['drums'])
    mix_db = beat_db(a.song)
    ev = arrange(mel, bas, segs, beat_times, drums_db, mix_db, step)
    t0 = a.start
    t1 = a.start + a.dur if a.dur else full
    x = render(ev, t0, t1, a.sf2)
    if not a.no_reverb:
        x = cathedral(x)
    x = np.tanh(x / (np.max(np.abs(x)) + 1e-9) * 1.25)
    x = x / np.max(np.abs(x)) * 0.89
    write_wav(a.out, x)
    print('bpm %.1f  key %s %s  melody notes %d  bass notes %d  chord segments %d  -> %s'
          % (bpm, NAMES[tonic], mode, len(mel), len(bas), len(segs), a.out))


if __name__ == '__main__':
    main()
