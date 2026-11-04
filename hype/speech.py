"""Find a spoken line in a recording and get its exact timing (for speeches and sound bites).

    python3 speech.py <audio or video> [--start S] [--dur D] [--find "these are the boys of pointe du hoc"]

Transcribes with faster-whisper (base.en, CPU) with word timestamps and prints each
word with its time in the file. With --find, prints the best-matching span's start and
end (seconds in the file), so a clip can be cut tight on the line:
    ffmpeg -ss <start-0.2> -t <end-start+0.4> -i <file> -vn -c:a aac -b:a 192k media/<key>.m4a
"""
import argparse
import difflib
import os
import re
import subprocess
import tempfile


def words_of(path, start=0.0, dur=None, model='base.en'):
    from faster_whisper import WhisperModel
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'a.wav')
        cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-i', path]
        if dur:
            cmd += ['-t', str(dur)]
        subprocess.run(cmd + ['-vn', '-ac', '1', '-ar', '16000', wav], check=True)
        import soundfile as sf
        audio, _ = sf.read(wav, dtype='float32')
        m = WhisperModel(model, device='cpu', compute_type='int8')
        segs, _ = m.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=5)
        out = []
        for s in segs:
            for w in s.words or []:
                out.append((w.start + start, w.end + start, w.word.strip()))
        return out


def norm(t):
    return re.sub(r'[^a-z0-9 ]', '', t.lower())


def find(words, phrase):
    target = norm(phrase).split()
    toks = [norm(w) for _, _, w in words]
    best = (0.0, None)
    n = len(target)
    for i in range(len(toks)):
        for L in range(max(1, n - 2), n + 3):
            cand = toks[i:i + L]
            r = difflib.SequenceMatcher(None, ' '.join(cand), ' '.join(target)).ratio()
            if r > best[0]:
                best = (r, (i, i + L))
    if best[1] is None:
        return None
    i, j = best[1]
    j = min(j, len(words))
    return best[0], words[i][0], words[j - 1][1], ' '.join(w for _, _, w in words[i:j])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--dur', type=float)
    ap.add_argument('--find')
    ap.add_argument('--model', default='base.en')
    a = ap.parse_args()
    ws = words_of(a.file, a.start, a.dur, a.model)
    for s, e, w in ws:
        print('%8.2f %8.2f  %s' % (s, e, w))
    if a.find:
        r = find(ws, a.find)
        if r:
            print('\nbest match (%.0f%%): %.2f - %.2f s  "%s"' % (100 * r[0], r[1], r[2], r[3]))
        else:
            print('\nno match')


if __name__ == '__main__':
    main()
