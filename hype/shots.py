"""Generated shots. Each is fn(ts, dur, W, H, p) -> float32 HxWx3 frame.
ts = seconds since the cut, p = per-shot params from the edit list."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx

TAU = 2 * math.pi


def _rot(pts, c, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def _ground(f, y0, t, speed, col=(18, 8, 6), streak=(90, 40, 20)):
    H, W = f.shape[:2]
    y0 = int(y0)
    f[y0:] = np.array(col, np.float32)
    rng = np.random.default_rng(11)
    for i in range(60):
        yy = y0 + int((rng.random() ** 1.7) * (H - y0))
        depth = (yy - y0) / max(1, H - y0)
        L = int(30 + 200 * depth)
        x = int((rng.random() * W * 2 - speed * (0.3 + depth * 1.6) * t) % (W * 2)) - W // 2
        x0, x1 = max(0, x), min(W, x + L)
        if x1 > x0:
            f[yy:yy + 2, x0:x1] = np.array(streak, np.float32) * (0.4 + depth)


# ---------------------------------------------------------------- Washington on a T-Rex

def trex(ts, dur, W, H, p):
    f = fx.sunset(W, H, ts, sun=(0.78, 0.6), sun_r=0.09, top=(20, 0, 6), mid=(130, 16, 4), hor=(255, 110, 25))
    # volcano on the horizon
    vx, hy = 0.86 * W, 0.8 * H
    vol = Image.new('L', (W, H), 0)
    ImageDraw.Draw(vol).polygon([(vx - 330, hy), (vx - 70, hy - 210), (vx + 40, hy - 215), (vx + 300, hy)], fill=255)
    m = np.asarray(vol, np.float32)[..., None] / 255
    f = f * (1 - m) + m * np.array([45, 10, 6], np.float32)
    fx.fire(f, vx - 15, hy - 250, 170, ts + 0.4, seed=3, rise=1.6)
    for k, (x, r, t0) in enumerate([(0.12, 120, 0.0), (0.33, 90, 0.25), (0.58, 140, 0.5)]):
        if ts > t0:
            fx.fire(f, x * W, hy - 30, r, ts - t0, seed=10 + k)
    _ground(f, hy, ts, 900, col=(22, 7, 4), streak=(110, 35, 12))
    fx.embers(f, ts, n=180, vx=-420, vy=-160)

    phase = ts * TAU * 2.3
    sc = 0.74 * H / 720
    ox = 0.42 * W + 10 * math.sin(ts * 1.3)
    oy = 0.92 * H - 312 * sc - 14 * abs(math.sin(phase)) * sc
    S = fx.Sil(W, H, ox, oy, sc)

    def hd(pts):  # the head is drawn small, then scaled up around the neck
        return [(300 + (x - 300) * 1.4, -75 + (y + 60) * 1.4) for x, y in pts]

    sway = 18 * math.sin(phase * 0.5)
    jaw = 0.32 + 0.12 * math.sin(ts * 5)
    hinge = (338, -84)
    lower = hd(_rot([(330, -50), (400, -46), (455, -52), (472, -60), (444, -68), (384, -70), (344, -78)], hinge, jaw * 0.6))
    upper = hd([(346, -92), (420, -96), (478, -99), (486, -110), (456, -129), (400, -141), (350, -151), (318, -149),
                (298, -134)])
    body = [(-10, -82), (-130, -84), (-260, -66), (-380, -44), (-482, -24 + sway), (-478, -14 + sway), (-380, -14),
            (-260, -2), (-130, 26), (-30, 76), (40, 104), (130, 110), (205, 86), (255, 46), (290, 6), (306, -30)]
    neck = [(282, -128), (240, -110), (170, -106), (80, -100)]
    S.poly(body + lower + upper + neck)
    for i in range(5):  # teeth
        x = 360 + i * 22
        S.poly(hd([(x, -95), (x + 9, -95), (x + 4, -82)]))
        lx, ly = _rot([(x - 4, -70)], hinge, jaw * 0.6)[0]
        S.poly(hd([(lx, ly), (lx + 9, ly - 1), (lx + 5, ly - 13)]))
    S.line([(258, 30), (292, 56), (310, 46)], 15)  # tiny arms

    def limb(a, b, w0, w1):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        S.poly([(a[0] + nx * w0 / 2, a[1] + ny * w0 / 2), (b[0] + nx * w1 / 2, b[1] + ny * w1 / 2),
                (b[0] - nx * w1 / 2, b[1] - ny * w1 / 2), (a[0] - nx * w0 / 2, a[1] - ny * w0 / 2)])
        S.circle(b, w1 / 2)

    for off in (math.pi, 0.0):
        ph = phase + off
        hip = (10, 30)
        a1 = 0.35 + 0.5 * math.sin(ph)
        knee = (hip[0] + 130 * math.sin(a1), hip[1] + 125 * math.cos(a1))
        a2 = -0.45 + 0.4 * math.sin(ph) - 0.35 * max(0.0, -math.cos(ph))
        ank = (knee[0] + 115 * math.sin(a2), knee[1] + 115 * math.cos(a2))
        a3 = 0.15 + 0.3 * math.sin(ph)
        foot = (ank[0] + 55 * math.sin(a3), ank[1] + 55 * math.cos(a3))
        S.circle(hip, 62)
        limb(hip, knee, 110, 46)
        limb(knee, ank, 44, 28)
        limb(ank, foot, 28, 20)
        limb(foot, (foot[0] + 58, foot[1] + 2), 18, 8)

    # George Washington, flag aloft (drawn at 1.35x around the saddle)
    def g(pts):
        return [(85 + (x - 85) * 1.35, -92 + (y + 80) * 1.35) for x, y in pts]

    G = 1.35
    flap = 14 * math.sin(ts * 17)
    S.line(g([(85, -80), (142, -56), (132, 2)]), 25 * G)
    S.line(g([(86, -86), (100, -190)]), 44 * G)
    S.poly(g([(68, -120), (76, -82), (18, -70 + flap), (-14, -58 + flap * 1.4), (42, -100)]))
    S.circle(g([(109, -222)])[0], 21 * G)
    S.circle(g([(89, -216)])[0], 8 * G)
    S.poly(g([(126, -228), (136, -217), (126, -213)]))
    S.poly(g([(66, -246), (84, -250), (110, -290), (132, -252), (150, -232), (128, -238), (108, -244), (86, -240)]))
    S.poly(g([(84, -214), (74, -206), (80, -200), (90, -208)]))  # queue ribbon
    S.line(g([(100, -183), (152, -146), (196, -124)]), 16 * G)
    S.line(g([(100, -186), (132, -226), (141, -268)]), 18 * G)
    top = g([(150, -380)])[0]
    S.line(g([(137, -240)]) + [top], 6 * G)
    S.circle(top, 7 * G)
    m = S.mask()
    fx.comp_sil(f, m, rim=(255, 140, 50), light=(1, -0.6), rim_px=3)
    ex, ey = S.p(*hd([(400, -127)])[0])
    fx.fire(f, ex / S.ss, ey / S.ss, 11 * sc + 3, 5.0, seed=77, strength=1.5)  # glowing eye

    fl = fx.wave_flag(int(120 * sc), ts, pole='right', speed=11, waves=1.6)
    px, py = S.p(*top)
    fx.paste(f, fl, int(px / S.ss - fl.shape[1]), int(py / S.ss - fl.shape[0] * 0.1))
    return f


# ---------------------------------------------------------------- Lincoln on a chopper

def _mountains(W, H, y, seed, amp, col):
    rng = np.random.default_rng(seed)
    xs = np.arange(W * 3)
    ys = np.zeros_like(xs, dtype=np.float32)
    for k in (1, 2, 5, 11):
        ys += np.sin(xs / W * TAU * k + rng.random() * 9) / k
    return y - (ys - ys.min()) / (ys.max() - ys.min()) * amp, col


def chopper(ts, dur, W, H, p):
    f = fx.sunset(W, H, ts, sun=(0.62, 0.7), sun_r=0.2, top=(30, 5, 50), mid=(210, 50, 70), hor=(255, 180, 80))
    hy = int(0.8 * H)
    ridge, col = _mountains(W, H, hy, 4, 0.16 * H, (70, 20, 45))
    off = int(ts * 60) % W
    r = ridge[off:off + W]
    ys = np.arange(H)[:, None]
    m = (ys > r[None, :]).astype(np.float32)[..., None]
    f = f * (1 - m) + m * np.array(col, np.float32)
    for k, (x, rr, t0) in enumerate([(0.2, 110, 0.15), (0.9, 150, 0.0)]):
        if ts > t0:
            fx.fire(f, x * W, hy - 20, rr, ts - t0, seed=20 + k)
    f[hy:] = np.array([24, 18, 26], np.float32)
    dash = int(ts * 1800) % 240
    yy = int(hy + (H - hy) * 0.55)
    for x in range(-dash, W, 240):
        f[yy:yy + 6, max(0, x):max(0, x + 120)] = (230, 200, 120)
    fx.speed_lines(f, ts, n=30, speed=3200, alpha=0.25, y_range=(0.15, 0.78))

    sc = 1.05 * H / 720
    ox = 0.3 * W + 8 * math.sin(ts * 2.1)
    oy = H - 0.06 * H - 75 * sc + 2.5 * math.sin(ts * 47) * sc
    S = fx.Sil(W, H, ox, oy, sc)
    spin = ts * 22
    for c, rad in (((0, 0), 75), ((362, 7), 68)):
        S.circle(c, rad, outline_w=17)
        S.circle(c, 15)
        for k in range(10):
            a = spin + k * TAU / 10
            S.line([c, (c[0] + rad * math.cos(a), c[1] + rad * math.sin(a))], 3)
    S.line([(0, 0), (60, -96)], 14)
    S.line([(0, 0), (120, -40)], 12)
    S.poly([(18, -106), (110, -104), (112, -88), (24, -86)])
    S.poly([(120, -120), (200, -130), (232, -113), (202, -97), (128, -100)])
    S.line([(100, -112), (258, -144)], 12)
    S.line([(256, -150), (362, 7)], 12)
    S.line([(266, -146), (370, 0)], 7)
    S.line([(250, -132), (192, -30)], 12)
    S.poly([(96, -92), (186, -96), (196, -24), (106, -18)])
    S.poly([(110, -92), (128, -150), (152, -145), (140, -90)])
    S.poly([(150, -92), (178, -146), (200, -136), (178, -88)])
    S.line([(150, -30), (-40, -24), (-96, -38)], 10)
    S.line([(258, -150), (236, -272), (210, -270)], 8)
    S.circle((288, -124), 16)
    S.line([(-6, -60), (-34, -346)], 5)  # sissy-bar flagpole
    # Abraham Lincoln
    flap = 16 * math.sin(ts * 19)
    S.line([(70, -110), (172, -112), (232, -46)], 26)
    S.line([(70, -112), (60, -236)], 44)
    S.poly([(48, -160), (40, -112), (-44, -112 + flap), (-80, -98 + flap * 1.5), (20, -100)])
    S.circle((66, -268), 22)
    S.poly([(54, -262), (92, -258), (91, -240), (70, -236), (54, -248)])
    S.poly([(86, -274), (95, -266), (86, -263)])
    S.poly([(36, -293), (100, -293), (100, -285), (36, -285)])
    S.poly([(46, -292), (90, -292), (88, -376), (48, -376)])
    S.line([(64, -214), (142, -232), (212, -266)], 16)
    m = S.mask()
    fx.comp_sil(f, m, rim=(255, 170, 90), light=(0.8, -0.4), rim_px=3)
    # exhaust flames, headlight, aviator glint
    ex, ey = S.p(-100, -38)
    fx.fire(f, ex / S.ss - 30, ey / S.ss, 55 * sc, 0.5 + (ts * 7) % 1.0, seed=int(ts * 30), squash=1.6, strength=1.2)
    hx, hy2 = S.p(300, -124)
    hx, hy2 = hx / S.ss, hy2 / S.ss
    ang, dist = fx._polar(W, H, int(hx), int(hy2))
    beam = np.exp(-np.abs(ang) * 9) * np.exp(-dist / (W * 0.5)) * (dist > 6)
    f += beam[..., None] * np.array([255, 235, 190], np.float32) * 0.9
    gx, gy = S.p(84, -272)
    _glint(f, gx / S.ss, gy / S.ss, 1.0 if (ts % 1.2) < 0.25 else 0.25, 40 * sc)
    fl = fx.wave_flag(int(95 * sc), ts, pole='right', speed=14, waves=1.8)
    px, py = S.p(-34, -346)
    fx.paste(f, fl, int(px / S.ss - fl.shape[1]), int(py / S.ss - 6))
    return f


def _glint(f, x, y, k, L):
    H, W = f.shape[:2]
    x, y = int(x), int(y)
    for dx in range(-int(L), int(L) + 1):
        a = k * (1 - abs(dx) / L) ** 2
        for xx, yy in ((x + dx, y), (x, y + dx)):
            if 0 <= xx < W and 0 <= yy < H:
                f[max(0, yy - 1):yy + 1, max(0, xx - 1):xx + 1] += 255 * a


# ---------------------------------------------------------------- Frontier AI lab

def datacenter(ts, dur, W, H, p):
    f = np.zeros((H, W, 3), np.float32)
    cx, cy = W / 2, H * 0.47
    F = 0.8 * W
    zc = ts * 3.2
    img = Image.new('RGB', (W, H), (4, 6, 14))
    d = ImageDraw.Draw(img)

    def pr(x, y, z):
        dz = z - zc
        return cx + F * x / dz, cy + F * y / dz

    for x in (-1.2, 1.2):  # solid rack faces
        d.polygon([pr(x, -1.0, zc + 0.35), pr(x, -1.0, zc + 45), pr(x, 0.85, zc + 45), pr(x, 0.85, zc + 0.35)],
                  fill=(13, 16, 26))
        for y in np.linspace(-0.92, 0.78, 15):
            d.line([pr(x, y, zc + 0.35), pr(x, y, zc + 45)], fill=(26, 30, 44), width=1)
    d.polygon([pr(-1.2, 0.85, zc + 0.35), pr(-1.2, 0.85, zc + 45), pr(1.2, 0.85, zc + 45), pr(1.2, 0.85, zc + 0.35)],
              fill=(8, 10, 16))
    for x in (-0.45, 0.45):  # floor reflections of the light strips
        d.line([pr(x, 0.85, zc + 0.35), pr(x, 0.85, zc + 45)], fill=(40, 52, 80), width=6)
    for z in np.arange(math.floor(zc) + 0.4, zc + 40, 1.0):  # rack frames
        for x in (-1.2, 1.2):
            a, b = pr(x, -1.0, z), pr(x, 0.85, z)
            fog = max(0.0, 1 - (z - zc) / 40)
            c = int(90 * fog)
            d.line([a, b], fill=(c, c, int(c * 1.3)), width=max(2, int(14 / (z - zc))))
        a, b = pr(-1.2, 0.85, z), pr(1.2, 0.85, z)
        d.line([a, b], fill=(18, 22, 34), width=1)
    for x in (-0.45, 0.45):  # ceiling light strips
        d.line([pr(x, -1.05, zc + 0.35), pr(x, -1.05, zc + 45)], fill=(200, 225, 255), width=3)
    for x in (-0.6, 0, 0.6):
        d.line([pr(x, 0.85, zc + 0.35), pr(x, 0.85, zc + 45)], fill=(22, 28, 44), width=1)
    f += np.asarray(img, np.float32)

    zs = np.arange(math.floor(zc / 0.12) * 0.12 + 0.12, zc + 40, 0.12)
    yv = np.linspace(-0.9, 0.75, 30)
    Z, Y = np.meshgrid(zs, yv)
    Z, Y = Z.ravel(), Y.ravel()
    led = np.zeros((H, W, 3), np.float32)
    pal = np.array([[60, 140, 255], [40, 230, 255], [60, 255, 120], [255, 180, 40], [240, 240, 255]], np.float32)
    for side in (-1.2, 1.2):
        dz = Z - zc
        ok = dz > 0.3
        z, y, dzz = Z[ok], Y[ok], dz[ok]
        idx = np.round(z / 0.12) * 31 + np.round(y * 100) + (side > 0) * 7
        h = np.sin(idx * 12.9898 + np.floor(ts * (4 + (idx % 5)) + idx) * 78.233) * 43758.5453
        h = h - np.floor(h)
        on = h > 0.45
        sx = (cx + F * side / dzz).astype(int)
        sy = (cy + F * y / dzz).astype(int)
        size = np.clip(F * 0.012 / dzz, 1, 5).astype(int)
        fog = np.clip(1 - dzz / 40, 0, 1) ** 1.5
        hp = (np.abs(idx) * 0.618) % 1
        col = pal[np.where(hp < 0.55, 0, np.where(hp < 0.8, 1, np.where(hp < 0.9, 2, np.where(hp < 0.96, 3, 4))))]
        col = col * (fog * on * (0.6 + 0.4 * h))[:, None]
        for s in range(1, 6):
            sel = (size == s) & on & (sx >= 0) & (sx < W - s) & (sy >= 0) & (sy < H - s)
            for dy in range(s):
                for dx in range(s):
                    np.add.at(led, (sy[sel] + dy, sx[sel] + dx), col[sel])
    small = Image.fromarray(np.clip(led, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    bloom = np.asarray(small.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR), np.float32)
    f += led + bloom * 2.2
    f[int(cy + F * 0.85 / 6):] *= 1.0
    return f


# ---------------------------------------------------------------- terminal

TERM = [
    '$ ./train --model FREEDOM-1 --gpus 1,776,000',
    '[init] loading 50 states .................. ok',
    '[init] eagle.cfg .......................... ok',
    'step 1776   loss 2.4831',
    'step 1812   loss 0.8615',
    'step 1865   loss 0.0417',
    'step 1969   loss 0.0000   (moon reached)',
    'step 2026   loss -inf     FREEDOM ACHIEVED',
]


def terminal(ts, dur, W, H, p):
    lines = p.get('lines', TERM)
    img = Image.new('RGB', (W, H), (4, 10, 7))
    d = ImageDraw.Draw(img)
    size = int(H * p.get('size', 0.056))
    fnt = fx.font(size, 'JetBrainsMono.ttf')
    total = sum(len(l) for l in lines)
    n = int(total * min(1.0, ts / (dur * 0.8)))
    y = int(H * p.get('y', 0.1))
    for l in lines:
        s = l[:max(0, n)]
        n -= len(l)
        if s:
            col = (255, 230, 90) if 'FREEDOM' in s else (90, 255, 140)
            d.text((int(W * 0.05), y), s, font=fnt, fill=col)
        if n < 0:
            if (ts * 3) % 1 < 0.6:
                bx = int(W * 0.05) + int(fnt.getlength(s))
                d.rectangle([bx, y + 4, bx + size * 0.55, y + size + 4], fill=(90, 255, 140))
            break
        y += int(size * 1.45)
    f = np.asarray(img, np.float32)
    glow = np.asarray(img.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(2)).resize((W, H)), np.float32)
    f = f + glow * 1.2
    f[::3] *= 0.8
    return f


# ---------------------------------------------------------------- flyover

JET = [(0, -62), (7, -34), (10, -8), (58, 18), (58, 28), (12, 26), (24, 50), (24, 58), (5, 52), (0, 56)]


def flyover(ts, dur, W, H, p):
    y = np.linspace(0, 1, H)[:, None, None]
    f = np.broadcast_to(np.array([15, 50, 135]) + (np.array([175, 205, 240]) - np.array([15, 50, 135])) * y ** 1.4,
                        (H, W, 3)).astype(np.float32).copy()
    ang, dist = fx._polar(W, H, int(W * 0.82), int(H * 0.16))
    f += np.exp(-dist / (H * 0.12))[..., None] * np.array([255, 240, 200], np.float32)
    f += ((0.5 + 0.5 * np.sin(ang * 14)) ** 8 * np.exp(-dist / (H * 0.6)))[..., None] * 60
    k = ts / max(dur, 0.01)
    scale = (0.7 + 1.3 * k) * H / 720
    cxf, cyf = W * (0.45 + 0.08 * k), H * (1.05 - 1.25 * k)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    trails = [(255, 40, 50), (250, 250, 250), (40, 90, 255), (250, 250, 250)]
    pos = [(0, 0), (-95, 75), (95, 75), (0, 150)]
    for (px, py), col in zip(pos, trails):
        jx, jy = cxf + px * scale, cyf + py * scale + 50 * scale
        for i in range(24):
            a, b = i / 24, (i + 1) / 24
            w0, w1 = (10 + 80 * a) * scale, (10 + 80 * b) * scale
            y0, y1 = jy + a * H * 1.6, jy + b * H * 1.6
            al = int(200 * (1 - a) ** 1.2)
            d.polygon([(jx - w0, y0), (jx + w0, y0), (jx + w1, y1), (jx - w1, y1)], fill=col + (al,))
    lay = np.asarray(layer.filter(ImageFilter.GaussianBlur(6)), np.float32)
    fx.paste(f, lay, 0, 0)
    S = fx.Sil(W, H, 0, 0, 1)
    for px, py in pos:
        jx, jy = cxf + px * scale, cyf + py * scale
        pts = JET + [(-x, y) for x, y in reversed(JET)]
        S.d.polygon([((jx + x * scale) * S.ss, (jy + y * scale) * S.ss) for x, y in pts], fill=255)
    m = S.mask()
    fx.comp_sil(f, m, color=(40, 44, 56), rim=(255, 240, 200), light=(1, -1), rim_px=2, rim_k=0.6)
    # stadium rim
    rim = Image.new('L', (W, H), 0)
    rd = ImageDraw.Draw(rim)
    rd.ellipse([-W * 0.3, H * 0.86, W * 1.3, H * 1.6], fill=255)
    for x in (0.08, 0.3, 0.7, 0.92):
        rd.rectangle([x * W - 4, H * 0.7, x * W + 4, H], fill=255)
        rd.rectangle([x * W - 30, H * 0.68, x * W + 30, H * 0.72], fill=255)
    mm = np.asarray(rim, np.float32) / 255
    f = f * (1 - mm[..., None]) + mm[..., None] * np.array([12, 14, 22], np.float32)
    for x in (0.08, 0.3, 0.7, 0.92):
        _glint(f, x * W, H * 0.7, 0.9, 50)
    return f


# ---------------------------------------------------------------- Reagan vs. a samurai

def duel(ts, dur, W, H, p):
    beat = p.get('_beat', 0.43)
    y = np.linspace(0, 1, H)[:, None, None]
    f = np.broadcast_to(np.array([70, 0, 20]) + (np.array([255, 120, 90]) - np.array([70, 0, 20])) * y ** 1.3,
                        (H, W, 3)).astype(np.float32).copy()
    cx, cy = W / 2, H * 0.44
    ang, dist = fx._polar(W, H, int(cx), int(cy))
    R = H * 0.33
    f += np.exp(-dist / (R * 1.6))[..., None] * np.array([255, 90, 40], np.float32) * 0.5
    disc = np.clip((R - dist) / 2.0, 0, 1)[..., None]
    f = f * (1 - disc) + disc * np.array([235, 30, 35], np.float32)
    for k, (yy, amp, col, sp) in enumerate([(0.74, 0.16, (150, 40, 60), 8), (0.82, 0.12, (100, 20, 40), 20)]):
        ridge, _ = _mountains(W, H, yy * H, 30 + k, amp * H, col)
        off = int(ts * sp) % W
        m = (np.arange(H)[:, None] > ridge[off:off + W][None, :]).astype(np.float32)[..., None]
        f = f * (1 - m) + m * (np.array(col, np.float32) * 0.6 + f * 0.4)
    fog = np.exp(-((y - 0.8) / 0.08) ** 2) * 0.35
    f = f * (1 - fog) + fog * np.array([255, 190, 190], np.float32)

    sc = 0.95 * H / 720
    phase = (ts % beat) / beat
    push = 10 * math.sin(phase * math.pi)
    S = fx.Sil(W, H, cx, H * 0.93, sc)
    rk = [(-520, 0), (-420, -40), (-330, -30), (-200, -55), (-60, -45), (80, -60), (230, -50), (360, -35),
          (470, -55), (560, -20), (800, 0), (800, 200), (-800, 200), (-800, 0)]
    S.poly(rk)
    C = (0, -372)

    def blade(hands, tipdir):
        dx, dy = C[0] - hands[0], C[1] - hands[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        tip = (hands[0] + ux * 215, hands[1] + uy * 215 - 12 * tipdir)
        mid = (hands[0] + ux * 110, hands[1] + uy * 110 - 4)
        S.line([hands, mid, tip], 5)
        S.line([(hands[0] - ux * 30, hands[1] - uy * 30), hands], 9)
        S.line([(hands[0] + uy * 14, hands[1] - ux * 14), (hands[0] - uy * 14, hands[1] + ux * 14)], 6)

    # Reagan: cowboy hat, suit, lunging in from the left
    o = -push
    S.line([(-175 + o, -150), (-112 + o, -82), (-92 + o, 0)], 27)
    S.line([(-182 + o, -150), (-240 + o, -76), (-282 + o, 0)], 27)
    S.poly([(-204 + o, -176), (-142 + o, -176), (-130 + o, -136), (-214 + o, -136)])
    S.line([(-176 + o, -150), (-160 + o, -265)], 58)
    S.circle((-152 + o, -293), 20)
    S.poly([(-214 + o, -296), (-196 + o, -309), (-150 + o, -313), (-106 + o, -309), (-88 + o, -297),
            (-104 + o, -302), (-150 + o, -305), (-198 + o, -302)])
    S.poly([(-174 + o, -310), (-171 + o, -338), (-153 + o, -333), (-135 + o, -338), (-131 + o, -310)])
    hands_r = (-110 + o, -318)
    S.line([(-162 + o, -255), (-140 + o, -292), hands_r], 17)
    blade(hands_r, 1)
    # the samurai: kabuto with crescent horns, shoulder plates, armored skirt
    o = push
    S.line([(170 + o, -150), (116 + o, -80), (96 + o, 0)], 29)
    S.line([(180 + o, -150), (246 + o, -76), (288 + o, 0)], 29)
    S.poly([(134 + o, -178), (214 + o, -178), (238 + o, -116), (112 + o, -116)])
    S.line([(176 + o, -160), (166 + o, -262)], 66)
    S.poly([(128 + o, -268), (160 + o, -268), (150 + o, -214), (120 + o, -220)])
    S.poly([(190 + o, -266), (224 + o, -262), (232 + o, -208), (198 + o, -212)])
    S.circle((168 + o, -292), 20)
    S.poly([(146 + o, -296), (150 + o, -318), (168 + o, -326), (188 + o, -318), (194 + o, -296)])
    S.poly([(140 + o, -298), (198 + o, -298), (214 + o, -272), (128 + o, -274)])
    S.line([(160 + o, -318), (140 + o, -346), (146 + o, -366)], 6)
    S.line([(170 + o, -320), (188 + o, -350), (180 + o, -370)], 6)
    hands_s = (112 + o, -318)
    S.line([(165 + o, -252), (142 + o, -288), hands_s], 17)
    blade(hands_s, -1)
    S.line([(470, -40), (462, -330)], 6)
    m = S.mask()
    fx.comp_sil(f, m, color=(10, 4, 8), rim=(255, 150, 120), light=(0, -1), rim_px=3, rim_k=0.8)
    fl = fx.wave_flag(int(96 * sc), ts, pole='left', speed=9)
    px, py = S.p(462, -330)
    fx.paste(f, fl, int(px / S.ss), int(py / S.ss - 4))

    # sparks on every clash (each beat)
    k0 = int(ts // beat)
    spx, spy = S.p(*C)
    spx, spy = spx / S.ss, spy / S.ss
    lay = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(max(0, k0 - 1), k0 + 1):
        age = ts - k * beat
        if age < 0:
            continue
        rng = np.random.default_rng(100 + k)
        for i in range(70):
            a = rng.uniform(0, TAU)
            v = rng.uniform(250, 900) * sc
            x = spx + math.cos(a) * v * age
            yv = spy + math.sin(a) * v * age + 900 * sc * age * age
            al = max(0.0, 1 - age / 0.55)
            c = (int(255 * al), int(220 * al), int(120 * al))
            d.line([(x, yv), (x - math.cos(a) * v * 0.025, yv - math.sin(a) * v * 0.025)], fill=c, width=2)
    f += np.asarray(lay, np.float32) * 1.4
    flash = math.exp(-((ts % beat) / 0.06))
    _glint(f, spx, spy, flash, 120 * sc)
    fx.fire(f, spx, spy, 40 * sc, 5.0, seed=k0, strength=flash * 1.2)
    fx.embers(f, ts, n=90, color=(255, 170, 200), vx=-140, vy=50, seed=21, size=3)
    return f


# ---------------------------------------------------------------- simple cards

def flag(ts, dur, W, H, p):
    return fx.flag_fullscreen(W, H, ts + p.get('t0', 0), dark=p.get('dark', 0.0))


def boom(ts, dur, W, H, p):
    f = np.zeros((H, W, 3), np.float32) + np.array([10, 2, 2], np.float32)
    for k, (x, y, r, t0) in enumerate(p.get('booms', [(0.5, 0.62, 330, 0.0)])):
        if ts > t0:
            fx.fire(f, x * W, y * H, r * H / 720, ts - t0, seed=40 + k, rise=1.4)
    fx.embers(f, ts, n=120, vx=0, vy=-300, seed=5)
    return f


def endcard(ts, dur, W, H, p):
    f = fx.flag_fullscreen(W, H, ts, dark=0.62)
    for k, (x, t0) in enumerate([(0.08, 0.0), (0.92, 0.1), (0.3, 0.3), (0.7, 0.4)]):
        if ts > t0:
            fx.fire(f, x * W, H * 1.02, 260 * H / 720, ts - t0, seed=60 + k)
    fx.embers(f, ts, n=200, vx=0, vy=-220, seed=9)
    return f


def slot(ts, dur, W, H, p):
    """Stand-in card for footage that hasn't been downloaded yet."""
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    stripe = ((xs + ys + ts * 400) // (H * 0.08)) % 2
    f = np.zeros((H, W, 3), np.float32) + np.array([18, 22, 40], np.float32)
    f += stripe[..., None] * np.array([10, 10, 18], np.float32)
    col = {'clip': (255, 200, 60), 'photo': (120, 220, 255)}.get(p.get('kind', 'clip'), (255, 200, 60))
    fx.text(f, p.get('label', 'CLIP'), 0.15 * H, cy=0.42, style='plain')
    fx.text(f, p.get('desc', ''), 0.055 * H, cy=0.62, style='mono', name='JetBrainsMono.ttf')
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    tag = 'NEEDS ' + p.get('kind', 'clip').upper()
    fnt = fx.font(0.04 * H, 'JetBrainsMono.ttf')
    d.rectangle([0.04 * W, 0.06 * H, 0.04 * W + fnt.getlength(tag) + 0.03 * H, 0.13 * H], outline=col, width=3)
    d.text((0.04 * W + 0.015 * H, 0.07 * H), tag, font=fnt, fill=col)
    return np.asarray(img, np.float32)


SHOTS = dict(slot=slot, duel=duel, trex=trex, chopper=chopper, datacenter=datacenter, terminal=terminal, flyover=flyover,
             flag=flag, boom=boom, endcard=endcard)
