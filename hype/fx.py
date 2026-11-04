"""Shared building blocks: fire, waving flags, silhouettes, text slams, and the
per-frame post chain (punch zoom, shake, chroma split, flash, grade, grain)."""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')

RED = (191, 10, 48)
WHITE = (245, 245, 245)
BLUE = (0, 40, 104)


# ---------------------------------------------------------------- fonts / text

DEFAULT_FONT = 'ChakraPetch-700.ttf'
SERIF_FONT = 'EBGaramond-MediumItalic.ttf'  # small elegant captions (style='serif')


@lru_cache(maxsize=64)
def font(size, name=DEFAULT_FONT):
    return ImageFont.truetype(os.path.join(FONTS, name), int(size))


def _line_width(f, line, track):
    return sum(f.getlength(c) for c in line) + track * max(0, len(line) - 1)


@lru_cache(maxsize=256)
def _text_rgba(text, size, style, name, max_w):
    track_k = 0.0 if style in ('mono', 'serif') else 0.06
    while True:
        f = font(size, name)
        track = size * track_k
        lines = text.split('\n')
        w = int(max(_line_width(f, l, track) for l in lines))
        if not max_w or w <= max_w or size < 12:
            break
        size = int(size * max_w / w) - 1
    asc, desc = f.getmetrics()
    lh = int(size * 1.08)
    pad = int(size * 0.35)
    img = Image.new('RGBA', (w + pad * 2, lh * len(lines) + pad * 2), (0, 0, 0, 0))
    glyphs = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(glyphs)
    for i, l in enumerate(lines):
        x = pad + (w - _line_width(f, l, track)) / 2
        y = pad + i * lh + (lh - asc - desc) / 2
        for c in l:
            d.text((x, y), c, font=f, fill=255)
            x += f.getlength(c) + track
    if style == 'mono':
        g = np.asarray(glyphs, np.float32)
        return np.dstack([np.full(g.shape + (3,), 255, np.float32), g])
    if style == 'serif':  # soft drop shadow only: reads like a subtitle, not a slam
        g = np.asarray(glyphs, np.float32) / 255
        sh = np.asarray(glyphs.filter(ImageFilter.GaussianBlur(max(2, size / 10))), np.float32) / 255
        alpha = np.maximum(np.clip(sh * 0.7, 0, 1), g)
        rgb = np.repeat((g * 255.0 / np.maximum(alpha, 1e-6))[..., None], 3, axis=2)
        return np.dstack([rgb, alpha * 255])
    shadow = glyphs.filter(ImageFilter.GaussianBlur(max(2, size / 14)))
    edge = glyphs.filter(ImageFilter.MaxFilter(3 if size < 60 else 5))
    sh = np.asarray(shadow, np.float32) / 255
    ed = np.asarray(edge, np.float32) / 255
    g = np.asarray(glyphs, np.float32) / 255
    color = {'gold': (255, 205, 60)}.get(style, (255, 255, 255))
    a = np.clip(np.maximum(sh * 0.9, ed * 0.6), 0, 1)
    rgb = np.zeros(g.shape + (3,), np.float32)
    rgb += g[..., None] * np.array(color, np.float32)
    alpha = np.maximum(a, g)
    return np.dstack([rgb / np.maximum(alpha, 1e-6)[..., None], alpha * 255])


def text(frame, s, size, cx=0.5, cy=0.5, style='clean', slam_t=None, name=DEFAULT_FONT, alpha=1.0, max_w=0.9):
    """Composite text onto float frame. slam_t: seconds since the slam began
    (text drops in from oversized and lands hard). Lines wider than max_w of the
    frame are shrunk to fit."""
    H, W = frame.shape[:2]
    scale = 1.0
    if style == 'serif':  # captions fade in quickly instead of slamming
        name = SERIF_FONT
        if slam_t is not None:
            alpha *= min(1.0, max(0.0, slam_t) / 0.08)
        slam_t = None
    if slam_t is not None:
        scale = 1.0 + 0.9 * math.exp(-max(0.0, slam_t) / 0.04)
        scale = round(scale * 25) / 25
    rgba = _text_rgba(s, int(size), style, name, int(max_w * W) if max_w else 0)
    if scale != 1.0:
        img = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
        rgba = np.asarray(img).astype(np.float32)
    paste(frame, rgba, int(cx * W - rgba.shape[1] / 2), int(cy * H - rgba.shape[0] / 2), alpha)


