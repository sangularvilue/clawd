"""The painting session, in MyPaint, stage by stage as at the easel.

  0  toned ground (imprimatura)
  1  drawing transferred in thin umber line
  2  umber underpainting: the values only
  3  colour block-in with big bristle brushes, sky softened wet-in-wet
  4  modelling with medium brushes
  5  the landscape painted in by hand: forest, spruces, village, tree, tracks, thorns
  6  figures finished with small brushes
  7  accents and highlights

Run:  /usr/bin/python3.12 paintit.py <workdir> [first_stage]
Every mark is a MyPaint brush stroke (stock tanda / deevad brush packs).
"""
import sys, math, time
import numpy as np
from mp import Canvas

S = sys.argv[1]
START = int(sys.argv[2]) if len(sys.argv) > 2 else 0
STOP = int(sys.argv[3]) if len(sys.argv) > 3 else 7
W, H = 3840, 2160
SX, SY, YH = 2032.0, 1058.0, 1090.0
G = np.load(S + '/guides.npz')
rng = np.random.default_rng(12)

BRISTLE, BRISTLE2, FLAT, SOFT, ROUND, LINER, PENCIL = ('tanda/oil-01-paint', 'tanda/oil-03-paint', 'tanda/acrylic-04-paint',
                                                        'tanda/oil-06-paint', 'deevad/brush', 'deevad/detail_brush_thin',
                                                        'deevad/2B_pencil')
c = Canvas(W, H)
t0 = time.time()


def log(*a):
    print('[%5.0fs]' % (time.time() - t0), *a, flush=True)


def f32(name):
    return G[name].astype(np.float32) / 255.0


