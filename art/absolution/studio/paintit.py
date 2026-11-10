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
POINT = 'deevad/brush#fixed'
c = Canvas(W, H)
c.record(S + '/tl_%d.mp4' % START)      # one film segment per sitting
t0 = time.time()


def log(*a):
    print('[%5.0fs]' % (time.time() - t0), *a, flush=True)


def f32(name):
    return G[name].astype(np.float32) / 255.0


def lay(ref, ang, r, grid, brush, thr=0.05, region=None, lmin=3, lmax=9, jit=0.03, op=None, p=0.8,
        always=False, tol=0.10, detail=None, dpow=1.0, curv=0.3, brush_in=None, inmask=None, taper=0.25):
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
            if i > 2 and np.abs(ref[jy, jx] - ref[iy, ix]).sum() > tol * 3:
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
        c.stroke(b, col, pts, r=r * rng.uniform(0.8, 1.2), op=op, p=p * rng.uniform(0.75, 1.0), taper=taper)
        n += 1
    return n


def snap(name):
    c.save(S + '/stage_%s.png' % name)
    log('saved stage', name, '| strokes so far', c.nstrokes)


def wob(pts, amp):
    P = np.asarray(pts, float)
    return P + rng.normal(0, amp, P.shape)


def line(pts, col, r, brush=ROUND, p=0.7, op=None, amp=0.0, taper=0.25):
    if brush == ROUND and r < 6:
        brush = POINT       # small exact marks want a firm point
    c.stroke(brush, col, wob(pts, amp) if amp else pts, r=r, p=p, op=op, taper=taper)


# ------------------------------------------------------------------ stage 0
if START <= 0:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = (np.sin(xx / 310 + 1.3 * np.sin(yy / 270)) * np.sin(yy / 230 + np.sin(xx / 410)) * 0.5 + 0.5)
    g = np.array([0.56, 0.43, 0.31], np.float32)[None, None] * (0.88 + 0.2 * v[..., None])
    c.load(g)
    del yy, xx, v, g
    c.frame_every = 30
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
    c.frame_every = 1
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
    xs = np.arange(0, W, 24)
    line(np.column_stack([xs, G['ridge3'][xs]]), umber, 1.8, PENCIL, p=0.55, amp=1.0)
    line([(0, 1005), (500, 1062), (900, 1124), (1250, 1196), (1480, 1262), (1600, 1320)], umber, 2, PENCIL, p=0.5, amp=2)
    line([(2640, 1440), (2850, 1384), (3150, 1322), (3500, 1262), (3840, 1215)], umber, 2, PENCIL, p=0.5, amp=2)
    line([(628, 1745), (668, 1330), (728, 790)], umber, 2.2, PENCIL, p=0.6, amp=2)
    line([(3640, 1860), (3640, 860), (3440, 1800), (3840, 1800)], umber, 2, PENCIL, p=0.45, amp=3)
    snap('1_drawing')

# ------------------------------------------------------------------ stage 2: umber underpainting
if START <= 2:
    val = f32('value')
    dark = np.array([0.17, 0.105, 0.07], np.float32); lite = np.array([0.94, 0.87, 0.72], np.float32)
    mono = dark[None, None] + (lite - dark)[None, None] * (val[..., None] ** 1.1)
    # first the big blots: only the three or four great masses of light and dark
    c.frame_every = 5
    n = lay(mono, G['ang60'].astype(np.float32), 130, 150, FLAT, always=True, lmin=3, lmax=6, jit=0.03, op=0.6, p=0.75, tol=0.2)
    c.frame_every = 12
    n += lay(mono, G['ang60'].astype(np.float32), 80, 80, FLAT, thr=0.05, lmin=3, lmax=7, jit=0.025, op=0.6, p=0.7, tol=0.12)
    c.frame_every = 40
    n += lay(mono, G['ang60'].astype(np.float32), 44, 44, FLAT, thr=0.07, lmin=3, lmax=8, jit=0.02, op=0.6, p=0.7, tol=0.08)
    log('underpainting strokes', n)
    del mono, val
    snap('2_underpainting')

