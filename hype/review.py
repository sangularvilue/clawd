"""Self-review of a rendered edit, the pass every video gets before Will sees it (see PLAYBOOK.md).

    python3 review.py edits/weekly/<edit>.py out/<render>.mp4 [--sheets DIR] [--speech] [--model small.en]

Prints, and writes under DIR (default out/review_<edit>/):
  - shots_NN.png   one labeled frame per shot (beat, length, source), 6 across: look at every one
  - shot list      beat, seconds, length, source, source resolution; flags for
                     LOWRES   a color shot whose source (after its crop) is under 700 px wide
                     REPEAT   the same source used more than once (strobe recaps excepted, they are listed)
                     SEEN     a clip that an earlier edit in edits/ already used: Will has watched it before
                     LONG     a shot over 5 s;  SLOT  a placeholder card that still needs footage
  - loudness       integrated LUFS and true peak of the whole mix, and LUFS per section between the marks
  - --speech       transcribes the final mix with whisper and prints the words it could hear, so the lines can
                   be checked against the script (a word the model can't pull out of the mix, Will can't either),
                   and how much of the film is talk (speech seconds / length)
"""
import argparse
import glob
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    spec = importlib.util.spec_from_file_location('edit', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def seen_before(edit_path):
    """Base names of every clip or photo used by the other edit files under edits/."""
    seen = {}
    me = os.path.abspath(edit_path)
    for f in sorted(glob.glob(os.path.join(HERE, 'edits', '**', '*.py'), recursive=True)):
        if os.path.abspath(f) == me:
            continue
        try:
            m = load(f)
        except Exception:
            continue
        for s in getattr(m, 'SEQ', []):
            src = s.get('clip') or s.get('photo')
            if src:
                seen.setdefault(os.path.splitext(os.path.basename(src))[0], os.path.basename(f))
    return seen


def probe(path):
    try:
        o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                            '-of', 'json', path], capture_output=True, text=True, check=True).stdout
        s = json.loads(o)['streams'][0]
        return s['width'], s['height']
    except Exception:
        return None


