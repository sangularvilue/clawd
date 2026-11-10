#!/usr/bin/env python3
"""
Stage 2 of the old-master self-portrait: the painting.

Takes the lit study from old_master_model.py and paints it in simulated oil:
a toned ground, then layer on layer of bristle strokes from broad to fine,
each one loaded with colour mixed from the study and dragged along the form.
Lights are laid thick, shadows thin. Then the picture is aged: raking light
on the impasto, canvas weave showing through the darks, a yellowed varnish,
and four centuries of craquelure.

usage: python3 old_master_paint.py reference.npy out.png [width]
"""
import sys
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw, ImageFont

import os
STILL = os.environ.get('STILL') == '1'
REF = sys.argv[1]
OUT = sys.argv[2]
W = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
H = W * 4 // 3
K = W / 2400.0
f32 = np.float32
rng = np.random.default_rng(1669)


def up(a, order=Image.BICUBIC):
    if a.ndim == 3:
        return np.stack([up(a[..., i], order) for i in range(a.shape[2])], -1)
    return np.asarray(Image.fromarray(a.astype(f32), "F").resize((W, H), order), f32)


def noise(scale, octaves=4, gain=0.5):
    out = np.zeros((H, W), f32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        s = scale * K / (2 ** o)
        if s < 1.5:
            z = rng.standard_normal((H, W)).astype(f32) * 0.6
        else:
            g = rng.standard_normal((int(H / s) + 3, int(W / s) + 3)).astype(f32)
            z = ndi.zoom(g, s, order=3)[:H, :W]
        out += amp * z; tot += amp; amp *= gain
    return np.clip(out / tot / 0.75, -1.6, 1.6)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- the study
ref = np.clip(up(np.load(REF)), 0, 1)
mat = np.load(REF.replace(".npy", "_mat.npy"))
face = up((np.isin(mat, (0, 1))).astype(f32), Image.BILINEAR)
linen = up((mat == 5).astype(f32), Image.BILINEAR)
figure = up((mat >= 0).astype(f32), Image.BILINEAR)
# a painter does not see flat gradients: break the colour, warm against cool
warm = noise(260, 4)[..., None] * np.array([0.030, 0.008, -0.022], f32)
ref = ref * (1 + 0.10 * noise(520, 4)[..., None] * (1 - 0.6 * face[..., None])) + warm * (0.35 + 0.65 * (1 - face[..., None]))
ref += 0.008 * noise(40, 3)[..., None] * (1 - face[..., None])
ref = np.clip(ref, 0.012, 1)
soft = ndi.gaussian_filter(ref, (4 * K, 4 * K, 0))                       # sfumato: no edge in a face is a knife edge
eyes = np.clip(ndi.gaussian_filter(up((mat == 1).astype(f32), Image.BILINEAR), 14 * K) * 6, 0, 1)
if STILL:                                                              # writing is laid in last, dark and crisp, with a fine brush
    fine = up((mat == 1).astype(f32), Image.BILINEAR)[..., None]
    loc = ndi.gaussian_filter(ref, (9 * K, 9 * K, 0))
    ref = np.clip(ref - 1.1 * fine * np.clip(loc - ref, 0, 1) * (loc.sum(-1, keepdims=True) > 1.2), 0.012, 1)
sf = ((0.2 if STILL else 0.65) * face * (1 - eyes))[..., None]
ref = ref * (1 - sf) + soft * sf
ref += (0.4 if STILL else 1.0) * face[..., None] * noise(34, 3)[..., None] * np.array([0.030, 0.004, -0.020], f32)   # broken colour in the flesh

# ----------------------------------------------------------------- painting
canvas = np.empty((H, W, 3), f32)
canvas[:] = np.array([0.215, 0.135, 0.075], f32)                    # warm imprimatura
canvas *= (1 + 0.12 * noise(300, 4))[..., None]
height = np.zeros((H, W), f32)
flow = noise(900, 3) * 2.2 + 0.7                                    # the habit of the arm
weave_x = np.sin((np.arange(W) / (5.6 * K)) * 2 * np.pi).astype(f32)
weave_y = np.sin((np.arange(H) / (5.6 * K)) * 2 * np.pi).astype(f32)
weave = (weave_x[None, :] * 0.5 + weave_y[:, None] * 0.5) + 0.35 * noise(3, 1)


def paint_layer(bw, bl, thr, opacity, region=None, curve=0.0, colour_jit=0.02, dry=0.5):
    bw *= K; bl *= K
    sig = max(bw * 0.28, 0.6)
    rb = ndi.gaussian_filter(ref, (sig, sig, 0))
    lum = ndi.gaussian_filter(ref @ np.array([0.3, 0.55, 0.15], f32), max(bw * 0.5, 1.0))
    gy, gx = np.gradient(lum)
    # structure tensor -> the direction along the form
    s2 = max(bw * 0.8, 2)
    jxx, jyy, jxy = (ndi.gaussian_filter(a, s2) for a in (gx * gx, gy * gy, gx * gy))
    ang = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
    cohn = coh / (coh + np.percentile(coh, 70) + 1e-9)
    err = np.abs(ndi.gaussian_filter(canvas, (sig, sig, 0)) - rb).sum(-1)
    step = max(bw * 0.5, 1.5)
    gx_, gy_ = np.meshgrid(np.arange(step / 2, W, step), np.arange(step / 2, H, step))
    pts = np.stack([gx_.ravel(), gy_.ravel()], 1) + rng.uniform(-step / 2, step / 2, (gx_.size, 2))
    pts[:, 0] = np.clip(pts[:, 0], 0, W - 1); pts[:, 1] = np.clip(pts[:, 1], 0, H - 1)
    ix, iy = pts[:, 0].astype(int), pts[:, 1].astype(int)
    keep = err[iy, ix] > thr
    if region is not None:
        keep &= rng.uniform(0, 1, len(pts)) < region[iy, ix]
    pts, ix, iy = pts[keep], ix[keep], iy[keep]
    order = rng.permutation(len(pts))
    n_b = 24
    for j in order:
        x, y = pts[j]
        c = cohn[iy[j], ix[j]]
        a = ang[iy[j], ix[j]] * c + flow[iy[j], ix[j]] * (1 - c) if c < 0.35 else ang[iy[j], ix[j]]
        a += rng.normal(0, 0.18)
        L = bl * rng.uniform(0.6, 1.25) * (0.55 + 0.45 * c)
        wv = bw * rng.uniform(0.75, 1.2)
        R = int(L / 2 + wv) + 2
        x0, x1, y0, y1 = max(0, int(x) - R), min(W, int(x) + R + 1), max(0, int(y) - R), min(H, int(y) + R + 1)
        dx = np.arange(x0, x1, dtype=f32)[None, :] - x
        dy = np.arange(y0, y1, dtype=f32)[:, None] - y
        ca, sa = np.cos(a), np.sin(a)
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        if curve:
            v = v - rng.normal(0, curve) * u * u / L
        un = u / L + 0.5                                                    # 0 at the start of the stroke, 1 at the lift
        vn = v / wv
        bristle = rng.uniform(0.35, 1.0, n_b).astype(f32)
        bi = np.clip(((vn + 0.5) * n_b).astype(int), 0, n_b - 1)
        br = bristle[bi]
        al = smoothstep(0.5, 0.36, np.abs(vn)) * smoothstep(-0.02, 0.10, un) * smoothstep(1.02, 0.80, un)
        # the brush runs dry: bristles lift, the weave catches what is left
        dryness = smoothstep(0.35, 1.0, un) * dry
        al = al * smoothstep(dryness - 0.15, dryness + 0.25, br * (0.8 + 0.25 * weave[y0:y1, x0:x1]))
        al = al * opacity
        col = rb[iy[j], ix[j]] * (1 + rng.normal(0, colour_jit)) + rng.normal(0, colour_jit * 0.4, 3)
        lumc = float(col @ np.array([0.3, 0.55, 0.15]))
        streak = 1 + 0.07 * (br - 0.65)                                     # imperfectly mixed paint
        canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - al[..., None]) + (col[None, None, :] * streak[..., None]) * al[..., None]
        thick = (0.15 + 1.6 * lumc ** 2) * min(1.0, bw / (12 * K)) ** 0.5
        height[y0:y1, x0:x1] = height[y0:y1, x0:x1] * (1 - 0.8 * al) + al * thick * (0.55 + 0.6 * br + 0.5 * smoothstep(0.25, 0.5, np.abs(vn)))
    print(f"  brush {bw / K:5.1f}: {len(pts)} strokes"); sys.stdout.flush()