def paste(frame, rgba, x, y, alpha=1.0):
    H, W = frame.shape[:2]
    h, w = rgba.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = src[..., 3:4] / 255.0 * alpha
    dst = frame[y0:y1, x0:x1]
    dst *= 1 - a
    dst += src[..., :3] * a


# ---------------------------------------------------------------- noise / fire

def _tile_noise(n=512, seed=0, octaves=(4, 8, 16, 32, 64, 128)):
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for g in octaves:
        r = rng.random((g, g)).astype(np.float32)
        x = np.arange(n) * g / n
        i0 = np.floor(x).astype(int)
        f = (x - i0).astype(np.float32)
        f = f * f * (3 - 2 * f)
        i1 = (i0 + 1) % g
        a, b = r[i0][:, i0], r[i0][:, i1]
        c, d = r[i1][:, i0], r[i1][:, i1]
        fx, fy = f[None, :], f[:, None]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        tot += amp
        amp *= 0.55
    out /= tot
    return (out - out.min()) / (out.max() - out.min())


NOISE = _tile_noise()
NN = NOISE.shape[0]


def _lut(stops):
    xs = np.linspace(0, 1, 256)
    p = [s[0] for s in stops]
    return np.stack([np.interp(xs, p, [s[1][c] for s in stops]) for c in range(3)], 1).astype(np.float32)


FIRE = _lut([(0, (0, 0, 0)), (0.18, (50, 4, 0)), (0.38, (160, 28, 0)), (0.58, (240, 95, 10)),
             (0.78, (255, 185, 55)), (1.0, (255, 250, 225))])


def fire(frame, cx, cy, r, t, seed=0, rise=1.2, strength=1.0, squash=1.0, heat=1.45):
    """Additive turbulent fireball. r in px; t seconds since it ignited."""
    H, W = frame.shape[:2]
    grow = 0.35 + 0.65 * (1 - math.exp(-t * 4))
    r = r * grow
    x0, x1 = max(0, int(cx - r * 1.4)), min(W, int(cx + r * 1.4))
    y0, y1 = max(0, int(cy - r * 1.7)), min(H, int(cy + r * 1.2))
    if x1 <= x0 or y1 <= y0 or r < 2:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx = (xs - cx) / r
    dy = (ys - cy) / r
    dy = np.where(dy < 0, dy * 0.72, dy * 1.25) * squash
    u = (dx * 150 + seed * 131).astype(np.int32) % NN
    v = (dy * 150 + t * rise * 150 + seed * 71).astype(np.int32) % NN
    n = NOISE[v, u]
    u2 = (dx * 330 + seed * 53 + 200).astype(np.int32) % NN
    v2 = (dy * 330 + t * rise * 330).astype(np.int32) % NN
    n = n * 0.65 + NOISE[v2, u2] * 0.35
    d = np.sqrt(dx * dx + dy * dy)
    fade = math.exp(-max(0.0, t - 0.6) * 0.6)
    rx, ry = (xs - cx) / r, (ys - cy) / r
    edge = (np.clip((rx + 1.4) / 0.35, 0, 1) * np.clip((1.4 - rx) / 0.35, 0, 1) *
            np.clip((ry + 1.7) / 0.45, 0, 1) * np.clip((1.2 - ry) / 0.3, 0, 1))
    val = np.clip((1.05 - d + (n - 0.5) * 1.5) * heat * fade, 0, 1) * edge
    frame[y0:y1, x0:x1] += FIRE[(val * 255).astype(np.uint8)] * strength


# ---------------------------------------------------------------- flags

