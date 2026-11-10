#!/usr/bin/env python3
"""
Self-Portrait (ink, watercolour, graphite and gold leaf on cold-press paper)

No image model is involved. Every mark is computed: paper tooth, pigment
pooling at the wet edge of a wash, pen strokes laid down point by point as
deposited ink, graphite catching only the peaks of the paper, leaf, a seal.

usage: python3 self_portrait.py [scale] [out.png]     (scale 1.0 -> 2400x3200)
"""
import sys
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import splprep, splev
from PIL import Image, ImageDraw

S = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
OUT = sys.argv[2] if len(sys.argv) > 2 else "self_portrait.png"
W, H = int(2400 * S), int(3200 * S)
rng = np.random.default_rng(11)
f32 = np.float32

yy, xx = np.mgrid[0:H, 0:W].astype(f32)
X, Y = xx / W, yy / W                      # unit coords: x in [0,1], y in [0,1.333]


# ----------------------------------------------------------------- helpers
def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def noise(scale, octaves=4, gain=0.5):
    """fractal value noise, roughly in [-1,1]; scale in px at S=1"""
    out = np.zeros((H, W), f32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = scale * S / (2 ** o)
        if s < 1.5:
            z = rng.standard_normal((H, W)).astype(f32) * 0.6
        else:
            g = rng.standard_normal((int(H / s) + 3, int(W / s) + 3)).astype(f32)
            z = ndi.zoom(g, s, order=3)[:H, :W]
        out += amp * z
        tot += amp
        amp *= gain
    return np.clip(out / tot / 0.75, -1.6, 1.6)


def blob(cx, cy, r):
    return np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * r * r))


def splat(dep, x, y, w):
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    ok = (x0 >= 0) & (x0 < W - 1) & (y0 >= 0) & (y0 < H - 1)
    x0, y0, fx, fy, w = x0[ok], y0[ok], (x - np.floor(x))[ok], (y - np.floor(y))[ok], w[ok]
    flat = dep.reshape(-1)
    for dx, dy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                       (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        flat += np.bincount((y0 + dy) * W + x0 + dx, weights=w * ww, minlength=W * H).astype(f32)


def resample(pts, spacing):
    d = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(d)])
    if s[-1] < spacing:
        return pts, s
    t = np.arange(0, s[-1], spacing)
    return np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], 1), t


LAYERS = {k: [] for k in ("ink", "bold", "graphite", "goldline", "sienna")}
SP = 0.4 * S


def stroke(layer, pts, pressure=1.0, wobble=0.0, taper=0.12):
    """lay a pen stroke: pts in px, pressure scalar or f(t in 0..1)"""
    pts, s = resample(np.asarray(pts, float), SP)
    n = len(pts)
    if n < 3:
        return
    t = s / max(s[-1], 1e-6)
    p = pressure(t) if callable(pressure) else np.full(n, float(pressure))
    if taper > 0:
        p = p * np.clip(np.minimum(t, 1 - t) / taper, 0, 1) ** 0.7
    if wobble:
        k = max(4, int(s[-1] / (60 * S)) + 3)
        wx = np.interp(t, np.linspace(0, 1, k), rng.standard_normal(k)) * wobble * S
        wy = np.interp(t, np.linspace(0, 1, k), rng.standard_normal(k)) * wobble * S
        pts = pts + np.stack([wx, wy], 1)
    p = p * (1 + 0.12 * np.interp(t, np.linspace(0, 1, 9), rng.standard_normal(9)))
    LAYERS[layer].append(np.column_stack([pts, p]))


def bezier(p0, p1, p2, n=60):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 2 * np.array(p0) + 2 * t * (1 - t) * np.array(p1) + t ** 2 * np.array(p2)) * W


def render_layer(name, sigma):
    dep = np.zeros((H, W), f32)
    if LAYERS[name]:
        a = np.concatenate(LAYERS[name])
        splat(dep, a[:, 0], a[:, 1], a[:, 2] * SP / S)
    return ndi.gaussian_filter(dep, sigma * S)


