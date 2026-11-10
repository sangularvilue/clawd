"""Thin driver around MyPaint's own brush engine (libmypaint + MyPaint's
tiled surface): every mark in the painting is a real MyPaint brush stroke
made with the stock brush packs.  Run with /usr/bin/python3.12."""
import sys, math, os
os.environ["OMP_NUM_THREADS"] = "1"   # MyPaint's tile code is not thread-safe headless
sys.path.insert(0, '/usr/lib/mypaint')
import numpy as np
from lib import mypaintlib, tiledsurface, brush as _brush

BR = '/usr/share/mypaint-data/2.0/brushes/'
N = mypaintlib.TILE_SIZE
LUT = (np.clip((np.arange(32769) / 32768.0) ** (1 / 2.2) * 255 + 0.5, 0, 255)).astype(np.uint8)


class Canvas:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.s = tiledsurface.Surface()
        self._bi = {}
        self._b = {}
        self.nstrokes = 0
        self.off = (0.0, 0.0)
        self.ff = None            # timelapse recorder
        self.frame_every = 50
        self.hold = 1

    def _get(self, name):
        if name not in self._b:
            bi = _brush.BrushInfo()
            fixed = name.endswith('#fixed')
            bi.load_from_string(open(BR + name.split('#')[0] + '.myb').read())
            if fixed:
                # a firm, predictable point for drawing with the brush: size no longer swells with pressure
                for cname in ('radius_logarithmic', 'offset_by_random', 'radius_by_random', 'offset_by_speed'):
                    for inp in ('pressure', 'speed1', 'speed2', 'random', 'stroke', 'direction', 'tilt_declination', 'tilt_ascension', 'custom'):
                        try:
                            bi.set_points(cname, inp, [])
                        except Exception:
                            pass
                    if cname != 'radius_logarithmic':
                        bi.set_base_value(cname, 0.0)
            self._bi[name] = bi
            self._b[name] = (_brush.Brush(bi), bi.get_base_value('radius_logarithmic'),
                             bi.get_base_value('opaque'))
        return self._b[name], self._bi[name]

    def stroke(self, name, color, pts, r=None, op=None, p=0.8, taper=0.25, dt=0.012, step=None, **sets):
        """pts: list of (x, y) or (x, y, pressure).  r: radius in px.  The brush
        is lifted, moved, pressed, dragged and lifted again like a hand."""
        (b, r0, o0), bi = self._get(name)
        bi.set_color_rgb(tuple(float(min(max(c, 0), 1)) for c in color))
        bi.set_base_value('radius_logarithmic', math.log(r) if r else r0)
        bi.set_base_value('opaque', op if op is not None else o0)
        for k_, v in sets.items():
            bi.set_base_value(k_, v)
        P = np.array(pts, float)
        P[:, 0] += self.off[0]; P[:, 1] += self.off[1]
        if P.shape[1] == 2:
            n = len(P)
            t = np.linspace(0, 1, n)
            pr = p * np.minimum(1, np.minimum(t / max(taper, 1e-3) + 0.25, (1 - t) / max(taper, 1e-3) + 0.15))
            P = np.column_stack([P, pr])
        # resample so the engine sees a smooth hand motion
        if step is None:
            step = max((r or math.exp(r0)) * 0.5, 1.5)
        seg = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))
        cum = np.concatenate([[0], np.cumsum(seg)])
        m = max(int(cum[-1] / step) + 1, 2)
        u = np.linspace(0, cum[-1], m)
        X = np.interp(u, cum, P[:, 0]); Y = np.interp(u, cum, P[:, 1]); Pr = np.interp(u, cum, P[:, 2])
        s = self.s
        b.reset()
        s.begin_atomic()
        b.stroke_to(s.backend, float(X[0]), float(Y[0]), 0.0, 0.0, 0.0, 10.0, 1.0, 0.0, 0.0)
        for i in range(m):
            b.stroke_to(s.backend, float(X[i]), float(Y[i]), float(Pr[i]), 0.0, 0.0, dt, 1.0, 0.0, 0.0)
        b.stroke_to(s.backend, float(X[-1]), float(Y[-1]), 0.0, 0.0, 0.0, dt, 1.0, 0.0, 0.0)
        s.end_atomic()
        self.nstrokes += 1
        if self.ff is not None and self.nstrokes % self.frame_every == 0:
            self.grab()

    def record(self, path, fps=30):
        """film the canvas while it is painted: frames are piped straight to ffmpeg"""
        import subprocess
        self.ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                    '-s', '%dx%d' % (self.W // 4, self.H // 4), '-r', str(fps), '-i', '-',
                                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', path], stdin=subprocess.PIPE)

    def grab(self, repeat=1):
        q = N // 4
        fr = np.zeros((self.H // 4, self.W // 4, 3), np.uint8)
        for ty in range((self.H + N - 1) // N):
            for tx in range(self.W // N):
                with self.s.tile_request(tx, ty, readonly=True) as t:
                    blk = LUT[t[::4, ::4, :3].clip(0, 32768)]
                    h = min(q, fr.shape[0] - ty * q)
                    fr[ty * q:ty * q + h, tx * q:(tx + 1) * q] = blk[:h]
        b = fr.tobytes()
        for _ in range(repeat):
            self.ff.stdin.write(b)

    def finish_recording(self):
        if self.ff is not None:
            self.grab(repeat=self.hold)
            self.ff.stdin.close(); self.ff.wait(); self.ff = None

    def load(self, arr):
        """lay in an RGB float array as the starting surface (the primed, toned canvas)"""
        a = np.zeros((self.H, self.W, 4), np.uint8)
        a[..., :3] = np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8)
        a[..., 3] = 255
        self.s.load_from_numpy(a, 0, 0)

    def array(self):
        """step back and look: read the canvas as it stands"""
        out = np.zeros((self.H, self.W, 3), np.float32)
        for ty in range((self.H + N - 1) // N):
            for tx in range((self.W + N - 1) // N):
                with self.s.tile_request(tx, ty, readonly=True) as t:
                    h = min(N, self.H - ty * N); w = min(N, self.W - tx * N)
                    out[ty * N:ty * N + h, tx * N:tx * N + w] = t[:h, :w, :3].astype(np.float32) / (1 << 15)
        return np.clip(out, 0, 1) ** (1 / 2.2)      # tiles hold linear light

    def load_png(self, path):
        self.s.load_from_png(path, 0, 0)

    def save(self, path):
        self.s.save_as_png(path, 0, 0, self.W, self.H, alpha=False)