@lru_cache(maxsize=8)
def flag_base(h):
    """Official-proportion US flag, h px tall (w = 1.9h), float32 RGB."""
    ss = 3
    H, W = h * ss, int(h * 1.9) * ss
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)
    sh = H / 13
    for i in range(0, 13, 2):
        d.rectangle([0, i * sh, W, (i + 1) * sh], fill=RED)
    cw, ch = W * 0.76 / 1.9, sh * 7
    d.rectangle([0, 0, cw, ch], fill=(10, 49, 97))
    R = H * 0.0616 / 2
    for row in range(9):
        y = (row + 1) * ch / 10
        cols = [(2 * j + 1) * cw / 12 for j in range(6)] if row % 2 == 0 else [(2 * j + 2) * cw / 12 for j in range(5)]
        for x in cols:
            pts = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                rr = R if k % 2 == 0 else R * 0.382
                pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
            d.polygon(pts, fill=WHITE)
    img = img.resize((W // ss, H // ss), Image.LANCZOS)
    return np.asarray(img).astype(np.float32)


def wave_flag(h, t, amp=None, waves=1.4, speed=7.0, pole='left', droop=0.0):
    """Waving flag pinned at the pole side. Returns float RGBA (h+2amp, 1.9h)."""
    base = flag_base(h)
    fh, fw = base.shape[:2]
    if amp is None:
        amp = int(h * 0.12)
    xs = np.arange(fw)
    if pole == 'right':
        base = base[:, ::-1]
        d = (fw - 1 - xs) / fw
    else:
        d = xs / fw
    phase = 2 * math.pi * waves * d - speed * t
    dy = amp * np.sin(phase) * d ** 0.8 + droop * h * d ** 2
    shade = 1 + 0.38 * np.cos(phase) * np.minimum(1, d * 4)
    oh = fh + 2 * amp + int(abs(droop) * h) + 2
    ys = np.arange(oh)[:, None] - amp - dy[None, :]
    valid = ((ys >= 0) & (ys < fh - 1)).astype(np.float32)
    src = base[np.clip(ys, 0, fh - 1).astype(int), xs[None, :]]
    rgb = np.clip(src * shade[None, :, None], 0, 255)
    return np.concatenate([rgb, valid[..., None] * 255], 2)


def flag_fullscreen(W, H, t, dark=0.0):
    h = int(H * 1.25)
    base = flag_base(h)
    fh, fw = base.shape[:2]
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    ph = xs * 0.011 + ys * 0.004 - t * 5.0
    sx = xs * (fw - 60) / W + 30 + np.sin(ph) * 14
    sy = ys * (fh - 80) / H + 40 + np.sin(ph) * 22
    out = base[np.clip(sy, 0, fh - 1).astype(int), np.clip(sx, 0, fw - 1).astype(int)]
    shade = 1 + 0.32 * np.cos(ph)
    return np.clip(out * shade[..., None] * (1 - dark), 0, 255)


# ---------------------------------------------------------------- silhouettes

class Sil:
    """Draw a silhouette in local units, anti-aliased via supersampling."""

    def __init__(self, W, H, ox, oy, sc, ss=2):
        self.W, self.H, self.ss = W, H, ss
        self.ox, self.oy, self.sc = ox, oy, sc
        self.img = Image.new('L', (W * ss, H * ss), 0)
        self.d = ImageDraw.Draw(self.img)

    def p(self, x, y):
        return ((self.ox + x * self.sc) * self.ss, (self.oy + y * self.sc) * self.ss)

    def poly(self, pts, fill=255):
        self.d.polygon([self.p(*q) for q in pts], fill=fill)

    def line(self, pts, w, fill=255):
        P = [self.p(*q) for q in pts]
        ww = max(1, int(w * self.sc * self.ss))
        self.d.line(P, fill=fill, width=ww, joint='curve')
        for q in (P[0], P[-1]):
            r = ww / 2
            self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=fill)

    def circle(self, c, r, fill=255, outline_w=None):
        x, y = self.p(*c)
        rr = r * self.sc * self.ss
        if outline_w:
            self.d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=fill, width=max(1, int(outline_w * self.sc * self.ss)))
        else:
            self.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=fill)

    def mask(self):
        return np.asarray(self.img.resize((self.W, self.H), Image.BILINEAR), np.float32) / 255.0


def comp_sil(frame, m, color=(8, 6, 10), rim=(255, 170, 70), light=(-1, -1), rim_px=3, rim_k=1.0):
    """Composite a silhouette mask with a rim light on edges facing `light`."""
    lx, ly = light
    sh = np.roll(m, (int(-ly * rim_px), int(-lx * rim_px)), axis=(0, 1))
    r = np.clip(m - sh, 0, 1) * rim_k
    frame *= (1 - m)[..., None]
    frame += m[..., None] * np.array(color, np.float32)
    frame += r[..., None] * np.array(rim, np.float32)


# ---------------------------------------------------------------- backgrounds

@lru_cache(maxsize=4)
def _polar(W, H, cx, cy):
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    return np.arctan2(ys - cy, xs - cx), np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)