# ------------------------------------------------------------------- paper
print("paper"); sys.stdout.flush()
tooth = ndi.gaussian_filter(rng.standard_normal((H, W)).astype(f32), 1.3 * S)
tooth = tooth / tooth.std() * 0.6 + noise(9, 2) * 0.5
tooth = np.clip(tooth, -1.5, 1.5)
mottle = noise(700, 4)
paper = np.empty((H, W, 3), f32)
base = np.array([0.955, 0.925, 0.865], f32)
paper[:] = base
paper *= (1 + 0.022 * mottle + 0.012 * noise(60, 3))[..., None]
paper[..., 2] *= 1 - 0.02 * smoothstep(-0.3, 1, mottle)                       # uneven ageing
relief = np.roll(tooth, 1, 0) - np.roll(tooth, -1, 0) + np.roll(tooth, 1, 1) - np.roll(tooth, -1, 1)
paper *= (1 + 0.022 * relief)[..., None]                                       # raking light
# fibres
fib = np.zeros((H, W), f32)
for _ in range(int(900)):
    p0 = rng.uniform([0, 0], [W, H]); a = rng.uniform(0, np.pi); L = rng.uniform(15, 70) * S
    c = rng.normal(0, 0.25)
    t = np.linspace(0, 1, int(L / SP) + 2)
    ang = a + c * t
    px = p0[0] + np.cumsum(np.cos(ang)) * SP; py = p0[1] + np.cumsum(np.sin(ang)) * SP
    splat(fib, px, py, np.full(len(t), rng.uniform(-1, 1) * 0.5, f32))
fib = ndi.gaussian_filter(fib, 0.7 * S)
paper *= (1 - 0.05 * fib)[..., None]
for _ in range(14):                                                            # foxing
    cx, cy, r = rng.uniform(0.03, 0.97), rng.uniform(0.03, 1.30), rng.uniform(0.0012, 0.004)
    paper *= 1 - blob(cx, cy, r)[..., None] * np.array([0.05, 0.10, 0.18], f32) * rng.uniform(0.3, 1)

# -------------------------------------------------------------- silhouette
print("form"); sys.stdout.flush()
PROFILE = np.array([
    (0.470, 0.200), (0.535, 0.207), (0.590, 0.232), (0.632, 0.272), (0.655, 0.318),
    (0.667, 0.360), (0.662, 0.392),                       # brow -> nasion
    (0.680, 0.428), (0.708, 0.462), (0.729, 0.488),       # nose
    (0.716, 0.506), (0.690, 0.512),                       # under nose
    (0.697, 0.534), (0.681, 0.551), (0.693, 0.570),       # lips
    (0.676, 0.592), (0.687, 0.626), (0.668, 0.655),       # chin
    (0.620, 0.672), (0.578, 0.684), (0.560, 0.720),       # jaw -> throat
    (0.560, 0.790), (0.585, 0.860), (0.660, 0.925), (0.770, 0.985), (0.850, 1.080),
    (0.880, 1.220), (0.890, 1.400),
    (0.040, 1.400), (0.050, 1.200), (0.090, 1.060), (0.180, 0.965), (0.290, 0.905),
    (0.345, 0.830), (0.345, 0.740), (0.315, 0.650),       # nape
    (0.272, 0.560), (0.250, 0.460), (0.255, 0.370), (0.290, 0.290), (0.350, 0.232), (0.410, 0.207),
])
tck, _ = splprep([np.r_[PROFILE[:, 0], PROFILE[0, 0]], np.r_[PROFILE[:, 1], PROFILE[0, 1]]], s=0, per=1, k=3)
uu = np.linspace(0, 1, 6000)
sil = np.stack(splev(uu, tck), 1) * W
im = Image.new("L", (W, H), 0)
ImageDraw.Draw(im).polygon([tuple(p) for p in sil], fill=255)
mask = np.asarray(im) > 0
sdf = (ndi.distance_transform_edt(~mask) - ndi.distance_transform_edt(mask)).astype(f32)
sds = ndi.gaussian_filter(sdf, 7 * S)
gy, gx = np.gradient(sds)
gn = np.hypot(gx, gy) + 1e-6
gx, gy = gx / gn, gy / gn
sdb = ndi.gaussian_filter(sdf, 30 * S)
by, bx = np.gradient(sdb)
bn = np.hypot(bx, by) + 1e-6
back = np.clip((-bx / bn - 0.35 * by / bn) * 1.3 + 0.1, 0, 1)                 # 1 behind, 0 at the face