detail = f32('detail')
maskd = G['maskd'].astype(bool)
fig = G['mask'] > 128

# ------------------------------------------------------------------ stage 3: colour block-in
if START <= 3 and STOP >= 3:
    ref = f32('ref60'); ang = G['ang60'].astype(np.float32)
    c.frame_every = 6
    n = lay(ref, ang, 120, 120, BRISTLE, always=True, lmin=3, lmax=7, jit=0.04, p=0.85, tol=0.2, curv=0.2)
    log('colour blots', n)
    c.frame_every = 50
    n = lay(ref, ang, 54, 44, BRISTLE, thr=0.04, lmin=4, lmax=10, jit=0.035, p=0.85, tol=0.09, curv=0.2)
    log('block-in, largest brush', n)
    ref = f32('ref30'); ang = G['ang30'].astype(np.float32)
    c.frame_every = 130
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
    c.frame_every = 300
    n = lay(ref, ang, 14, 13, BRISTLE2, thr=0.045, lmin=3, lmax=10, jit=0.03, p=0.85, tol=0.08, detail=detail, dpow=0.8,
            brush_in=POINT, inmask=maskd)
    log('modelling 14px', n)
    ref = f32('ref8'); ang = G['ang8'].astype(np.float32)
    c.frame_every = 500
    n = lay(ref, ang, 7.5, 7, POINT, thr=0.05, lmin=3, lmax=10, jit=0.025, p=0.85, tol=0.08, detail=detail, dpow=1.0)
    log('modelling 7px', n)
    # the distance drawn tightly, as the Hudson River painters finished theirs
    far = (np.arange(H)[:, None] < G['ridge3'][None, :]) & ~maskd
    ref = f32('ref4'); ang = G['ang4'].astype(np.float32)
    c.frame_every = 900
    n = lay(ref, ang, 4.2, 4.0, POINT, thr=0.04, region=far, lmin=3, lmax=10, jit=0.02, p=0.85, tol=0.07, curv=0.4, taper=0.15)
    log('distance 4px', n)
    land_ = far & (np.arange(H)[:, None] > G['ridge2'][None, :] - 6)
    ref = f32('ref2'); ang = G['ang2'].astype(np.float32)
    c.frame_every = 1500
    n = lay(ref, ang, 2.4, 2.4, POINT, thr=0.045, region=land_, lmin=3, lmax=9, jit=0.015, p=0.85, tol=0.07, curv=0.4, taper=0.15)
    log('distance 2px', n)
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
    c.frame_every = 60
    ED = G['ridge3']; ref8 = f32('ref8')
    FO = G['forest']; DP = G['depth'].astype(np.float32)
    # cloud still clinging round the great peak on the left
    for i in range(150):
        x = rng.uniform(120, 1250); y = 170 + rng.normal(60, 50) + (x - 650) ** 2 / 9000.0
        under = rng.random() < 0.3 and x > 600
        col = (np.array([0.86, 0.60, 0.58]) if under else np.array([0.27, 0.26, 0.38])) * rng.uniform(0.85, 1.15)
        c.stroke(SOFT, col, [(x, y + (16 if under else 0)), (x + rng.uniform(120, 340), y + rng.normal(0, 14) + (16 if under else 0))],
                 r=rng.uniform(16, 40), p=0.55, op=0.4)
    # the forests, tree by tree, far to near: size set by how far off they stand
    ys, xs = np.where((FO > 90) & (DP > 0.3) & (DP < 9.5))
    sel = rng.choice(len(ys), min(5600, len(ys)), replace=False)
    items = sorted([(-float(DP[ys[i], xs[i]]), xs[i] * 2 + rng.uniform(0, 2), ys[i] * 2 + rng.uniform(0, 2)) for i in sel])
    for (nd, x, y) in items:
        hpx = min(max(0.030 * 4200 / -nd, 7), 170) * rng.uniform(0.7, 1.25)
        if y + hpx * 0.3 > float(ED[int(min(x, W - 1))]) + 4 or maskd[int(min(y, H - 1)), int(min(x, W - 1))]:
            continue
        base = ref8[min(int(y), H - 1), min(int(x), W - 1)]
        dark = base * 0.42 * rng.uniform(0.7, 1.2) + np.array([0.015, 0.025, 0.03])
        sn = base * 0.45 + np.array([0.36, 0.40, 0.56]) * 0.6
        small_spruce(x, y + hpx * 0.3, hpx, dark, snow=sn if rng.random() < 0.5 else None)
    log('forests done')
    # rock breaking through the snow along the lip of the ledge
    for i in range(70):
        x = rng.uniform(0, W)
        if 1250 < x < 2850:
            continue
        y = float(ED[int(x)]) + rng.uniform(-4, 26)
        wd = rng.uniform(26, 90)
        c.stroke(BRISTLE2, np.array([0.11, 0.11, 0.17]) * rng.uniform(0.8, 1.3), [(x - wd / 2, y + rng.normal(0, 3)), (x + wd / 2, y + rng.normal(0, 3))], r=rng.uniform(7, 15), p=0.85)
        c.stroke(FLAT, np.array([0.50, 0.54, 0.76]) * rng.uniform(0.9, 1.1), [(x - wd * 0.45, y - 9), (x + wd * 0.45, y - 10)], r=rng.uniform(4, 8), p=0.8)
        if rng.random() < 0.5:
            sgn = 1 if x < SX else -1
            c.stroke(ROUND, (1.0, 0.84, 0.68), [(x + sgn * wd * 0.1, y - 14), (x + sgn * wd * 0.45, y - 12)], r=1.8, p=0.7)
    c.xf = (0.42, 3048.0, 1090.0, 2770.0, 1150.0)
    # the village and its church, lamps lit, at the end of the plain
    vb = (0.21, 0.21, 0.34)
    for i in range(24):
        x = rng.uniform(2800, 3300); y = rng.uniform(1078, 1098)
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
    c.xf = None
    # the blasted tree: dead wood on the side he has come from
    tr = [(628, 1745), (636, 1600), (660, 1420), (668, 1250), (700, 1080), (706, 930), (735, 800)]
    for j in range(9):
        wv = [(x + (j - 4) * 7.5 * (1 - 0.55 * i / 6.0) + rng.normal(0, 4), y + rng.normal(0, 8)) for i, (x, y) in enumerate(tr)]
        c.stroke(BRISTLE2, np.array([0.085, 0.07, 0.075]) * rng.uniform(0.7, 1.5) + (0.03 if j > 5 else 0.0), wv, r=rng.uniform(14, 22), p=0.9, taper=0.05)
    for (x0, y0, dx, dy) in [(738, 800, 26, -95), (728, 806, -20, -50), (722, 835, 12, -44)]:      # splintered top
        c.stroke(ROUND, (0.075, 0.062, 0.07), [(x0, y0), (x0 + dx * 0.4 + rng.normal(0, 3), y0 + dy * 0.5), (x0 + dx, y0 + dy)], r=8, p=0.9, taper=0.7)
    for (t, sd, ln, up) in [(0.52, 1, 300, 0.45), (0.66, -1, 230, 0.6), (0.80, 1, 150, 0.35), (0.40, -1, 150, 0.2)]:
        i = t * (len(tr) - 1); k_ = int(i); f = i - k_
        x = tr[k_][0] + (tr[k_ + 1][0] - tr[k_][0]) * f; y = tr[k_][1] + (tr[k_ + 1][1] - tr[k_][1]) * f
        pts = [(x, y)]
        a_ = -up
        for q in range(6):
            x += sd * ln / 6 * math.cos(a_); y += ln / 6 * math.sin(a_)
            a_ += rng.normal(-0.02, 0.32)
            pts.append((x, y))
        c.stroke(ROUND, (0.075, 0.062, 0.075), pts, r=10, p=0.9, taper=0.8)
        c.stroke(FLAT, (0.44, 0.48, 0.70), [(px, py - 7) for (px, py) in pts[1:4]], r=3.5, p=0.7, taper=0.4)
        for q in (2, 4):
            c.stroke(ROUND, (0.075, 0.062, 0.075), [pts[q], (pts[q][0] + sd * rng.uniform(20, 50), pts[q][1] - rng.uniform(40, 90))], r=3.5, p=0.85, taper=0.8)
    for k_ in range(len(tr) - 1):        # the dawn just touching its sunward edge, broken
        if rng.random() < 0.75:
            (xa, ya), (xb, yb) = tr[k_], tr[k_ + 1]
            f0, f1 = sorted(rng.uniform(0, 1, 2))
            off = 26 * (1 - 0.55 * k_ / 6.0)
            c.stroke(ROUND, (0.95, 0.68, 0.50), [(xa + (xb - xa) * f0 + off, ya + (yb - ya) * f0), (xa + (xb - xa) * f1 + off, ya + (yb - ya) * f1)], r=1.8, p=0.6, op=0.7)
    # and living evergreens on the side of the light
    spruce(3330, 1730, 440, dark=(0.06, 0.085, 0.085), warm=(0.98, 0.78, 0.62), sun=-1)
    spruce(3640, 1860, 1000, dark=(0.05, 0.075, 0.075), warm=(0.98, 0.78, 0.62), sun=-1)
    log('trees done')
    # the great snow-laden spruces of the foreground left
    spruce(-90, 1990, 1500)
    spruce(190, 1870, 1180)
    for (x, y, w_) in [(190, 1870, 260), (628, 1745, 120), (3640, 1860, 230), (3330, 1730, 110)]:    # drifts at their feet
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
        ln = 150 * scl
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
    c.frame_every = 450
    ref = f32('ref8'); ang = G['ang8'].astype(np.float32)
    n = lay(ref, ang, 7.0, 6, POINT, thr=0.04, region=reg, lmin=4, lmax=11, jit=0.02, p=0.9, tol=0.08, curv=0.4, taper=0.15)
    log('figures 7px', n)
    ref = f32('ref4'); ang = G['ang4'].astype(np.float32)
    for k_ in range(2):       # look again, correct again
        n = lay(ref, ang, 4.0, 3.6, POINT, thr=0.035, region=reg, lmin=4, lmax=11, jit=0.018, p=0.9, tol=0.07, curv=0.4, taper=0.15)
        log('figures 4px', n)
    ref = f32('ref2'); ang = G['ang2'].astype(np.float32)
    for k_ in range(2):
        n = lay(ref, ang, 2.2, 2.2, POINT, thr=0.045, region=reg, lmin=4, lmax=10, jit=0.012, p=0.9, tol=0.07, curv=0.4, taper=0.15)
        log('figures 2px', n)
    snap('6_figures')