def sunset(W, H, t, sun=(0.5, 0.62), sun_r=0.16, top=(40, 0, 20), mid=(200, 40, 10), hor=(255, 170, 60), rays=True):
    y = np.linspace(0, 1, H)[:, None, None]
    k = np.clip(y / 0.65, 0, 1)
    c = np.where(k < 0.6, np.array(top) + (np.array(mid) - np.array(top)) * (k / 0.6),
                 np.array(mid) + (np.array(hor) - np.array(mid)) * ((k - 0.6) / 0.4))
    sky = np.broadcast_to(c, (H, W, 3)).astype(np.float32).copy()
    cx, cy = int(sun[0] * W), int(sun[1] * H)
    ang, dist = _polar(W, H, cx, cy)
    R = sun_r * H
    glow = np.exp(-dist / (R * 2.2))
    sky += glow[..., None] * np.array([255, 150, 60], np.float32) * 0.8
    if rays:
        ray = (0.5 + 0.5 * np.sin(ang * 18 + t * 0.6)) ** 6 * np.exp(-dist / (W * 0.45))
        sky += ray[..., None] * np.array([255, 200, 120], np.float32) * 0.35
    disc = np.clip((R - dist) / 2.0, 0, 1)
    sky = sky * (1 - disc[..., None]) + disc[..., None] * np.array([255, 245, 210], np.float32)
    return sky


def embers(frame, t, n=160, seed=1, color=(255, 150, 40), vx=-260, vy=-120, size=2):
    H, W = frame.shape[:2]
    rng = np.random.default_rng(seed)
    x0, y0 = rng.random(n) * W, rng.random(n) * H
    sp = 0.5 + rng.random(n)
    xs = ((x0 + vx * sp * t) % W).astype(int)
    ys = ((y0 + vy * sp * t + np.sin(t * 3 + x0) * 10) % H).astype(int)
    br = (0.5 + 0.5 * np.sin(t * 9 + x0)) * 0.8 + 0.2
    for dy in range(size):
        for dx in range(size):
            yy, xx = np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)
            frame[yy, xx] += br[:, None] * np.array(color, np.float32)


def speed_lines(frame, t, n=40, seed=3, speed=2600, alpha=0.35, y_range=(0, 1)):
    H, W = frame.shape[:2]
    rng = np.random.default_rng(seed)
    for i in range(n):
        y = int((y_range[0] + rng.random() * (y_range[1] - y_range[0])) * H)
        L = int(80 + rng.random() * 260)
        x = int((rng.random() * W * 2 - speed * (0.6 + rng.random()) * t) % (W * 2)) - W // 2
        x0, x1 = max(0, x), min(W, x + L)
        if x1 > x0:
            frame[y:y + 2, x0:x1] = frame[y:y + 2, x0:x1] * (1 - alpha) + 255 * alpha


# ---------------------------------------------------------------- post chain