print("painting"); sys.stdout.flush()
paint_layer(95, 300, -1, 0.90, curve=0.5, colour_jit=0.05, dry=0.7)          # dead-colouring
paint_layer(46, 170, 0.05, 0.88, curve=0.4, colour_jit=0.04, dry=0.7)
paint_layer(22, 90, 0.045, 0.88, curve=0.3, colour_jit=0.03, dry=0.6)
paint_layer(11, 46, 0.04, 0.90, region=0.25 + 0.75 * figure, curve=0.2, colour_jit=0.025)
paint_layer(5.5, 30, 0.04, 0.85, region=np.clip(face + linen + 0.08, 0, 1), colour_jit=0.035, dry=0.5)
paint_layer(3.0, 17, 0.075, 0.88, region=np.clip(face + 0.5 * linen, 0, 1), colour_jit=0.02, dry=0.3)
paint_layer(1.8, 10, 0.10, 0.92, region=face, colour_jit=0.01, dry=0.2)
paint_layer(1.4, 7, 0.05, 0.95, region=eyes, colour_jit=0.005, dry=0.1)

# signature, in the shadow at the right, the way they did it
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", int(46 * K))
    sm = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sm)
    if STILL:
        d.text((int(0.66 * W), int(0.925 * H)), "Claude  f.  2026", font=font, fill=255)
    else:
        d.text((int(0.69 * W), int(0.598 * H)), "Claude  f.", font=font, fill=255)
        d.text((int(0.725 * W), int(0.622 * H)), "2026", font=font, fill=255)
    sg = ndi.gaussian_filter(np.asarray(sm, f32) / 255, 1.1 * K) * (0.55 + 0.3 * noise(30, 2)) * (0.75 + 0.25 * weave)
    sg = np.clip(sg, 0, 1)[..., None] * 0.62
    canvas = canvas * (1 - sg) + np.array([0.40, 0.27, 0.12], f32) * sg
    height += sg[..., 0] * 0.25
