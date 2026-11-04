"""Render an edit list to MP4. Every duration is in beats, so the same edit
re-times itself to whatever song and tempo it is given.

    python3 render.py <edit module> [--song FILE --start SEC --bpm N] [--hd] [--out FILE]
"""
import argparse
import importlib.util
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio  # noqa: E402
import fx  # noqa: E402
import shots  # noqa: E402


class Clip:
    """Frames from a video file: cover-fit, optional speed ramp, held on the last frame."""

    def __init__(self, path, start, dur, W, H, fps, speed=1.0, crop=None):
        vf = []
        if crop:  # (x, y, w, h) as fractions of the source frame
            vf.append('crop=iw*%f:ih*%f:iw*%f:ih*%f' % (crop[2], crop[3], crop[0], crop[1]))
        vf += ['setpts=PTS/%f' % speed, 'fps=%d' % fps,
               'scale=%d:%d:force_original_aspect_ratio=increase' % (W, H), 'crop=%d:%d' % (W, H)]
        cmd = ['ffmpeg', '-v', 'error', '-ss', str(start), '-i', path, '-t', str(dur * speed + 0.5),
               '-an', '-vf', ','.join(vf), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.W, self.H, self.last = W, H, None

    def next(self):
        b = self.p.stdout.read(self.W * self.H * 3)
        if len(b) == self.W * self.H * 3:
            self.last = np.frombuffer(b, np.uint8).reshape(self.H, self.W, 3).astype(np.float32)
        if self.last is None:
            self.last = np.zeros((self.H, self.W, 3), np.float32)
        return self.last.copy()

    def close(self):
        self.p.kill()


class Photo:
    """A still with a slow push-in. fit='cover' fills the frame; fit='contain' shows the whole
    image over a blurred, darkened copy of itself (for portrait photos that must stay readable)."""

    def __init__(self, path, W, H, zoom=(1.0, 1.12), center=(0.5, 0.5), fit='cover'):
        im = Image.open(path).convert('RGB')
        zm = max(zoom)
        self.W, self.H, self.zoom, self.c, self.zm, self.fit = W, H, zoom, center, zm, fit
        if fit == 'contain':
            s = max(W / im.width, H / im.height) * 1.1
            bg = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.BILINEAR)
            x0, y0 = (bg.width - W) // 2, (bg.height - H) // 2
            bg = bg.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(H / 40))
            self.bg = np.asarray(bg, np.float32) * 0.45
            k = int(H * 0.94 // im.height)
            if k >= 2:  # tiny web graphics: whole-pixel upscale first so labels stay crisp
                im = im.resize((im.width * k, im.height * k), Image.NEAREST)
            self.fg = im
            return
        sc = max(W * zm / im.width, H * zm / im.height)
        self.im = im.resize((math.ceil(im.width * sc), math.ceil(im.height * sc)), Image.LANCZOS)

    def at(self, k):
        z = self.zoom[0] + (self.zoom[1] - self.zoom[0]) * k
        if self.fit == 'contain':
            f = self.bg.copy()
            base = min(self.W * 0.94 / self.fg.width, self.H * 0.94 / self.fg.height)
            w, h = self.fg.width * base * z, self.fg.height * base * z
            fg = np.asarray(self.fg.resize((int(w), int(h)), Image.BILINEAR), np.float32)
            x = int(self.W / 2 - w / 2)
            y = int(self.H * 0.03 - (h - self.H * 0.94) * self.c[1])
            rgba = np.concatenate([fg, np.full(fg.shape[:2] + (1,), 255, np.float32)], 2)
            fx.paste(f, rgba, x, y)
            return f
        cw, ch = self.W * self.zm / z, self.H * self.zm / z
        x0 = min(max(0, self.c[0] * self.im.width - cw / 2), self.im.width - cw)
        y0 = min(max(0, self.c[1] * self.im.height - ch / 2), self.im.height - ch)
        return np.asarray(self.im.resize((self.W, self.H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)), np.float32)


def load_edit(path):
    spec = importlib.util.spec_from_file_location('edit', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edit')
    ap.add_argument('--song')
    ap.add_argument('--start', type=float, default=0.0, help='song time of beat 0 (a downbeat)')
    ap.add_argument('--bpm', type=float)
    ap.add_argument('--hd', action='store_true', help='1920x1080 60fps (default 1280x720 30fps draft)')
    ap.add_argument('--preview', action='store_true', help='640x360 30fps, fastest')
    ap.add_argument('--placeholder', action='store_true', help='placeholder drums even if the edit names a song')
    ap.add_argument('--vertical', action='store_true', help='9:16')
    ap.add_argument('--out')
    ap.add_argument('--only', help='render a beat range a:b for quick looks')
    a = ap.parse_args()

    E = load_edit(a.edit)
    W, H, fps = (1920, 1080, 60) if a.hd else (640, 360, 30) if a.preview else (1280, 720, 30)
    if a.vertical:
        W, H = H, W
    if not a.song and getattr(E, 'SONG', None) and not a.placeholder:
        a.song = os.path.join(HERE, E.SONG)
        a.start = getattr(E, 'SONG_START', 0.0)
    bpm = a.bpm or getattr(E, 'BPM', 160)
    beat = 60 / bpm
    seq = E.SEQ
    starts, b = [], 0.0
    for s in seq:
        starts.append(b)
        b += s['beats']
    total_beats = b
    b0, b1 = 0.0, total_beats
    if a.only:
        b0, b1 = (float(v) for v in a.only.split(':'))
    dur = (b1 - b0) * beat
    out = a.out or os.path.join(HERE, 'out', os.path.splitext(os.path.basename(a.edit))[0] + '.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    wav = out + '.wav'
    # MUSIC_IN (beats): the song comes in at this beat of the edit (SONG_START is the song time
    # of that beat); before it the edit is silent apart from voiceovers, e.g. a speech pre-roll
    music_in = getattr(E, 'MUSIC_IN', 0.0) if a.song else 0.0
    if a.song:
        pre = max(0.0, music_in - b0) * beat
        ss = a.start + max(0.0, b0 - music_in) * beat
        af = 'afade=t=out:st=%f:d=0.6' % max(0, dur - pre - 0.6)
        if pre > 0:
            af += ',adelay=%d|%d' % (int(pre * 1000), int(pre * 1000))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(ss), '-i', a.song, '-t', str(max(0.1, dur - pre)),
                        '-af', af + ',apad', '-t', str(dur), '-ar', '44100', '-ac', '2', wav], check=True)
    else:
        braams = [(starts[i] - b0) * beat for i, s in enumerate(seq) if s.get('braam') and b0 <= starts[i] < b1]
        scr = [(starts[i] - b0 + s.get('screech')) * beat for i, s in enumerate(seq)
               if s.get('screech') is not None and b0 <= starts[i] < b1]
        audio.drums(bpm, dur, wav, braams=braams, screech=scr[0] if scr else None)

    # Song treatments (beats of the edit):
    #  LOFI = dict(until=<beat>, cutoff=2400, hp=160): the song plays muffled, near-mono, with tape wobble and faint
    #  vinyl crackle until that beat, then opens to full fidelity (the finale payoff).
    #  SILENCE = [(<beat>, <beat>), ...]: the song drops out completely (e.g. one beat of nothing before the finale).
    lofi = getattr(E, 'LOFI', None) if a.song else None
    silences = [((x0 - b0) * beat, (x1 - b0) * beat) for x0, x1 in getattr(E, 'SILENCE', [])] if a.song else []
    if lofi or silences:
        treated = out + '.lofi.wav'
        t_open = (lofi['until'] - b0) * beat if lofi else -1.0
        mute = '*'.join("(1-between(t,%f,%f))" % (x0, x1) for x0, x1 in silences) or '1'
        if lofi:
            fc = ('[0:a]asplit=2[c][l];'
                  '[l]highpass=f=%d,lowpass=f=%d,lowpass=f=%d,vibrato=f=0.6:d=0.02,'
                  'pan=stereo|c0=0.65*c0+0.35*c1|c1=0.35*c0+0.65*c1,volume=1.15[lf];'
                  'aevalsrc=\'0.25*gt(random(0)\\,0.9993)*(random(1)-0.5)|0.25*gt(random(2)\\,0.9993)*(random(3)-0.5)\':s=44100:d=%f,'
                  'highpass=f=1500[ck];'
                  'anoisesrc=d=%f:c=pink:a=0.004:r=44100,aformat=channel_layouts=stereo,highpass=f=2000[hs];'
                  '[lf][ck][hs]amix=inputs=3:normalize=0:duration=first,volume=\'if(lt(t,%f),1,0)*%s\':eval=frame[lo];'
                  '[c]volume=\'if(lt(t,%f),0,1)*%s\':eval=frame[cl];'
                  '[lo][cl]amix=inputs=2:normalize=0:duration=first[o]'
                  % (lofi.get('hp', 160), lofi.get('cutoff', 2400), lofi.get('cutoff', 2400), dur, dur,
                     t_open, mute, t_open, mute))
        else:
            fc = "[0:a]volume='%s':eval=frame[o]" % mute
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-filter_complex', fc, '-map', '[o]',
                        '-ar', '44100', '-ac', '2', treated], check=True)
        os.replace(treated, wav)

    # Voices over the music, which ducks underneath each one:
    #  - sound bites: clips marked voice=True play their own audio during their shot
    #    (voice_tail= lets the line finish past the cut, voice_gain=, duck=)
    #  - VOICEOVER: speeches and monologues that run across any number of shots, e.g.
    #    VOICEOVER = [dict(file='media/w1109_speech.m4a', at=0, src_in=12.3, dur=6.5, gain=1.4, duck=0.25)]
    #    (at in beats of the edit, src_in/dur in seconds of the source)
    items = []
    for i, s in enumerate(seq):
        if s.get('voice') and 'clip' in s and b0 <= starts[i] < b1:
            spd = s.get('speed', 1.0)
            items.append(dict(file=s['clip'], src_in=s.get('in', 0.0), t0=(starts[i] - b0) * beat,
                              dur=s['beats'] * beat + s.get('voice_tail', 0.0), speed=spd,
                              gain=s.get('voice_gain', 1.6), duck=s.get('duck', 0.3)))
    for v in getattr(E, 'VOICEOVER', []):
        t0 = (v['at'] - b0) * beat
        if t0 + v['dur'] > 0 and t0 < dur:
            items.append(dict(file=v['file'], src_in=v.get('src_in', 0.0) + max(0.0, -t0), t0=max(0.0, t0),
                              dur=v['dur'] - max(0.0, -t0), speed=v.get('speed', 1.0), gain=v.get('gain', 1.4),
                              duck=v.get('duck', 0.25)))
    if items:
        mixed = out + '.mix.wav'
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', wav]
        parts, duck = [], '1'
        for j, v in enumerate(items):
            spd = v['speed']
            cmd += ['-ss', str(v['src_in']), '-t', str(v['dur'] * spd), '-i', os.path.join(HERE, v['file'])]
            tempo = 'atempo=%f,' % spd if abs(spd - 1) > 1e-3 and 0.5 <= spd <= 2 else ''
            ms = int(v['t0'] * 1000)
            parts.append('[%d:a]%saresample=44100,aformat=channel_layouts=stereo,volume=%f,'
                         'afade=t=in:d=0.02,afade=t=out:st=%f:d=0.08,adelay=%d|%d[v%d]'
                         % (j + 1, tempo, v['gain'], max(0.0, v['dur'] - 0.08), ms, ms, j))
            duck = 'if(between(t,%f,%f),%f,%s)' % (v['t0'] - 0.08, v['t0'] + v['dur'] + 0.12, v['duck'], duck)
        song = "[0:a]volume='%s':eval=frame[s]" % duck
        mix = '[s]' + ''.join('[v%d]' % j for j in range(len(items)))
        fc = ';'.join([song] + parts) + ';' + mix + 'amix=inputs=%d:normalize=0:duration=first[out]' % (len(items) + 1)
        subprocess.run(cmd + ['-filter_complex', fc, '-map', '[out]', '-ar', '44100', '-ac', '2', mixed], check=True)
        os.replace(mixed, wav)

    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                            '-r', str(fps), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart',
                            out], stdin=subprocess.PIPE)
    post = fx.Post(W, H)
    base_fx = getattr(E, 'FX', {})  # edit-wide defaults, e.g. FX = dict(sat=0.0) for a black-and-white week
    src, src_i = None, -1
    nframes = int(round(dur * fps))
    for i in range(nframes):
        t = b0 * beat + i / fps
        bt = t / beat
        k = max(j for j in range(len(seq)) if starts[j] <= bt + 1e-9)
        s = seq[k]
        ts = t - starts[k] * beat
        sdur = s['beats'] * beat
        p = dict(s.get('p', {}), _beat=beat)
        if k != src_i:
            if src is not None and hasattr(src, 'close'):
                src.close()
            src_i = k
            if 'clip' in s:
                src = Clip(os.path.join(HERE, s['clip']), s.get('in', 0.0), sdur, W, H, fps, s.get('speed', 1.0),
                           s.get('crop'))
            elif 'photo' in s:
                src = Photo(os.path.join(HERE, s['photo']), W, H, s.get('zoom', (1.0, 1.15)), s.get('center', (0.5, 0.5)),
                            s.get('fit', 'cover'))
            else:
                src = None
        if 'clip' in s:
            f = src.next()
        elif 'photo' in s:
            f = src.at(ts / sdur)
        else:
            f = shots.SHOTS[s['shot']](ts, sdur, W, H, p)
        if s.get('dim'):
            f *= 1 - s['dim']
        texts = s.get('text', [])
        for j, tx in enumerate(texts):
            st = tx[0] * beat
            end = tx[5] * beat if len(tx) > 5 and tx[5] is not None else (
                texts[j + 1][0] * beat if j + 1 < len(texts) and not s.get('stack') else sdur)
            if st <= ts < end:
                size = tx[2] * H / 720
                fx.text(f, tx[1], size, cy=tx[3], style=tx[4] if len(tx) > 4 else 'clean', slam_t=ts - st)
        tb = (bt - math.floor(bt + 1e-9)) * beat
        every = s.get('fx', {}).get('every', 1)
        if every > 1:
            tb = ((bt - starts[k]) % every) * beat
        frame = post(f, tb, ts, dict(base_fx, **s.get('fx', {})))
        enc.stdin.write(frame.tobytes())
        if i % 30 == 0:
            print('\rframe %d/%d' % (i, nframes), end='', flush=True)
    enc.stdin.close()
    enc.wait()
    if src is not None and hasattr(src, 'close'):
        src.close()
    os.remove(wav)
    print('\n' + out)


if __name__ == '__main__':
    main()