class Post:
    def __init__(self, W, H, seed=7):
        self.W, self.H = W, H
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2)
        self.vig = (1 - 0.42 * np.clip(r / 1.3, 0, 1) ** 2.2)[..., None].astype(np.float32)
        rng = np.random.default_rng(seed)
        self.grain = [rng.normal(0, 7, (H, W, 1)).astype(np.float32) for _ in range(6)]
        self.rng = rng
        self.n = 0

    def __call__(self, f, tb, ts, fx):
        """f float frame. tb: seconds since last beat; ts: seconds since cut.
        Light-touch looks (all off unless the shot asks): trail (0-0.6, echo of earlier frames),
        hue (degrees of slow hue breathing), drift (px of wandering RGB split), duotone ((dark rgb, light rgb)),
        bloom (0-1 highlight glow), mirror ('h' folds the left half onto the right)."""
        W, H = self.W, self.H
        if fx.get('mirror') == 'h':
            f = f.copy()
            f[:, W // 2:] = f[:, :W - W // 2][:, ::-1]
        trail = fx.get('trail', 0.0)
        if trail and getattr(self, 'prev', None) is not None and ts > getattr(self, 'last_ts', 1e9) >= 0:
            f = f * (1 - trail) + self.prev * trail
        self.prev, self.last_ts = (f.copy() if trail else None), ts
        punch = fx.get('punch', 0.06) * math.exp(-tb / 0.09)
        drift = fx.get('drift', 0.0) * ts
        shake = fx.get('shake', 10) * math.exp(-tb / 0.12)
        s = 1 + punch + drift
        sx = self.rng.uniform(-1, 1) * shake
        sy = self.rng.uniform(-1, 1) * shake
        if s > 1.001 or shake > 0.5:
            s = max(s, 1 + (abs(sx) + abs(sy)) * 2.2 / min(W, H))
            cw, chh = W / s, H / s
            x0 = (W - cw) / 2 + sx
            y0 = (H - chh) / 2 + sy
            x0 = min(max(0, x0), W - cw)
            y0 = min(max(0, y0), H - chh)
            img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
            img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + chh))
            f = np.asarray(img).astype(np.float32)
        k = int(round(fx.get('chroma', 6) * math.exp(-tb / 0.07)))
        if k:
            f[..., 0] = np.roll(f[..., 0], k, axis=1)
            f[..., 2] = np.roll(f[..., 2], -k, axis=1)
        drift = fx.get('drift', 0)
        if drift:
            dx = int(round(drift * math.sin(ts * 2.1)))
            dy = int(round(drift * 0.6 * math.sin(ts * 1.3 + 1.0)))
            f[..., 0] = np.roll(np.roll(f[..., 0], dx, axis=1), dy, axis=0)
            f[..., 2] = np.roll(np.roll(f[..., 2], -dx, axis=1), -dy, axis=0)
        hue = fx.get('hue', 0)
        if hue:
            a = math.radians(hue * math.sin(ts * 2 * math.pi / 3.2))
            c, sn = math.cos(a), math.sin(a)
            # rotate chroma in YIQ space
            m = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)
            r = np.array([[1, 0, 0], [0, c, -sn], [0, sn, c]], np.float32)
            t = np.linalg.inv(m) @ r @ m
            f = f @ t.T.astype(np.float32)
        bloom = fx.get('bloom', 0)
        if bloom:
            small = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
            hi = np.clip(np.asarray(small, np.float32) - 170, 0, 255) * 2.2
            glow = Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W / 160))
            f = f + np.asarray(glow.resize((W, H), Image.BILINEAR), np.float32) * bloom
        flash = fx.get('flash', 0.85) * math.exp(-ts / 0.05)
        if flash > 0.01:
            f = f + (255 - f) * flash
        x = np.clip(f / 255.0, 0, 1)
        x = x * x * (3 - 2 * x) * 0.35 + x * 0.65
        g = x.mean(2, keepdims=True)
        x = g + (x - g) * fx.get('sat', 1.18)
        duo = fx.get('duotone')
        if duo:
            lo, hi = np.array(duo[0], np.float32) / 255, np.array(duo[1], np.float32) / 255
            x = x * (1 - fx.get('duo_mix', 0.55)) + (lo + (hi - lo) * x.mean(2, keepdims=True)) * fx.get('duo_mix', 0.55)
        f = x * 255 * self.vig + self.grain[self.n % len(self.grain)]
        self.n += 1
        return np.clip(f, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- motion graphics (light touch)

_grid_cache = {}


def _radius(W, H, cx, cy):
    key = (W, H, round(cx, 3), round(cy, 3))
    if key not in _grid_cache:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        _grid_cache.clear()
        _grid_cache[key] = np.sqrt((xs - cx * W) ** 2 + (ys - cy * H) ** 2)
    return _grid_cache[key]


def rings(frame, ts, cx=0.5, cy=0.5, period=0.7, n=3, width=1.6, alpha=0.35, color=(255, 255, 255), reach=0.75):
    """Thin concentric rings radiating out from (cx, cy), like a phone signal; each fades as it grows."""
    H, W = frame.shape[:2]
    r = _radius(W, H, cx, cy)
    R = reach * math.hypot(W, H) / 2
    a = np.zeros((H, W), np.float32)
    for k in range(n):
        ph = ((ts / period) + k / n) % 1.0
        rk = ph * R
        a = np.maximum(a, np.exp(-((r - rk) / (width * H / 1080)) ** 2) * (1 - ph) ** 1.5)
    a = (a * alpha)[..., None]
    frame *= 1 - a
    frame += np.array(color, np.float32) * a


def scope(frame, samples, sr, t, y=0.86, amp=0.05, alpha=0.55, span=0.05, color=(255, 255, 255)):
    """A fine oscilloscope trace of the soundtrack around time t (the voice made visible)."""
    H, W = frame.shape[:2]
    i0 = int((t - span / 2) * sr)
    seg = samples[max(0, i0):max(0, i0) + int(span * sr)]
    if len(seg) < 8:
        return
    idx = np.linspace(0, len(seg) - 1, 480).astype(int)
    v = seg[idx] / (np.abs(samples).max() + 1e-9)
    xs = np.linspace(W * 0.08, W * 0.92, len(v))
    ys = y * H - v * amp * H * 4
    img = Image.new('L', (W, H), 0)
    ImageDraw.Draw(img).line(list(zip(xs.tolist(), ys.tolist())), fill=255, width=max(1, int(2 * H / 1080)))
    m = (np.asarray(img, np.float32) / 255 * alpha)[..., None]
    frame *= 1 - m
    frame += np.array(color, np.float32) * m