except Exception as e:
    print("no signature:", e)

# ------------------------------------------------------------------- ageing
print("ageing"); sys.stdout.flush()
img = canvas
hs = ndi.gaussian_filter(height, 1.6 * K)
hy, hx = np.gradient(hs)
rake = -(hx * 0.7 + hy * 0.7) / K ** 0 * 1.0
img = img * (1 + np.clip(0.9 * rake, -0.22, 0.3))[..., None]                   # raking light across the impasto
img += (np.clip(rake - 0.05, 0, 1) ** 1.5 * 0.6 * smoothstep(0.5, 1.4, hs))[..., None] * np.array([1.0, 0.95, 0.8], f32)
thin = 1 - smoothstep(0.1, 0.7, hs)
img *= (1 + 0.075 * weave * (0.35 + 0.65 * thin))[..., None]                   # weave shows where paint is thin

# glaze and varnish: warm, sunk in the darks, pooled in the hollows of the paint
pool = ndi.gaussian_filter(hs, 3 * K) - hs
img *= (1 - np.clip(pool, 0, 1) * 0.35)[..., None]
img = np.clip(img, 0, 1.2)
img = img * np.array([1.0, 0.94, 0.80], f32) * (1 + 0.05 * noise(700, 3))[..., None]
img = img + np.array([0.022, 0.016, 0.006], f32) * (1 + 0.5 * noise(400, 3))[..., None]

# craquelure: drying islands, finer and more open where the lead white is thick
yy, xx = np.mgrid[0:H, 0:W].astype(f32)
wx = xx + 14 * K * noise(120, 3); wy = (yy + 14 * K * noise(120, 3)) * 0.8
lumi = img @ np.array([0.3, 0.55, 0.15], f32)
light = ndi.gaussian_filter(smoothstep(0.12, 0.6, lumi), 20 * K)


def cracks(n, width):
    seeds = np.stack([rng.uniform(0, W, n), rng.uniform(0, H * 0.8, n)], 1)
    q = np.stack([wx.ravel(), wy.ravel()], 1)
    d, _ = cKDTree(seeds).query(q, k=2, workers=-1)
    e = (d[:, 1] - d[:, 0]).reshape(H, W)
    return smoothstep(width * K, width * K * 0.25, e)


c1 = cracks(int(2600), 1.5)
c2 = cracks(int(11000), 1.1)
gate = smoothstep(-0.2, 0.5, noise(240, 3))
ck = np.clip(c1 * (0.35 + 0.5 * light) + c2 * (0.08 + 0.55 * light) * gate, 0, 1)
ck *= 0.75 + 0.25 * noise(8, 2)
if STILL:
    ck *= 1 - 0.6 * eyes
lift = np.roll(np.roll(ck, -1, 0), -1, 1)                                      # the lifted lip of each island catches light
img = img * (1 - 0.45 * ck[..., None]) + 0.05 * (lift * (1 - ck))[..., None] * light[..., None]

# time: darkened edges where the frame sat, dust, a few losses
edge = np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) / W
img *= (0.55 + 0.45 * smoothstep(0.0, 0.035, edge + 0.006 * noise(60, 2)))[..., None]
img *= (1 - 0.30 * smoothstep(0.45, 1.0, np.hypot(xx / W - 0.47, (yy / H - 0.42) * 1.15) / 0.75))[..., None]
img += rng.standard_normal((H, W, 1)).astype(f32) * 0.006
img = np.clip(img, 0, 1)
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(OUT)
print("saved", OUT)