def lufs(path, t0=None, t1=None):
    cmd = ['ffmpeg', '-hide_banner', '-nostats']
    if t0 is not None:
        cmd += ['-ss', '%.3f' % t0, '-t', '%.3f' % (t1 - t0)]
    cmd += ['-i', path, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    tail = err[err.rfind('Summary:'):]
    val = lambda key: next((ln.split(':')[1].split()[0] for ln in tail.splitlines() if ln.strip().startswith(key)), '?')
    return val('I:'), val('Peak:')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edit')
    ap.add_argument('render')
    ap.add_argument('--sheets')
    ap.add_argument('--speech', action='store_true')
    ap.add_argument('--model', default='small.en')
    ap.add_argument('--color-from', type=float, help='beat from which shots are in color (default: the edit\'s DROP)')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    E = load(a.edit)
    beat = 60 / E.BPM
    name = os.path.splitext(os.path.basename(a.edit))[0]
    out = a.sheets or os.path.join(HERE, 'out', 'review_' + name)
    os.makedirs(out, exist_ok=True)
    color_from = a.color_from if a.color_from is not None else getattr(E, 'DROP', 0)

    earlier = seen_before(a.edit)
    rows, b, seen = [], 0.0, {}
    for i, s in enumerate(E.SEQ):
        src = s.get('clip') or s.get('photo')
        key = os.path.splitext(os.path.basename(src))[0] if src else 'SLOT ' + s.get('p', {}).get('desc', s.get('shot', '?'))
        flags = []
        res = probe(src) if src else None
        if not src:
            flags.append('SLOT')
        if res:
            w = res[0] * (s['crop'][2] if s.get('crop') else 1.0)
            if w < 700 and b >= color_from and s.get('fx', {}).get('sat', 1) > 0:
                flags.append('LOWRES')
        if s['beats'] * beat > 5.0:
            flags.append('LONG')
        if src and key in earlier:
            flags.append('SEEN(%s)' % earlier[key])
        if src:
            seen.setdefault(key, []).append(b)
        rows.append(dict(i=i, beat=b, len=s['beats'], key=key, res=res, flags=flags))
        b += s['beats']
    for r in rows:
        if len(seen.get(r['key'], [])) > 1:
            r['flags'].append('REPEAT x%d' % len(seen[r['key']]))

    print('%-4s %7s %7s %5s  %-34s %-10s %s' % ('#', 'beat', 'sec', 'len', 'source', 'res', 'flags'))
    for r in rows:
        print('%-4d %7.2f %7.2f %5.2f  %-34s %-10s %s' % (r['i'], r['beat'], r['beat'] * beat, r['len'], r['key'][:34],
                                                           '%dx%d' % r['res'] if r['res'] else '-', ' '.join(r['flags'])))
    print('total %.1f beats = %.1f s, %d shots, median shot %.2f s' % (
        b, b * beat, len(rows), sorted(r['len'] for r in rows)[len(rows) // 2] * beat))

    # one frame per shot, a third of the way in
    tw, th, per = 320, 180, 6
    thumbs = []
    for r in rows:
        t = (r['beat'] + min(r['len'] * 0.35, 1.2)) * beat
        fn = os.path.join(out, '_f.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.3f' % t, '-i', a.render, '-frames:v', '1',
                        '-vf', 'scale=%d:%d' % (tw, th), fn], check=True)
        im = Image.open(fn).convert('RGB')
        d = ImageDraw.Draw(im)
        label = '%d  b%.1f  %.1fs  %s' % (r['i'], r['beat'], r['len'] * beat, r['key'][:22])
        d.rectangle([0, th - 14, tw, th], fill=(0, 0, 0))
        d.text((3, th - 13), label, fill=(255, 255, 80) if r['flags'] else (255, 255, 255))
        thumbs.append(im)
    os.remove(os.path.join(out, '_f.png'))
    rows_per = 6
    for n in range(0, len(thumbs), per * rows_per):
        chunk = thumbs[n:n + per * rows_per]
        sheet = Image.new('RGB', (tw * per, th * ((len(chunk) + per - 1) // per)))
        for j, im in enumerate(chunk):
            sheet.paste(im, ((j % per) * tw, (j // per) * th))
        fn = os.path.join(out, 'shots_%02d.png' % (n // (per * rows_per)))
        sheet.save(fn)
        print('sheet', fn)

    i_all, pk = lufs(a.render)
    print('loudness: %s LUFS integrated, true peak %s dBFS' % (i_all, pk))
    marks = [(k, getattr(E, k)) for k in ('MUSIC_IN', 'DRUMS', 'DROP', 'LIFT', 'CHORD', 'RELEASE', 'END_AT') if hasattr(E, k)]
    edges = [('START', 0.0)] + sorted(marks, key=lambda m: m[1]) + [('END', b)]
    for (k0, x0), (k1, x1) in zip(edges, edges[1:]):
        if x1 > x0:
            print('  %-9s -> %-9s beats %6.1f-%6.1f  %s LUFS' % (k0, k1, x0, x1, lufs(a.render, x0 * beat, x1 * beat)[0]))

    if a.speech:
        sp = subprocess.run([sys.executable, os.path.join(HERE, 'speech.py'), a.render, '--model', a.model],
                            capture_output=True, text=True)
        words = []
        for ln in sp.stdout.splitlines():
            p = ln.split()
            if len(p) >= 3:
                try:
                    words.append((float(p[0]), float(p[1]), ' '.join(p[2:])))
                except ValueError:
                    pass
        print('speech heard in the final mix (seconds, beat):')
        line, t0 = [], None
        for w0, w1, w in words:
            if t0 is None:
                t0 = w0
            line.append(w)
            if w.rstrip().endswith(('.', '?', '!', ':')) or len(line) > 14:
                print('  %6.2f s  b%6.1f  %s' % (t0, t0 / beat, ' '.join(line)))
                line, t0 = [], None
        if line:
            print('  %6.2f s  b%6.1f  %s' % (t0, t0 / beat, ' '.join(line)))
        talk, last = 0.0, None
        for w0, w1, _ in words:  # runs of words, pauses under 0.35 s counted as talk
            talk += (w1 - w0) + (w0 - last if last is not None and w0 - last < 0.35 else 0.0)
            last = w1
        print('speech: %.1f s of %.1f s (%.0f%%)' % (talk, b * beat, 100 * talk / (b * beat)))


if __name__ == '__main__':
    main()