def lay(ref, ang, r, grid, brush, thr=0.05, region=None, lmin=3, lmax=9, jit=0.03, op=None, p=0.8,
        always=False, tol=0.10, detail=None, dpow=1.0, curv=0.3, brush_in=None, inmask=None):
    """One sitting with one brush size: look at the canvas, and wherever it still
    disagrees with the study, mix the colour and lay a stroke along the form."""
    cur = c.array()
    err = np.sqrt(((cur - ref) ** 2).sum(-1))
    del cur
    step = max(r * 0.9, 1.5)
    ny, nx = int(H / grid) + 1, int(W / grid) + 1
    n = 0
    for idx in rng.permutation(ny * nx):
        x = (idx % nx + rng.random()) * grid
        y = (idx // nx + rng.random()) * grid
        ix, iy = int(x), int(y)
        if ix >= W or iy >= H:
            continue
        if region is not None and not region[iy, ix]:
            continue
        if not always:
            th = thr if detail is None else thr / (0.3 + 0.7 * detail[iy, ix]) ** dpow
            if err[iy, ix] < th:
                continue
        col = ref[iy, ix] * (1 + rng.normal(0, jit)) + rng.normal(0, jit * 0.6, 3)
        a = float(ang[iy, ix])
        dx, dy = math.cos(a), math.sin(a)
        if rng.random() < 0.5:
            dx, dy = -dx, -dy
        pts = [(x, y)]
        cx_, cy_ = x, y
        for i in range(1, int(rng.integers(lmin, lmax + 1))):
            cx_ += dx * step; cy_ += dy * step
            jx, jy = int(cx_), int(cy_)
            if jx < 0 or jy < 0 or jx >= W or jy >= H:
                break
            if i > 1 and np.abs(ref[jy, jx] - ref[iy, ix]).sum() > tol * 3:
                break
            pts.append((cx_, cy_))
            a1 = float(ang[jy, jx])
            ndx, ndy = math.cos(a1), math.sin(a1)
            if ndx * dx + ndy * dy < 0:
                ndx, ndy = -ndx, -ndy
            dx, dy = curv * ndx + (1 - curv) * dx, curv * ndy + (1 - curv) * dy
            nn = math.hypot(dx, dy) + 1e-9
            dx, dy = dx / nn, dy / nn
        if len(pts) < 2:
            pts.append((x + dx * step, y + dy * step))
        b = brush
        if brush_in is not None and inmask[iy, ix]:
            b = brush_in
        c.stroke(b, col, pts, r=r * rng.uniform(0.8, 1.2), op=op, p=p * rng.uniform(0.75, 1.0))
        n += 1
    return n


def snap(name):
    c.save(S + '/stage_%s.png' % name)
    log('saved stage', name, '| strokes so far', c.nstrokes)


def wob(pts, amp):
    P = np.asarray(pts, float)
    return P + rng.normal(0, amp, P.shape)


def line(pts, col, r, brush=ROUND, p=0.7, op=None, amp=0.0, taper=0.25):
    c.stroke(brush, col, wob(pts, amp) if amp else pts, r=r, p=p, op=op, taper=taper)


# ------------------------------------------------------------------ stage 0
if START <= 0:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = (np.sin(xx / 310 + 1.3 * np.sin(yy / 270)) * np.sin(yy / 230 + np.sin(xx / 410)) * 0.5 + 0.5)
    g = np.array([0.56, 0.43, 0.31], np.float32)[None, None] * (0.88 + 0.2 * v[..., None])
    c.load(g)
    del yy, xx, v, g
    # scrub the tone in with a wide brush so the ground itself is brushed, not flat
    for i in range(700):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        a = rng.normal(-0.5, 0.5)
        L = rng.uniform(300, 700)
        col = np.array([0.55, 0.42, 0.30]) * rng.uniform(0.86, 1.12)
        c.stroke(BRISTLE, col, [(x, y), (x + L * math.cos(a), y + L * math.sin(a))], r=rng.uniform(60, 90), p=0.6, op=0.5)
    snap('0_ground')
else:
    c.load_png(S + '/stage_%s.png' % {1: '0_ground', 2: '1_drawing', 3: '2_underpainting', 4: '3_blockin', 5: '4_modelling',
                                      6: '5_landscape', 7: '6_figures'}[START])
    log('resumed before stage', START)

# ------------------------------------------------------------------ stage 1: the drawing
if START <= 1:
    umber = (0.23, 0.14, 0.09)
    line([(0, YH), (W, YH)], umber, 1.6, PENCIL, p=0.5)
    for k in ('ridge1', 'ridge2'):
        y = G[k]
        xs = np.arange(0, W, 24)
        line(np.column_stack([xs, y[xs]]), umber, 1.8, PENCIL, p=0.55, amp=1.0)
    # construction: the light fanning from the sun, the fall of the big shadows
    for a in np.linspace(0.15, math.pi - 0.15, 9):
        line([(SX, YH), (SX + 2600 * math.cos(a), YH + 2600 * math.sin(a) * 0.55)], umber, 1.2, PENCIL, p=0.3)
    c.stroke(PENCIL, umber, [(SX + 34 * math.cos(t), SY + 34 * math.sin(t)) for t in np.linspace(0, 6.4, 40)], r=1.6, p=0.6)
    for i in range(int(G['nlines'])):
        l = G['line%d' % i]
        l = np.vstack([l, l[:1]])
        # drawn in searching, overlapping passes like a hand finding the contour
        seg = 60
        for s0 in range(0, len(l) - 1, seg - 8):
            part = l[s0:s0 + seg]
            if len(part) > 1:
                line(part, umber, rng.uniform(1.6, 2.4), PENCIL, p=rng.uniform(0.5, 0.8), amp=0.9)
    # placing the landscape masses
    line([(0, 700), (300, 800), (700, 930), (1100, 1030), (1500, 1088)], umber, 2, PENCIL, p=0.5, amp=3)
    line([(0, 1260), (500, 1200), (1000, 1140), (1500, 1095)], umber, 2, PENCIL, p=0.5, amp=3)
    for (x, yb, h) in [(150, 1840, 1500), (560, 1650, 960), (870, 1570, 380)]:
        line([(x, yb), (x, yb - h)], umber, 2, PENCIL, p=0.5, amp=2)
        line([(x, yb - h), (x - h * 0.2, yb - h * 0.05), (x + h * 0.2, yb - h * 0.05), (x, yb - h)], umber, 2, PENCIL, p=0.45, amp=3)
    line([(3035, 1088), (3035, 1020), (3048, 960), (3061, 1020), (3061, 1088)], umber, 1.6, PENCIL, p=0.6)
    line([(3061, 1052), (3150, 1052), (3150, 1088)], umber, 1.6, PENCIL, p=0.6)
    snap('1_drawing')

# ------------------------------------------------------------------ stage 2: umber underpainting
if START <= 2:
    val = f32('value')
    dark = np.array([0.17, 0.105, 0.07], np.float32); lite = np.array([0.94, 0.87, 0.72], np.float32)
    mono = dark[None, None] + (lite - dark)[None, None] * (val[..., None] ** 1.1)
    n = lay(mono, G['ang60'].astype(np.float32), 58, 46, FLAT, always=True, lmin=4, lmax=9, jit=0.02, op=0.55, p=0.7, tol=0.07)
    n += lay(mono, G['ang30'].astype(np.float32), 26, 24, FLAT, thr=0.07, lmin=3, lmax=8, jit=0.02, op=0.6, p=0.7, tol=0.07)
    log('underpainting strokes', n)
    del mono, val
    snap('2_underpainting')

detail = f32('detail')
maskd = G['maskd'].astype(bool)
fig = G['mask'] > 128

# ------------------------------------------------------------------ stage 3: colour block-in
if START <= 3:
    ref = f32('ref60'); ang = G['ang60'].astype(np.float32)
    n = lay(ref, ang, 54, 40, BRISTLE, always=True, lmin=4, lmax=10, jit=0.035, p=0.85, tol=0.09, curv=0.2)
    log('block-in, largest brush', n)
    ref = f32('ref30'); ang = G['ang30'].astype(np.float32)
    n = lay(ref, ang, 28, 24, BRISTLE, thr=0.045, lmin=4, lmax=10, jit=0.035, p=0.85, tol=0.09, curv=0.25,
            brush_in=FLAT, inmask=maskd)
    log('block-in, second brush', n)
    # sky and far snow brought together wet-in-wet with a soft brush, leaving the bristle marks to show through
    sky = np.zeros((H, W), bool); sky[:int(YH) + 6] = True
    sky &= ~maskd
    n = lay(ref, ang, 34, 30, SOFT, always=True, region=sky, lmin=5, lmax=12, jit=0.02, p=0.7, tol=0.12, curv=0.2)
    snow = np.zeros((H, W), bool); snow[int(YH) + 6:] = True
    snow &= ~maskd
    n += lay(ref, ang, 30, 40, SOFT, always=True, region=snow, lmin=5, lmax=12, jit=0.02, p=0.6, tol=0.12, curv=0.2)
    log('blending', n)
    snap('3_blockin')

# ------------------------------------------------------------------ stage 4: modelling
if START <= 4 and STOP >= 4:
    ref = f32('ref15'); ang = G['ang15'].astype(np.float32)
    n = lay(ref, ang, 14, 13, BRISTLE2, thr=0.045, lmin=3, lmax=10, jit=0.03, p=0.85, tol=0.08, detail=detail, dpow=0.8,
            brush_in=FLAT, inmask=maskd)
    log('modelling 14px', n)
    ref = f32('ref8'); ang = G['ang8'].astype(np.float32)
    n = lay(ref, ang, 7.5, 7, BRISTLE2, thr=0.05, lmin=3, lmax=10, jit=0.028, p=0.85, tol=0.08, detail=detail, dpow=1.3,
            brush_in=ROUND, inmask=maskd)
    log('modelling 7px', n)
    snap('4_modelling')


# ------------------------------------------------------------------ stage 5: landscape by hand
def spruce(x, yb, h, dark=(0.045, 0.062, 0.075), snow=(0.36, 0.42, 0.60), warm=(0.78, 0.62, 0.60), snowy=0.75, sun=1):
    line([(x, yb), (x + rng.normal(0, h * 0.004), yb - h * 0.55), (x, yb - h * 0.97)], np.array(dark) * 0.8,
         max(h * 0.011, 1.5), ROUND, p=0.8)
    tiers = int(9 + h / 34)
    for i in range(tiers):
        t = (i + 0.5) / tiers
        y = yb - h * (1 - t) * 0.97 - h * 0.02
        hw = (h * 0.235 * t ** 0.85 + h * 0.012) * rng.uniform(0.8, 1.15)
        rr = max(h * 0.016 * (0.45 + t), 2.0)
        for sd in (-1, 1):
            for j in range(int(rng.integers(2, 4))):
                ex = x + sd * hw * rng.uniform(0.55, 1.05)
                ey = y + hw * rng.uniform(0.22, 0.48)
                mx, my = (x + ex) / 2 + rng.normal(0, hw * 0.05), (y + ey) / 2 - hw * rng.uniform(0.02, 0.12)
                col = np.array(dark) * rng.uniform(0.7, 1.5) + rng.normal(0, 0.006, 3)
                c.stroke(BRISTLE2, col, [(x + sd * rr * 0.3, y - rr), (mx, my), (ex, ey)], r=rr * rng.uniform(0.8, 1.3),
                         p=rng.uniform(0.7, 0.95), taper=0.3)
                if rng.random() < snowy * (0.35 + 0.5 * t):
                    f0, f1 = rng.uniform(0.15, 0.35), rng.uniform(0.6, 0.92)
                    a = (x + (mx - x) * 2 * f0, y + (my - y) * 2 * f0 - rr * 1.1) if f0 < 0.5 else (mx, my - rr)
                    b = (mx + (ex - mx) * (f1 - 0.5) * 2, my + (ey - my) * (f1 - 0.5) * 2 - rr * 0.9)
                    sc_ = np.array(warm if (sd == sun and rng.random() < 0.35) else snow) * rng.uniform(0.85, 1.12)
                    c.stroke(FLAT, sc_, [a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - rr * 0.3), b], r=rr * rng.uniform(0.5, 0.8),
                             p=rng.uniform(0.6, 0.9), taper=0.35)