MIND = np.array([0.432, 0.405])                                               # the still point
R_RES = 0.050
dm = np.hypot(X - MIND[0], Y - MIND[1])

# where the line may live
n_l = noise(420, 3)
Lmap = 2 * S + 0.36 * W * back * (0.6 + 0.4 * n_l)
ALLOW = np.where(sdf < 0, 1.0, 1 - sdf / Lmap).astype(f32)
edge = np.minimum(np.minimum(xx, W - xx), yy)
ALLOW *= smoothstep(0.025 * W, 0.13 * W, edge)
ALLOW *= 1 - smoothstep(1.06 * W, 1.27 * W, yy + 0.05 * W * n_l)
ALLOW[dm < R_RES] = 0
ALLOW = np.clip(ALLOW, 0, 1)
OUTN = np.clip(1 - ALLOW, 0, 1) * (sdf > 0)                                    # how far gone

# tone -> line spacing
T = 0.46 + 0.2 * noise(500, 3)
T += 0.40 * blob(0.628, 0.385, 0.028) + 0.45 * blob(0.585, 0.700, 0.045) + 0.32 * blob(0.365, 0.72, 0.06)
T += 0.30 * blob(0.672, 0.520, 0.018) + 0.25 * blob(0.640, 0.585, 0.03) + 0.30 * blob(0.50, 0.57, 0.06)
T += 0.30 * blob(0.45, 0.95, 0.12) + 0.25 * np.exp(-(sdf / (0.012 * W)) ** 2) * (sdf < 0) * (1 - back)
T -= 0.38 * blob(0.60, 0.295, 0.055) + 0.34 * blob(0.625, 0.47, 0.04) + 0.25 * blob(0.69, 0.455, 0.02)
T -= 0.25 * blob(0.64, 0.63, 0.025) + 0.2 * blob(0.66, 1.02, 0.09)
T += 0.30 * np.exp(-((dm - R_RES) / 0.03) ** 2)
T = np.clip(T, 0, 1)
DSEP = (10.5 - 7.0 * T) * S * (1 + 5.5 * OUTN ** 1.4) * (1 + 2.5 * (1 - ALLOW) * (sdf <= 0))

# orientation field (double-angle blend): contour of the face, wind, orbit of the mind
th_c = np.arctan2(gx, -gy)
w_c = 1.7 * np.where(sdf < 0, np.exp(-(sdf / (0.05 * W)) ** 2), np.exp(-(sdf / (0.03 * W)) ** 2)) * (1 - 0.9 * back)
th_w = np.pi + 0.30 + 0.62 * noise(800, 3) + 0.5 * OUTN * noise(260, 2)
w_w = 0.75
th_d = np.arctan2(X - MIND[0], -(Y - MIND[1]))
w_d = 3.0 * np.exp(-((dm - R_RES) / 0.055) ** 2)
C = w_c * np.cos(2 * th_c) + w_w * np.cos(2 * th_w) + w_d * np.cos(2 * th_d)
Sn = w_c * np.sin(2 * th_c) + w_w * np.sin(2 * th_w) + w_d * np.sin(2 * th_d)
th = 0.5 * np.arctan2(Sn, C)
VX, VY = np.cos(th).astype(f32), np.sin(th).astype(f32)
del C, Sn, th_c, th_w, th_d, w_c, w_d

# ------------------------------------------------------------- streamlines
print("drawing"); sys.stdout.flush()
CELL = max(1, int(round(2 * S)))
oh, ow = H // CELL + 1, W // CELL + 1
occ = np.zeros((oh, ow), bool)
STEP = 1.5 * S
MAXS = 800


def look(A, P):
    ix = np.clip(P[:, 0].astype(int), 0, W - 1)
    iy = np.clip(P[:, 1].astype(int), 0, H - 1)
    return A[iy, ix]