# ------------------------------------------------------------------ stage 7: accents
if START <= 7 and STOP >= 7:
    c.frame_every = 20
    # the sun itself, loaded lead-white with a breath of yellow
    for i in range(46):
        a = rng.uniform(0, 6.28); d = rng.uniform(0, 26)
        c.stroke(FLAT, (1.0, 0.99, 0.90), [(SX + d * math.cos(a), SY + d * math.sin(a)), (SX + d * math.cos(a) + rng.normal(0, 9), SY + d * math.sin(a) + rng.normal(0, 5))],
                 r=rng.uniform(6, 11), p=0.95)
    # the shaft of light between them laid broken on the snow, and sparkle along the drift crests
    for i in range(110):
        t = rng.random() ** 1.6
        y = 1690 + t * 300
        x = SX + (y - YH) * rng.normal(0.0, 0.035) + rng.normal(0, 14)
        c.stroke(FLAT, np.array([1.0, 0.90, 0.72]) * rng.uniform(0.92, 1.0), [(x, y), (x + rng.uniform(14, 60) * (0.5 + t), y + rng.normal(0, 2))],
                 r=rng.uniform(2.5, 5) * (0.6 + t), p=0.7, op=0.5)
    for i in range(500):
        x = SX + rng.normal(0, 520); y = YH + 8 + abs(rng.normal(0, 190))
        if x < 0 or x >= W or maskd[int(y), int(x)]:
            continue
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
    # the fallen log he sits on: bark, the sawn end, snow lying along it
    for i in range(170):
        x, y = P3(rng.uniform(0.80, 1.62), rng.uniform(0.04, 0.43), 0.22)
        col = np.array([0.20, 0.15, 0.12]) * rng.uniform(0.5, 1.6) + rng.normal(0, 0.01, 3)
        c.stroke(BRISTLE2, col, [(x, y), (x + rng.uniform(40, 130), y + rng.normal(0, 4))], r=rng.uniform(3, 7), p=0.7, op=0.75)
    ex, ey = P3(1.61, 0.235, 0.05)
    for i in range(26):
        a0 = rng.uniform(0, 6.28)
        rr_ = rng.uniform(0.2, 1.0)
        c.stroke(FLAT, np.array([0.50, 0.38, 0.27]) * rng.uniform(0.75, 1.15), [(ex + 26 * rr_ * math.cos(a0), ey + 118 * rr_ * math.sin(a0)),
                 (ex + 26 * rr_ * math.cos(a0 + 0.7), ey + 118 * rr_ * math.sin(a0 + 0.7))], r=rng.uniform(4, 8), p=0.8)
    for i in range(150):
        x, y = P3(rng.uniform(0.84, 1.66), 0.47 + rng.normal(0, 0.012), 0.05)
        lit_ = rng.random() < 0.3
        col = (np.array([0.96, 0.84, 0.78]) if lit_ else np.array([0.60, 0.65, 0.88])) * rng.uniform(0.92, 1.05)
        c.stroke(FLAT, col, [(x, y - (5 if lit_ else 0)), (x + rng.uniform(20, 70), y + rng.normal(0, 2) - (5 if lit_ else 0))], r=rng.uniform(4, 10) * (0.5 if lit_ else 1), p=0.8)
    # a tear taking the light on the penitent's cheek
    tx, ty = P3(-0.036, 0.930, 0.075)
    c.stroke(POINT, (1.0, 0.90, 0.74), [(tx - 1, ty - 8), (tx, ty)], r=1.0, p=0.6, op=0.7)
    c.stroke(POINT, (1.0, 0.97, 0.88), [(tx, ty), (tx + 1, ty + 1)], r=1.8, p=1.0, taper=0.01)
    # new snow lying on shoulders, hair, the scarlet cloak where it trails
    for (X0, Y0, X1, Y1, Z, n_, sp) in [(0.44, 1.215, 0.66, 0.99, 0.2, 60, 0.022), (-0.30, 1.03, -0.52, 0.86, 0.22, 44, 0.022),
                                         (-1.05, 0.11, -1.72, 0.09, 0.2, 240, 0.07)]:
        for i in range(n_):
            t = rng.random()
            x, y = P3(X0 + (X1 - X0) * t + rng.normal(0, sp), Y0 + (Y1 - Y0) * t + rng.normal(0, sp * 0.5), Z + rng.normal(0, 0.12))
            if rng.random() < 0.5:
                continue
            c.stroke(POINT, np.array([0.70, 0.75, 0.93]) * rng.uniform(0.9, 1.05), [(x, y), (x + rng.uniform(1, 3), y + rng.normal(0, 1))],
                     r=rng.uniform(1.8, 3.6), p=0.8, op=0.8, taper=0.02)
    # last flakes of the departing storm, flicked on over the dark wood
    for i in range(900):
        x = abs(rng.normal(0, 900)); y = rng.uniform(0, H)
        if x > W or rng.random() > 0.25 + 0.75 * math.exp(-x / 700):
            continue
        r_ = 1.2 + 3.0 * rng.random() ** 3
        c.stroke(ROUND, (0.92, 0.94, 1.0), [(x, y), (x + r_ * 0.8, y + r_ * 1.6)], r=r_, p=rng.uniform(0.4, 0.85), op=0.8, taper=0.05)
    snap('7_final')
c.hold = 150 if STOP >= 7 else 1
c.finish_recording()
log('finished:', c.nstrokes, 'brush strokes')