def small_spruce(x, yb, h, dark, snow=None):
    c.stroke(BRISTLE2, dark, [(x, yb - h), (x + rng.normal(0, 1), yb - h * 0.5), (x, yb)], r=max(h * 0.12, 1.6),
             p=0.9, taper=0.02, step=1.5)
    for sd in (-1, 1):
        for q in (0.35, 0.6, 0.85):
            c.stroke(BRISTLE2, dark, [(x, yb - h * (1 - q)), (x + sd * h * 0.2 * q, yb - h * (1 - q) + h * 0.09)],
                     r=max(h * 0.06, 1.4), p=0.8)
    if snow is not None and h > 30:
        for q in (0.3, 0.55, 0.8):
            sd = rng.choice([-1, 1])
            c.stroke(FLAT, snow, [(x, yb - h * (1 - q) - 2), (x + sd * h * 0.14 * q, yb - h * (1 - q) + h * 0.03)],
                     r=max(h * 0.03, 1.2), p=0.6)


if START <= 5 and STOP >= 5:
    # the dark wooded hill to the left: the country he has come out of
    top = lambda x: 700 + 392 * min(max(x / 1560.0, 0), 1) ** 0.85
    low = lambda x: 1262 - 170 * min(max(x / 1560.0, 0), 1)
    for i in range(1500):
        x = rng.uniform(-40, 1560)
        y = rng.uniform(top(x) + 25, low(x))
        dep = (y - top(x)) / max(low(x) - top(x), 1)
        col = np.array([0.075, 0.095, 0.14]) * rng.uniform(0.7, 1.35) + np.array([0.05, 0.05, 0.08]) * (1 - dep) * (x / 1560)
        a = rng.normal(1.2, 0.35)
        L = rng.uniform(30, 90)
        c.stroke(BRISTLE, col, [(x, y), (x + L * math.cos(a) * 0.4, y + L * math.sin(a))], r=rng.uniform(14, 26), p=0.85)
    trees = []
    for i in range(620):
        x = rng.uniform(-30, 1600)
        t = rng.random() ** 0.7
        y = top(x) + 30 + t * (low(x) - top(x) - 18)
        s = (30 + 210 * (1 - min(max(x, 0), 1560) / 1560.0) ** 1.5) * rng.uniform(0.7, 1.25) * (0.5 + 0.55 * t)
        trees.append((y, x, s))
    for (y, x, s) in sorted(trees):
        dep = min(max((y - 720) / 560.0, 0), 1)
        far = min(max(x / 1560.0, 0), 1)
        dark = np.array([0.055, 0.075, 0.10]) * (0.8 + 0.5 * rng.random()) + np.array([0.10, 0.10, 0.16]) * far * (1 - dep * 0.5)
        small_spruce(x, y, s, dark, snow=np.array([0.34, 0.39, 0.56]) * rng.uniform(0.85, 1.1) if rng.random() < 0.5 else None)
    # mist lying at the foot of the wood
    for i in range(160):
        x = rng.uniform(0, 1700)
        y = low(x) + rng.normal(4, 9)
        c.stroke(SOFT, np.array([0.50, 0.52, 0.70]) * rng.uniform(0.9, 1.1), [(x, y), (x + rng.uniform(90, 240), y + rng.normal(-8, 5))],
                 r=rng.uniform(10, 22), p=0.45, op=0.35)
    log('forest done')
    # scattered firs out on the plain
    for (x, yb, h) in [(1700, 1118, 54), (1790, 1128, 76), (2600, 1150, 118), (2668, 1166, 150), (3340, 1196, 188),
                       (3432, 1180, 120), (3742, 1236, 250), (2470, 1124, 58)]:
        spruce(x, yb, h, dark=(0.11, 0.13, 0.22), snow=(0.50, 0.52, 0.72), warm=(0.95, 0.74, 0.60), sun=-1 if x > SX else 1)
        c.stroke(SOFT, (0.40, 0.44, 0.66), [(x, yb + 3), (x + (x - SX) * 0.35 * h / 150, yb + 3 + h * 0.5)], r=h * 0.06, p=0.5, op=0.5)
    # the village and its church, lamps lit, at the end of the plain
    vb = (0.21, 0.21, 0.34)
    for i in range(70):
        x = rng.uniform(2700, 3840); y = rng.uniform(1078, 1098)
        s = rng.uniform(7, 20)
        c.stroke(BRISTLE2, np.array([0.17, 0.18, 0.30]) * rng.uniform(0.8, 1.2), [(x, y), (x + rng.normal(0, 3), y - s)], r=s * 0.45, p=0.8)
    for (hx, hw) in [(2952, 44), (3176, 50), (3244, 36), (2892, 32), (3306, 40), (3110, 30)]:
        hy = 1092
        line([(hx, hy - 9), (hx + hw, hy - 9)], vb, 9, FLAT, p=0.9)
        line([(hx - 3, hy - 18), (hx + hw / 2, hy - 31), (hx + hw + 3, hy - 18)], (0.60, 0.59, 0.76), 3.2, ROUND, p=0.8)
        line([(hx - 2, hy - 19), (hx + hw / 2, hy - 32)], (0.99, 0.80, 0.64), 2.2, ROUND, p=0.8)
        line([(hx + hw * 0.6, hy - 9), (hx + hw * 0.6 + 4, hy - 9)], (1.0, 0.72, 0.25), 2.6, ROUND, p=0.9)
    line([(3058, 1077), (3148, 1077)], vb, 17, FLAT, p=0.95)                         # nave
    line([(3048, 1090), (3048, 1026)], vb, 13, FLAT, p=0.95)                         # tower
    line([(3036, 1028), (3048, 962), (3060, 1028)], vb, 4.5, ROUND, p=0.9)
    line([(3048, 1022), (3048, 968)], vb, 5.5, ROUND, p=0.9)
    line([(3048, 964), (3048, 942)], vb, 1.6, ROUND, p=0.9)
    line([(3041, 950), (3055, 950)], vb, 1.5, ROUND, p=0.9)
    line([(3052, 1060), (3100, 1034), (3152, 1060)], (0.58, 0.58, 0.76), 4.2, ROUND, p=0.85)
    line([(3052, 1059), (3100, 1033)], (0.99, 0.80, 0.64), 3.0, ROUND, p=0.85)
    line([(3037, 1026), (3047, 966)], (0.99, 0.80, 0.64), 2.2, ROUND, p=0.8)
    for wx in (3070, 3090, 3110, 3130):
        line([(wx, 1072), (wx, 1085)], (1.0, 0.74, 0.26), 2.8, ROUND, p=0.95, taper=0.05)
    line([(3048, 1042), (3048, 1052)], (1.0, 0.74, 0.26), 2.4, ROUND, p=0.95, taper=0.05)
    for i in range(14):
        t = i / 13
        c.stroke(SOFT, np.array([0.93, 0.74, 0.70]), [(3190 + 140 * t ** 1.5 + rng.normal(0, 4), 1066 - 160 * t),
                                                      (3200 + 150 * (t + 0.1) ** 1.5, 1066 - 160 * (t + 0.1))],
                 r=4 + 22 * t, p=0.5, op=0.3)
    log('village done')
    # the bare tree on the right, drawn with a long-haired rigger
    def branch(x, y, a, ln, w, depth):
        if depth == 0 or w < 0.8:
            return
        pts = [(x, y)]
        for i in range(4):
            a += rng.normal(0, 0.09)
            x += math.cos(a) * ln / 4; y += math.sin(a) * ln / 4
            pts.append((x, y))
        c.stroke(ROUND, np.array([0.085, 0.07, 0.095]) * rng.uniform(0.8, 1.3), pts, r=w, p=0.9, taper=0.08)
        if w > 3:   # the dawn catching the left side of the limbs
            c.stroke(ROUND, (1.0, 0.76, 0.52), [(px - w * 0.55, py - 1) for (px, py) in pts], r=max(w * 0.16, 1.0), p=0.7, op=0.8)
        for i in range(2 if rng.random() < 0.55 else 3):
            na = a + rng.normal(0, 0.30) + (0.36 if i == 0 else (-0.36 if i == 1 else 0.0))
            na = na * 0.74 + (-math.pi / 2 - 0.08) * 0.26
            branch(x, y, na, ln * rng.uniform(0.62, 0.84), w * rng.uniform(0.52, 0.66), depth - 1)
    branch(3580, 1668, -math.pi / 2 - 0.02, 310, 32, 10)
    for i in range(30):
        c.stroke(FLAT, np.array([0.60, 0.64, 0.84]) * rng.uniform(0.9, 1.1), [(3580 + rng.normal(0, 60), 1672 + rng.normal(0, 5)),
                                                                          (3580 + rng.normal(0, 90), 1676 + rng.normal(0, 6))], r=rng.uniform(5, 11), p=0.7)
    log('tree done')
    # the great snow-laden spruces of the foreground left
    spruce(-70, 1960, 1750)
    spruce(870, 1575, 400)
    spruce(560, 1655, 980)
    spruce(150, 1850, 1560)
    for (x, y, w_) in [(150, 1850, 300), (560, 1655, 210), (870, 1575, 90)]:    # drifts at their feet
        for i in range(26):
            c.stroke(FLAT, np.array([0.40, 0.45, 0.68]) * rng.uniform(0.88, 1.12),
                     [(x + rng.normal(0, w_ * 0.4), y + rng.normal(4, 5)), (x + rng.normal(0, w_ * 0.5), y + rng.normal(10, 6))],
                     r=rng.uniform(7, 16), p=0.7)
    log('spruces done')
    # his tracks: stumbling in from the thorns at the corner to where the cloak fell
    path = np.array([(250, 2210), (440, 2075), (590, 1975), (740, 1880), (860, 1790), (940, 1722), (985, 1682)], float)
    tt = np.linspace(0, len(path) - 1, 300)
    xs = np.interp(tt, np.arange(len(path)), path[:, 0]); ys = np.interp(tt, np.arange(len(path)), path[:, 1])
    cum = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    s_, side = 20.0, 1
    while s_ < cum[-1] - 8:
        i = min(int(np.searchsorted(cum, s_)), len(xs) - 2)
        x, y = xs[i], ys[i]
        dx, dy = xs[i + 1] - xs[i], ys[i + 1] - ys[i]
        Ln = math.hypot(dx, dy); dx, dy = dx / Ln, dy / Ln
        scl = 0.18 + 0.9 * (y - YH) / (H - YH)
        ln = 96 * scl
        px, py = x - dy * side * ln * 0.42 + rng.normal(0, 3) * scl, y + dx * side * ln * 0.22
        a = math.atan2(dy * 0.5, dx) + rng.normal(0, 0.18)
        ca, sa = math.cos(a), math.sin(a)
        c.stroke(FLAT, (0.15, 0.18, 0.36), [(px - ca * ln * 0.36, py - sa * ln * 0.36), (px + ca * ln * 0.36, py + sa * ln * 0.36)],
                 r=ln * 0.17, p=0.95, taper=0.12)
        c.stroke(SOFT, (0.10, 0.12, 0.27), [(px - ca * ln * 0.25, py - sa * ln * 0.25 - ln * 0.05), (px + ca * ln * 0.25, py + sa * ln * 0.25 - ln * 0.05)],
                 r=ln * 0.09, p=0.7)
        c.stroke(ROUND, (0.80, 0.76, 0.90), [(px - ca * ln * 0.42, py - sa * ln * 0.42 + ln * 0.15), (px, py + ln * 0.23),
                                             (px + ca * ln * 0.42, py + sa * ln * 0.42 + ln * 0.13)], r=max(ln * 0.035, 1.3), p=0.6, op=0.8)
        s_ += ln * rng.uniform(0.95, 1.25)
        side = -side
    # a broken fetter left lying in them
    x, y = 705, 1930
    for i in range(9):
        a = rng.uniform(-0.5, 0.5)
        pts = [(x + 13 * math.cos(t) * math.cos(a) - 6 * math.sin(t) * math.sin(a), y + 13 * math.cos(t) * math.sin(a) + 6 * math.sin(t) * math.cos(a))
               for t in np.linspace(0, 6.3 if i < 8 else 4.2, 14)]
        c.stroke(ROUND, (0.09, 0.08, 0.11), pts, r=2.4, p=0.9, taper=0.05)
        c.stroke(ROUND, (0.95, 0.76, 0.56), [(px - 1.5, py - 2) for (px, py) in pts[6:11]], r=1.0, p=0.7)
        x -= 20 + rng.normal(0, 2); y += 8 + rng.normal(0, 3)
    # thorns in the near corner, with a few hips red as drops of blood
    for i in range(30):
        x0 = rng.uniform(-60, 640); y0 = 2190
        hg = rng.uniform(170, 540) * (1 - x0 / 1300); lean = rng.uniform(-150, 320)
        ts = np.linspace(0, 1, 16)
        p1, p2, p3 = (x0 + lean * 0.2, y0 - hg * 0.7), (x0 + lean * 0.7, y0 - hg * 1.05), (x0 + lean * 1.25, y0 - hg * rng.uniform(0.45, 0.9))
        bez = [((1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
                (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1]) for t in ts]
        wdt = rng.uniform(2.2, 4.6)
        c.stroke(ROUND, np.array([0.085, 0.06, 0.085]) * rng.uniform(0.8, 1.4), bez, r=wdt, p=0.9, taper=0.5)
        c.stroke(ROUND, (0.86, 0.60, 0.46), [(px + 1.5, py - 1.5) for (px, py) in bez[4:13]], r=1.0, p=0.55, op=0.7)
        for j in range(9):
            bx, by = bez[int(rng.integers(2, 16))]
            a = rng.uniform(0, 6.28)
            c.stroke(ROUND, (0.08, 0.06, 0.08), [(bx, by), (bx + 12 * math.cos(a), by + 12 * math.sin(a))], r=1.3, p=0.8, taper=0.6)
        for j in range(2):
            bx, by = bez[int(rng.integers(5, 16))]
            c.stroke(FLAT, np.array([0.58, 0.64, 0.86]) * rng.uniform(0.9, 1.1), [(bx - wdt * 2.2, by - wdt), (bx + wdt * 2.2, by - wdt * 1.2)], r=wdt * 0.9, p=0.8)
        if rng.random() < 0.6:
            bx, by = bez[int(rng.integers(10, 16))]
            c.stroke(ROUND, (0.66, 0.05, 0.045), [(bx + 4, by + 6), (bx + 6, by + 10)], r=5.5, p=0.95, taper=0.01)
            c.stroke(ROUND, (1.0, 0.55, 0.36), [(bx + 5, by + 5), (bx + 6, by + 6)], r=1.5, p=0.9, taper=0.01)
    log('tracks and thorns done')
    snap('5_landscape')

# ------------------------------------------------------------------ stage 6: figures finished
if START <= 6 and STOP >= 6:
    reg = maskd
    ref = f32('ref4'); ang = G['ang4'].astype(np.float32)
    n = lay(ref, ang, 3.8, 3.6, ROUND, thr=0.045, region=reg, lmin=3, lmax=10, jit=0.02, p=0.85, tol=0.07, curv=0.4)
    log('figures 4px', n)
    ref = f32('ref2'); ang = G['ang2'].astype(np.float32)
    n = lay(ref, ang, 2.1, 2.2, ROUND, thr=0.06, region=reg, lmin=3, lmax=9, jit=0.015, p=0.85, tol=0.07, curv=0.4)
    log('figures 2px', n)
    snap('6_figures')

# ------------------------------------------------------------------ stage 7: accents
if START <= 7 and STOP >= 7:
    # the sun itself, loaded lead-white with a breath of yellow
    for i in range(46):
        a = rng.uniform(0, 6.28); d = rng.uniform(0, 26)
        c.stroke(FLAT, (1.0, 0.99, 0.90), [(SX + d * math.cos(a), SY + d * math.sin(a)), (SX + d * math.cos(a) + rng.normal(0, 9), SY + d * math.sin(a) + rng.normal(0, 5))],
                 r=rng.uniform(6, 11), p=0.95)
    # the shaft of light between them laid broken on the snow, and sparkle along the drift crests
    for i in range(260):
        t = rng.random() ** 0.8
        y = 1675 + t * 470
        x = SX + (y - YH) * rng.normal(0.0, 0.035) + rng.normal(0, 14)
        c.stroke(FLAT, np.array([1.0, 0.90, 0.72]) * rng.uniform(0.92, 1.0), [(x, y), (x + rng.uniform(14, 60) * (0.5 + t), y + rng.normal(0, 2))],
                 r=rng.uniform(2.5, 6) * (0.6 + t), p=0.8, op=0.75)
    for i in range(500):
        x = SX + rng.normal(0, 520); y = YH + 8 + abs(rng.normal(0, 190))
        c.stroke(ROUND, (1.0, 0.95, 0.80), [(x, y), (x + rng.uniform(4, 18), y + rng.normal(0, 1))], r=rng.uniform(1.2, 2.6), p=0.8)
    # morning star
    c.stroke(ROUND, (1.0, 0.98, 0.92), [(3184, 318), (3186, 319)], r=4.0, p=1.0, taper=0.01)
    c.stroke(ROUND, (1.0, 0.98, 0.92), [(3174, 318), (3196, 318)], r=1.1, p=0.6)
    c.stroke(ROUND, (1.0, 0.98, 0.92), [(3185, 308), (3185, 328)], r=1.1, p=0.6)
    # gold of the stole: fringe and a small embroidered cross
    P3 = lambda X, Y, Z: (2000 + 4200 * X / (7.0 - Z), 1090 - 4200 * (Y - 0.95) / (7.0 - Z))
    gold = (0.97, 0.78, 0.34)
    for zz in (0.1275,):
        x, y = P3(0.095, 0.21, zz)
        for i in range(9):
            c.stroke(ROUND, gold, [(x - 30 + i * 7.5, y + 6), (x - 31 + i * 7.5, y + 24)], r=1.6, p=0.9, taper=0.1)
        cx_, cy_ = P3(0.10, 0.345, zz)
        c.stroke(ROUND, gold, [(cx_, cy_ - 20), (cx_, cy_ + 22)], r=2.3, p=0.9, taper=0.1)
        c.stroke(ROUND, gold, [(cx_ - 13, cy_ - 6), (cx_ + 13, cy_ - 6)], r=2.3, p=0.9, taper=0.1)
    # a tear taking the light on the penitent's cheek
    tx, ty = P3(0.035, 0.955, 0.06)
    c.stroke(ROUND, (1.0, 0.93, 0.78), [(tx - 1, ty - 9), (tx, ty)], r=1.2, p=0.7)
    c.stroke(ROUND, (1.0, 0.97, 0.88), [(tx, ty), (tx + 1, ty + 1)], r=2.4, p=1.0, taper=0.01)
    # new snow lying on shoulders, hair, the scarlet cloak where it trails
    for (X0, Y0, X1, Y1, Z, n_, sp) in [(0.44, 1.215, 0.66, 0.99, 0.2, 60, 0.022), (-0.30, 1.03, -0.52, 0.86, 0.22, 44, 0.022),
                                         (-0.10, 1.115, -0.02, 1.10, 0.05, 10, 0.012), (-1.05, 0.11, -1.72, 0.09, 0.2, 240, 0.07)]:
        for i in range(n_):
            t = rng.random()
            x, y = P3(X0 + (X1 - X0) * t + rng.normal(0, sp), Y0 + (Y1 - Y0) * t + rng.normal(0, sp * 0.5), Z + rng.normal(0, 0.12))
            c.stroke(FLAT, np.array([0.80, 0.84, 0.98]) * rng.uniform(0.9, 1.03), [(x, y), (x + rng.uniform(2, 9), y + rng.normal(0, 1.5))],
                     r=rng.uniform(1.6, 4.2), p=0.85)
    # last flakes of the departing storm, flicked on over the dark wood
    for i in range(900):
        x = abs(rng.normal(0, 900)); y = rng.uniform(0, H)
        if x > W or rng.random() > 0.25 + 0.75 * math.exp(-x / 700):
            continue
        r_ = 1.2 + 3.0 * rng.random() ** 3
        c.stroke(ROUND, (0.92, 0.94, 1.0), [(x, y), (x + r_ * 0.8, y + r_ * 1.6)], r=r_, p=rng.uniform(0.4, 0.85), op=0.8, taper=0.05)
    snap('7_final')
log('finished:', c.nstrokes, 'brush strokes')