def trace(seeds, dist):
    n = len(seeds)
    halves = []
    for sign in (1, -1):
        P = seeds.astype(f32).copy()
        D = sign * np.stack([look(VX, P), look(VY, P)], 1)
        alive = np.ones(n, bool)
        rec = np.full((MAXS, n, 2), np.nan, f32)
        for k in range(MAXS):
            v = np.stack([look(VX, P), look(VY, P)], 1)
            v[(v * D).sum(1) < 0] *= -1
            Pm = P + v * (STEP * 0.5)
            v2 = np.stack([look(VX, Pm), look(VY, Pm)], 1)
            v2[(v2 * D).sum(1) < 0] *= -1
            P = P + v2 * STEP
            D = v2
            inb = (P[:, 0] > 1) & (P[:, 0] < W - 2) & (P[:, 1] > 1) & (P[:, 1] < H - 2)
            ix = np.clip(P[:, 0].astype(int), 0, W - 1); iy = np.clip(P[:, 1].astype(int), 0, H - 1)
            alive &= inb & (ALLOW[iy, ix] > 0.02) & (dist[iy // CELL, ix // CELL] > DSEP[iy, ix] * 0.5)
            if not alive.any():
                break
            rec[k, alive] = P[alive]
        halves.append(rec)
    paths = []
    for i in range(n):
        f = halves[0][:, i]; b = halves[1][:, i]
        f = f[~np.isnan(f[:, 0])]; b = b[~np.isnan(b[:, 0])]
        paths.append(np.concatenate([b[::-1], seeds[i:i + 1], f]))
    return paths


ALLOW_lo = ALLOW[::CELL, ::CELL]
DSEP_lo = DSEP[::CELL, ::CELL]
hh, wl = ALLOW_lo.shape
PATHS = []
for it in range(700):
    dist = (ndi.distance_transform_edt(~occ) * CELL).astype(f32) if occ.any() else np.full((oh, ow), 1e6, f32)
    cand = np.flatnonzero((dist[:hh, :wl] > DSEP_lo) & (ALLOW_lo > 0.03))
    if len(cand) < 12:
        break
    pick = rng.choice(cand, size=min(len(cand), 40 + it), replace=False)
    sy, sx = np.unravel_index(pick, (hh, wl))
    key = (sy * CELL // int(34 * S)) * 10000 + sx * CELL // int(34 * S)
    _, first = np.unique(key, return_index=True)
    seeds = np.stack([sx[first] * CELL + 0.5, sy[first] * CELL + 0.5], 1).astype(f32)
    for p in trace(seeds, dist):
        occ[np.clip((p[:, 1] / CELL).astype(int), 0, oh - 1), np.clip((p[:, 0] / CELL).astype(int), 0, ow - 1)] = True
        if len(p) >= 4:
            PATHS.append(p)
print("  strokes:", len(PATHS), "iterations:", it); sys.stdout.flush()

for p in PATHS:
    pts, s = resample(p.astype(float), SP)
    n = len(pts)
    if n < 4:
        continue
    t = s / s[-1]
    a = look(ALLOW, pts); o = look(OUTN, pts); tone = look(T, pts)
    press = rng.uniform(0.55, 1.0) * np.clip(np.minimum(t, 1 - t) / 0.1, 0, 1) ** 0.6
    press = press * (0.30 + 0.70 * a ** 0.8) * (0.72 + 0.5 * tone)
    press = press * (1 + 0.15 * np.interp(t, np.linspace(0, 1, 12), rng.standard_normal(12)))
    # past the edge of the head the line loosens into handwriting
    tan = np.gradient(pts, axis=0)
    tan /= np.hypot(tan[:, 0], tan[:, 1])[:, None] + 1e-9
    nor = np.stack([-tan[:, 1], tan[:, 0]], 1)
    ph = rng.uniform(0, 6.28, 5)
    lam = np.array([9.5, 5.6, 15.0]) * S * rng.uniform(0.85, 1.2)
    sig = np.sin(6.283 * s / lam[0] + ph[0]) + 0.7 * np.sin(6.283 * s / lam[1] + ph[1] + 1.3 * np.sin(6.283 * s / lam[2] + ph[2]))
    sig += 0.9 * np.maximum(0, np.sin(6.283 * s / (lam[2] * 2.3) + ph[3])) ** 6 * np.sign(np.sin(ph[4] + s))  # ascenders
    amp = 5.2 * S * smoothstep(0.06, 0.6, o)
    slant = 0.45 * amp * sig
    pts = pts + nor * (amp * sig)[:, None] + tan * slant[:, None]
    word = smoothstep(-0.92, -0.75, np.sin(6.283 * s / (rng.uniform(55, 110) * S) + ph[3]))
    press = press * (1 - smoothstep(0.2, 0.5, o) * (1 - word))
    LAYERS["ink"].append(np.column_stack([pts, press]))

# ----------------------------------------------------------- face, by hand
u_of = lambda i: int(i / len(PROFILE) * 6000)
seg = sil[u_of(1.2):u_of(24.6)]
tt = np.linspace(0, 1, len(seg))
stroke("bold", seg, lambda t: 0.55 + 0.45 * np.interp(t, tt, ndi.gaussian_filter1d(
    np.clip(np.gradient(seg[:, 0]) * -1.0, 0, None) / S, 40) * 2.2 + 0.25), wobble=0.5, taper=0.10)
stroke("ink", seg + [1.2 * S, 0.6 * S], 0.5, wobble=0.9, taper=0.2)
stroke("bold", bezier((0.597, 0.397), (0.626, 0.421), (0.653, 0.404)), lambda t: 0.5 + 0.6 * np.sin(np.pi * t), taper=0.2)
stroke("ink", bezier((0.600, 0.384), (0.630, 0.374), (0.657, 0.390)), 0.6, taper=0.3)
for k in range(9):                                                             # lashes
    t0 = 0.45 + 0.055 * k
    b = bezier((0.597, 0.397), (0.626, 0.421), (0.653, 0.404), 100)[int(t0 * 99)] / W
    stroke("ink", bezier(b, (b[0] + 0.006, b[1] + 0.008), (b[0] + 0.012 + 0.001 * k, b[1] + 0.011 - 0.0012 * k), 20), 0.7, taper=0.45)
stroke("bold", bezier((0.684, 0.5515), (0.668, 0.553), (0.652, 0.559)), lambda t: 0.9 - 0.5 * t, taper=0.25)
stroke("ink", bezier((0.704, 0.497), (0.694, 0.492), (0.690, 0.503)), 0.9, taper=0.3)   # nostril
stroke("ink", bezier((0.560, 0.36), (0.600, 0.338), (0.648, 0.352)), 0.55, taper=0.4)   # brow

# instrument around the still point
ang = np.linspace(0, 2 * np.pi, 400)
for r, pr in ((0.0405, 0.8), (0.0470, 0.55), (0.0500, 0.9)):
    a0 = rng.uniform(0, 6.28)
    stroke("ink", np.stack([MIND[0] + r * np.cos(ang + a0), MIND[1] + r * np.sin(ang + a0)], 1) * W, pr, wobble=0.35, taper=0.02)
for k in range(120):
    a = 2 * np.pi * k / 120
    r1 = 0.0470 - (0.0048 if k % 10 == 0 else 0.0033 if k % 5 == 0 else 0.002)
    stroke("ink", np.array([[MIND[0] + r1 * np.cos(a), MIND[1] + r1 * np.sin(a)],
                            [MIND[0] + 0.0470 * np.cos(a), MIND[1] + 0.0470 * np.sin(a)]]) * W, 0.8, taper=0.1)

# graphite under-drawing: the armature someone else ruled
SK = np.array([0.458, 0.425]); RS = 0.218
stroke("graphite", np.stack([SK[0] + RS * np.cos(ang), SK[1] + RS * np.sin(ang)], 1) * W, 0.9, wobble=0.8, taper=0.01)
stroke("graphite", np.stack([SK[0] + RS * 1.618 * np.cos(ang[40:230]), SK[1] + 0.135 + RS * 1.618 * np.sin(ang[40:230])], 1) * W, 0.5, wobble=0.8)
for (x0, y0, x1, y1, pr) in ((0.16, 0.425, 0.80, 0.425, 0.8), (0.458, 0.14, 0.458, 1.12, 0.8),
                             (0.50, 0.360, 0.78, 0.360, 0.6), (0.50, 0.512, 0.80, 0.512, 0.6),
                             (0.50, 0.660, 0.78, 0.660, 0.6), (0.733, 0.17, 0.733, 0.72, 0.5),
                             (0.24, 0.207, 0.76, 0.207, 0.5), (0.20, 0.17, 0.80, 0.77, 0.35),
                             (0.432, 0.405, 0.626, 0.405, 0.7)):
    stroke("graphite", np.array([[x0, y0], [x1, y1]]) * W, pr, wobble=0.7, taper=0.03)
for yv in (0.207, 0.360, 0.512, 0.660):
    stroke("graphite", np.array([[0.772, yv - 0.006], [0.784, yv + 0.006]]) * W, 0.9, taper=0.1)

# ------------------------------------------------------------------ stars
print("stars"); sys.stdout.flush()
wt = (smoothstep(0.08, 0.5, OUTN) * (1 - smoothstep(0.8, 1.0, OUTN)) * (ALLOW > 0.02)
      + 0.25 * (sdf < 0) * back * (dm > 0.09) * (Y < 0.8))[::8, ::8].astype(float)
wt *= ((X < 0.6) & (edge > 0.07 * W))[::8, ::8]
idx = rng.choice(wt.size, size=260, replace=False, p=(wt / wt.sum()).ravel())
sy, sx = np.unravel_index(idx, wt.shape)
cands = np.stack([sx * 8 + rng.uniform(0, 8, len(sx)), sy * 8 + rng.uniform(0, 8, len(sx))], 1)
stars = []
for c in cands:                                                                # keep them apart
    if all(np.hypot(*(c - s0)) > 0.034 * W for s0 in stars):
        stars.append(c)
stars = np.array(stars[:64])
srad = rng.pareto(2.2, len(stars)) * 3.0 + 3.6
srad = np.clip(srad, 3.6, 14) * S
mind_px = MIND * W
# threads: a minimum spanning tree — every point reachable from the centre, no thread wasted
nodes = np.vstack([mind_px, stars])
D2 = np.hypot(nodes[:, None, 0] - nodes[None, :, 0], nodes[:, None, 1] - nodes[None, :, 1])
intree = [0]; edges = []
best = D2[0].copy(); parent = np.zeros(len(nodes), int)
best[0] = np.inf
for _ in range(len(nodes) - 1):
    j = int(np.argmin(best))
    edges.append((parent[j], j)); intree.append(j)
    upd = D2[j] < best
    upd[intree] = False
    parent[upd] = j; best[upd] = D2[j][upd]; best[j] = np.inf
for a, b in edges:
    p0, p1 = nodes[a].copy(), nodes[b]
    if a == 0:
        d = (p1 - p0) / np.hypot(*(p1 - p0)); p0 = p0 + d * 0.0505 * W
    stroke("goldline", np.array([p0, p1]), 0.9, wobble=0.5, taper=0.04)

# ------------------------------------------------------------------ washes
print("washes"); sys.stdout.flush()


def wash(cx, cy, rx, ry, amp, soft, strength, rot=0.0):
    dx, dy = X - cx, Y - cy
    if rot:
        dx, dy = dx * np.cos(rot) + dy * np.sin(rot), -dx * np.sin(rot) + dy * np.cos(rot)
    d = (np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) - 1) * min(rx, ry)
    f = -(d + amp * (0.7 * noise(520, 5, 0.55) + 0.3 * noise(90, 3))) / soft
    m = smoothstep(0, 1, f)
    rim = np.exp(-((f - 0.55) / 0.3) ** 2) * m                                 # pigment carried to the drying edge
    pool = 0.62 + 0.38 * noise(300, 4)                                         # back-runs and pooling
    return strength * (m * pool + 0.55 * rim) * (1 + 0.32 * tooth)


halo = smoothstep(R_RES * 0.95, R_RES * 2.4, dm)                               # paper kept dry around the light
indigo = (wash(0.335, 0.475, 0.265, 0.355, 0.085, 0.022, 0.44) + wash(0.30, 0.43, 0.17, 0.23, 0.07, 0.03, 0.34, 0.4)
          + wash(0.20, 0.80, 0.12, 0.16, 0.06, 0.03, 0.22, -0.5)) * (0.12 + 0.88 * halo)
sienna = (wash(0.585, 0.60, 0.150, 0.340, 0.07, 0.022, 0.42, 0.12) + wash(0.60, 0.50, 0.085, 0.16, 0.05, 0.03, 0.22)
          + wash(0.55, 1.0, 0.20, 0.13, 0.07, 0.03, 0.26, 0.3))
sienna *= 1 - 0.6 * smoothstep(0, 0.012 * W, sdf) * (1 - back)                 # mostly held by the profile
ochre = wash(0.45, 0.36, 0.16, 0.13, 0.06, 0.04, 0.30, -0.3) * (0.3 + 0.7 * halo) + wash(0.70, 0.80, 0.07, 0.10, 0.05, 0.03, 0.16)
for dep, n_sp in ((indigo, 70), (sienna, 45)):                                 # flicked brush
    for _ in range(n_sp):
        cx = rng.uniform(0.06, 0.94) * W; cy = rng.uniform(0.08, 1.25) * W
        r = min(rng.pareto(2.0) * 1.6 + 1.2, 11) * S
        x0, x1, y0, y1 = int(cx - r - 3), int(cx + r + 4), int(cy - r - 3), int(cy + r + 4)
        if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H:
            continue
        d = np.hypot(xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy)
        dep[y0:y1, x0:x1] += rng.uniform(0.2, 0.6) * (np.clip(r - d, 0, 1) * (0.6 + 0.6 * np.clip(d / r, 0, 1) ** 3))

# ---------------------------------------------------------------- compose
print("compose"); sys.stdout.flush()
ink = render_layer("ink", 0.62)
ink = ink + 0.16 * ndi.gaussian_filter(ink, 1.8 * S)                           # slight feathering into the sheet
bold = render_layer("bold", 1.05)
gra = render_layer("graphite", 0.75) * np.clip(0.55 + 0.9 * tooth, 0.05, 1.6)  # graphite rides the tooth
ink_d = 1.75 * ink * (1 + 0.12 * tooth) + 1.9 * bold


def absorb(rgb):
    return -np.log(np.array(rgb, f32))


img = paper.copy()
od = (0.55 * gra[..., None] * absorb((0.30, 0.30, 0.33))
      + indigo[..., None] * absorb((0.13, 0.20, 0.40))
      + sienna[..., None] * absorb((0.78, 0.36, 0.22))
      + ochre[..., None] * absorb((0.90, 0.68, 0.30))
      + ink_d[..., None] * absorb((0.20, 0.17, 0.19)))
img *= np.exp(-od)

# gold leaf
gm = np.zeros((H, W), f32)
rag = 0.9 * S * noise(14, 2)
gm = np.maximum(gm, np.clip((0.0345 * W - dm * W + rag) / S + 0.5, 0, 1))
for c, r in zip(stars, srad):
    x0, x1, y0, y1 = int(c[0] - r - 3), int(c[0] + r + 4), int(c[1] - r - 3), int(c[1] + r + 4)
    d = np.hypot(xx[y0:y1, x0:x1] - c[0], yy[y0:y1, x0:x1] - c[1])
    gm[y0:y1, x0:x1] = np.maximum(gm[y0:y1, x0:x1], np.clip((r - d + rag[y0:y1, x0:x1] * 0.5) / S + 0.5, 0, 1))
gl = np.clip(render_layer("goldline", 0.6) * 2.6, 0, 1)
gm = np.maximum(gm, gl * (0.55 + 0.45 * (tooth > -0.5)))
crinkle = np.abs(noise(46, 4, 0.6))
sheen = 0.5 + 0.5 * np.sin((X * 0.8 + Y * 0.6) * 9 + 2.2 * noise(380, 3))
lum = np.clip(0.50 + 0.38 * sheen + 0.30 * noise(7, 3) * 0.6 - 0.35 * smoothstep(0.0, 0.10, 0.12 - crinkle) + 0.05 * relief, 0, 1.25)
dark, mid, lite = np.array([0.45, 0.30, 0.09], f32), np.array([0.80, 0.60, 0.22], f32), np.array([0.99, 0.90, 0.60], f32)
lum3 = lum[..., None]
gold = np.where(lum3 < 0.6, dark + (mid - dark) * (lum3 / 0.6), mid + (lite - mid) * np.clip((lum3 - 0.6) / 0.55, 0, 1))
sh = ndi.gaussian_filter(np.roll(np.roll(gm, int(2 * S) + 1, 0), int(2 * S) + 1, 1), 2.2 * S)
img *= (1 - 0.30 * sh * (1 - gm))[..., None]
flaw = smoothstep(0.80, 0.95, noise(26, 3) * 0.6 + 0.5 + 0.25 * tooth)         # where the leaf didn't take
ga = gm * (1 - 0.8 * flaw)
img = img * (1 - ga[..., None]) + gold * ga[..., None]
# incised rays on the disc
rays = np.zeros((H, W), f32)
for k in range(48):
    a = 2 * np.pi * k / 48 + 0.03
    r = np.linspace(0.006 if k % 2 else 0.011, 0.031, 80) * W
    splat(rays, mind_px[0] + r * np.cos(a), mind_px[1] + r * np.sin(a), np.full(80, 0.5, f32))
rays = np.clip(ndi.gaussian_filter(rays, 0.6 * S) * 1.4, 0, 1)
img *= (1 - 0.42 * rays)[..., None]

# the seal
ss = int(0.058 * W); q = 4
sim = Image.new("L", (ss * q, ss * q), 0)
dr = ImageDraw.Draw(sim)
dr.rounded_rectangle([0, 0, ss * q - 1, ss * q - 1], radius=int(ss * q * 0.07), fill=255)
m_ = ss * q
dr.rectangle([m_ * 0.10, m_ * 0.10, m_ * 0.90, m_ * 0.90], outline=0, width=int(m_ * 0.035))
dr.ellipse([m_ * 0.27, m_ * 0.27, m_ * 0.73, m_ * 0.73], outline=0, width=int(m_ * 0.05))
dr.ellipse([m_ * 0.44, m_ * 0.44, m_ * 0.56, m_ * 0.56], fill=0)
for k in range(3):                                                             # three strands leaving
    yv = m_ * (0.40 + 0.10 * k)
    pts = [(m_ * 0.10 + t * m_ * 0.24, yv + m_ * 0.025 * np.sin(t * 7 + k)) for t in np.linspace(0, 1, 20)]
    dr.line(pts, fill=0, width=int(m_ * 0.04))
sim = sim.rotate(-3.5, resample=Image.BICUBIC, expand=True).resize((int(ss * 1.08), int(ss * 1.08)), Image.LANCZOS)
sa = np.asarray(sim, f32) / 255
sx0, sy0 = int(0.845 * W), int(1.195 * W)
sl = (slice(sy0, sy0 + sa.shape[0]), slice(sx0, sx0 + sa.shape[1]))
tx = np.clip(0.80 + 0.5 * tooth[sl] + 0.35 * noise(120, 3)[sl], 0, 1.25)
sa = ndi.gaussian_filter(sa, 0.5 * S) * tx
img[sl] *= np.exp(-1.25 * sa[..., None] * absorb((0.80, 0.13, 0.09)))

# finish: the sheet itself
img *= (1 - 0.05 * smoothstep(0.55, 1.0, np.hypot(X - 0.5, (Y - 0.667) * 0.75) / 0.7))[..., None]
img += rng.standard_normal((H, W, 1)).astype(f32) * 0.006
img = np.clip(img, 0, 1) ** (1 / 1.0)
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(OUT)
print("saved", OUT, W, H)
