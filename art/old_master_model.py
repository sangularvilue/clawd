#!/usr/bin/env python3
"""
Stage 1 of the old-master self-portrait: the sitter.

A head, hat, hair, collar and cloak are sculpted as signed-distance fields and
lit by a single high window to the left (sphere tracing, soft shadow, ambient
occlusion). The result is only a *reference* - the study a painter looks at.
Stage 2 (old_master_paint.py) paints from it.

usage: python3 old_master_model.py [width] [out.npy]
"""
import sys
import numpy as np

WI = int(sys.argv[1]) if len(sys.argv) > 1 else 600
OUT = sys.argv[2] if len(sys.argv) > 2 else "reference.npy"
HI = WI * 4 // 3
f32 = np.float32


def norm(v):
    v = np.asarray(v, f32)
    return v / np.linalg.norm(v)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def ell(p, c, r):
    q = (p - np.asarray(c, f32)) / np.asarray(r, f32)
    k0 = np.sqrt((q * q).sum(-1))
    k1 = np.sqrt(((q / np.asarray(r, f32)) ** 2).sum(-1)) + 1e-9
    return k0 * (k0 - 1) / k1


def sph(p, c, r):
    return np.sqrt(((p - np.asarray(c, f32)) ** 2).sum(-1)) - r


def cap(p, a, b, ra, rb=None):
    a = np.asarray(a, f32); b = np.asarray(b, f32)
    rb = ra if rb is None else rb
    pa, ba = p - a, b - a
    h = np.clip((pa * ba).sum(-1) / (ba * ba).sum(), 0, 1)
    return np.sqrt(((pa - ba * h[..., None]) ** 2).sum(-1)) - (ra + (rb - ra) * h)


def roty(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([c * p[..., 0] + s * p[..., 2], p[..., 1], -s * p[..., 0] + c * p[..., 2]], -1)


def rotx(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([p[..., 0], c * p[..., 1] - s * p[..., 2], s * p[..., 1] + c * p[..., 2]], -1)


def rotz(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([c * p[..., 0] - s * p[..., 1], s * p[..., 0] + c * p[..., 1], p[..., 2]], -1)


HEAD_POS = np.array([0.12, 0.0, 0.0], f32)
YAW, PITCH, ROLL = -0.40, 0.06, -0.05          # turned toward the window, chin a little down
EYES = [(-0.315, -0.095, 0.585), (0.315, -0.095, 0.585)]
SKIN, EYE, HAT, HAIR, CLOAK, LINEN = range(6)


def to_head(p):
    return rotz(rotx(roty(p - HEAD_POS, -YAW), -PITCH), -ROLL)


def scene(p):
    """returns distances per material group, shape (6, N)"""
    h = to_head(p)
    ax = h.copy(); ax[..., 0] = np.abs(ax[..., 0])          # mirrored features

    # --- skull and face
    d = ell(h, (0, 0.14, -0.08), (0.80, 0.90, 0.93))
    d = smin(d, ell(h, (0, -0.42, 0.16), (0.60, 0.74, 0.60)), 0.22)
    d = smin(d, ell(h, (0, -0.98, 0.36), (0.25, 0.20, 0.23)), 0.20)           # chin
    d = smin(d, ell(ax, (0.36, -0.80, 0.10), (0.26, 0.24, 0.40)), 0.22)       # jaw
    d = smin(d, sph(ax, (0.45, -0.27, 0.42), 0.24), 0.20)
    d = smin(d, ell(ax, (0.40, -0.55, 0.30), (0.26, 0.30, 0.34)), 0.2)                     # cheekbone
    d = smin(d, cap(ax, (0.07, 0.085, 0.76), (0.50, 0.10, 0.56), 0.105, 0.09), 0.13)   # brow
    d = smin(d, ell(h, (0, 0.38, 0.62), (0.50, 0.30, 0.22)), 0.2)             # forehead
    # eye sockets
    d = smax(d, -sph(ax, (0.315, -0.10, 0.86), 0.20), 0.10)
    # temples
    d = smax(d, -sph(ax, (0.90, 0.02, 0.50), 0.22), 0.20)
    # nose
    d = smin(d, cap(h, (0, 0.02, 0.74), (0, -0.36, 0.985), 0.085, 0.115), 0.09)
    d = smin(d, sph(h, (0, -0.405, 1.00), 0.118), 0.05)                       # tip
    d = smin(d, ell(ax, (0.125, -0.435, 0.865), (0.085, 0.075, 0.10)), 0.05)  # alae
    d = smax(d, -ell(ax, (0.075, -0.50, 0.90), (0.045, 0.03, 0.06)), 0.03)    # nostrils
    # naso-labial fold and the hollow under the cheek
    d = smax(d, -cap(ax, (0.19, -0.42, 0.90), (0.33, -0.76, 0.74), 0.03), 0.10)
    # muzzle and lips
    d = smin(d, ell(h, (0, -0.70, 0.60), (0.30, 0.20, 0.22)), 0.12)
    up = ell(h, (0, -0.668, 0.775), (0.215, 0.050, 0.095))
    lo = ell(h, (0, -0.765, 0.765), (0.185, 0.065, 0.095))
    d = smin(d, up, 0.045)
    d = smin(d, lo, 0.045)
    bow = h.copy(); bow[..., 1] += 0.10 * ax[..., 0] ** 2 * 4 - 0.01
    d = smax(d, -ell(bow, (0, -0.716, 0.87), (0.25, 0.007, 0.07)), 0.02)      # the line of the mouth
    d = smax(d, -sph(ax, (0.26, -0.725, 0.76), 0.035), 0.05)                  # corners
    d = smax(d, -ell(h, (0, -0.565, 0.90), (0.035, 0.07, 0.05)), 0.04)        # philtrum
    d = smax(d, -ell(h, (0, -0.865, 0.72), (0.16, 0.035, 0.08)), 0.06)        # under the lower lip
    # lids
    for sx in (-1, 1):
        e = np.array(EYES[0 if sx < 0 else 1], f32)
        q = h - e
        ball = np.sqrt((q * q).sum(-1))
        tilt = q[..., 1] + 0.10 * sx * q[..., 0]
        upper = smax(ball - 0.186, -(tilt - 0.030 + 1.3 * q[..., 0] ** 2 - 0.05 * sx * q[..., 0]), 0.02)
        lower = smax(ball - 0.181, (tilt + 0.058 - 0.9 * q[..., 0] ** 2), 0.02)
        d = smin(d, upper, 0.035)
        d = smin(d, lower, 0.04)
        d = smin(d, ell(h, e + [0.0, -0.15, 0.12], (0.16, 0.035, 0.05)), 0.07)   # the pouch under the eye
    # ears
    d = smin(d, ell(ax, (0.82, -0.14, -0.06), (0.07, 0.25, 0.15)), 0.05)
    # neck
    d = smin(d, cap(h, (0, -0.80, -0.14), (0.05, -2.3, -0.35), 0.44, 0.60), 0.20)
    skin = d

    eye = np.minimum(sph(h, EYES[0], 0.17), sph(h, EYES[1], 0.17))

    # --- hat: a soft velvet beret, pushed back and to one side
    hh = rotz(rotx(h - np.array([0.04, 0.80, -0.10], f32), 0.20), 0.16)
    lump = 0.035 * np.sin(5.0 * hh[..., 0] + 1.0) * np.sin(4.2 * hh[..., 2] + 0.5) + 0.02 * np.sin(11 * hh[..., 0]) * np.sin(9 * hh[..., 2])
    hat = ell(hh, (0, 0.05, 0), (1.22, 0.33, 1.15)) + lump
    hat = smin(hat, ell(hh, (0, -0.20, 0.02), (0.90, 0.20, 0.95)), 0.12)      # band

    # --- hair: loose curls at the temples and the nape
    curl = 0.045 * np.sin(13 * h[..., 0] + 2 * np.sin(7 * h[..., 1])) * np.sin(11 * h[..., 1] + 1.7) * np.sin(9 * h[..., 2] + 0.4)
    curl += 0.02 * np.sin(31 * h[..., 0]) * np.sin(29 * h[..., 1]) * np.sin(23 * h[..., 2])
    hair = ell(ax, (0.80, -0.22, -0.22), (0.30, 0.72, 0.58))
    hair = smin(hair, ell(h, (0, -0.25, -0.75), (0.85, 0.85, 0.45)), 0.2)
    hair = smin(hair, ell(ax, (0.70, 0.30, 0.10), (0.25, 0.30, 0.45)), 0.15) + curl

    # --- body
    b = roty(p - np.array([0.05, 0, -0.35], f32), 0.22)
    cloak = ell(b, (0, -3.35, 0), (2.35, 1.55, 1.05))
    cloak = smin(cloak, ell(b, (0, -2.15, 0.0), (1.05, 0.55, 0.78)), 0.5)
    fold = 0.03 * np.sin(7 * b[..., 0] + 2.5 * np.sin(1.7 * b[..., 1])) * np.clip(-1.9 - b[..., 1], 0, 1)
    cloak = cloak + fold
    # fur edge of the cloak, a soft roll over the shoulders
    fur = cap(np.stack([np.abs(b[..., 0]), b[..., 1], b[..., 2]], -1), (0.30, -2.05, 0.62), (1.55, -3.3, 0.75), 0.22, 0.30)
    fur = fur + 0.03 * np.sin(23 * b[..., 0] + 5 * b[..., 1]) * np.sin(19 * b[..., 1]) * np.sin(17 * b[..., 2])

    # --- linen: a soft collar folded at the throat
    lq = p - np.array([0.20, -1.52, -0.20], f32)
    ring = np.sqrt(lq[..., 0] ** 2 + (lq[..., 2] * 1.1) ** 2)
    rip = 0.012 * np.sin(np.arctan2(lq[..., 2], lq[..., 0]) * 5 + 1.0) + 0.006 * np.sin(np.arctan2(lq[..., 2], lq[..., 0]) * 17)
    linen = np.sqrt(((ring - 0.80) / 3.2) ** 2 + (lq[..., 1] + 0.75 * (ring - 0.55)) ** 2) - 0.05 + rip

    return np.stack([skin, eye, hat, hair, cloak, linen])


def dist(p):
    return scene(p).min(0)


def render():
    cam = np.array([0.0, -0.75, 11.0], f32)
    hw = 1.9
    top = 1.75
    if len(sys.argv) > 3:
        hw, top = 0.95, 0.95
    xs = np.linspace(-hw, hw, WI, dtype=f32)
    ys = np.linspace(top, top - 2 * hw * 4 / 3, HI, dtype=f32)
    px, py = np.meshgrid(xs + (0.1 if len(sys.argv) > 3 else 0), ys)
    tgt = np.stack([px, py, np.zeros_like(px)], -1).reshape(-1, 3)
    rd = tgt - cam
    rd /= np.linalg.norm(rd, axis=1, keepdims=True)
    N = len(rd)
    t = np.full(N, 7.5, f32)
    hit = np.zeros(N, bool)
    act = np.arange(N)
    for i in range(110):
        p = cam + rd[act] * t[act, None]
        d = dist(p)
        t[act] += d * 0.9
        done = d < 0.0015
        hit[act[done]] = True
        act = act[(~done) & (t[act] < 15.5)]
        if len(act) == 0:
            break
    idx = np.flatnonzero(hit)
    P = cam + rd[idx] * t[idx, None]
    g = scene(P)
    mat = g.argmin(0)
    e = 0.004
    k = np.array([[1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]], f32)
    nrm = sum(kk[None, :] * dist(P + kk * e)[:, None] for kk in k)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9

    L = norm([-0.90, 0.62, 0.30])                    # the window: high, left, a little in front
    V = -rd[idx]
    # soft shadow
    sh = np.ones(len(idx), f32)
    ts = np.full(len(idx), 0.03, f32)
    a2 = np.arange(len(idx))
    for i in range(60):
        d = dist(P[a2] + nrm[a2] * 0.01 + L * ts[a2, None])
        sh[a2] = np.minimum(sh[a2], np.clip(5.0 * d / ts[a2], 0, 1))
        ts[a2] += np.clip(d, 0.012, 0.3)
        a2 = a2[(ts[a2] < 5.0) & (sh[a2] > 0.01)]
        if len(a2) == 0:
            break
    ao = np.ones(len(idx), f32)
    for j, hstep in enumerate((0.04, 0.10, 0.22, 0.42)):
        ao -= 0.55 / (j + 1.3) * np.clip(hstep - dist(P + nrm * hstep), 0, 1) / hstep
    ao = np.clip(ao, 0, 1)

    ndl = (nrm * L).sum(1)
    diff = np.clip(ndl * 0.92 + 0.08, 0, 1) * sh
    Hv = L + V; Hv /= np.linalg.norm(Hv, axis=1, keepdims=True)
    ndh = np.clip((nrm * Hv).sum(1), 0, 1)
    rim = (1 - np.clip((nrm * V).sum(1), 0, 1))
    fill = np.clip((nrm * norm([0.75, -0.15, 0.55])).sum(1) * 0.5 + 0.5, 0, 1)   # warm light off the wall

    h = to_head(P)
    alb = np.zeros((len(idx), 3), f32)
    spec = np.zeros(len(idx), f32)
    # skin
    m = mat == SKIN
    skin = np.tile(np.array([0.80, 0.53, 0.34], f32), (len(idx), 1))
    ax = np.abs(h[:, 0])
    red = (0.55 * np.exp(-(((ax - 0.40) / 0.2) ** 2 + ((h[:, 1] + 0.42) / 0.17) ** 2))
           + 0.50 * np.exp(-((h[:, 0] / 0.13) ** 2 + ((h[:, 1] + 0.40) / 0.11) ** 2)) * (h[:, 2] > 0.6)
           + 0.5 * (ax > 0.74) * (h[:, 1] > -0.45)
           + 0.35 * np.exp(-(((ax - 0.315) / 0.2) ** 2 + ((h[:, 1] + 0.12) / 0.11) ** 2)))
    lipm = np.exp(-((h[:, 0] / 0.21) ** 4 + ((h[:, 1] + 0.718) / 0.068) ** 4)) * (h[:, 2] > 0.6)
    red = np.clip(red, 0, 1)
    skin = skin * (1 - red[:, None]) + np.array([0.86, 0.47, 0.36], f32) * red[:, None]
    skin = skin * (1 - lipm[:, None]) + np.array([0.66, 0.25, 0.21], f32) * lipm[:, None]
    beard = np.clip(np.exp(-((h[:, 1] + 0.85) / 0.22) ** 2) * (h[:, 2] > 0.1) * 0.25, 0, 1) * (1 - lipm)   # cooler lower face
    skin = skin * (1 - beard[:, None]) + np.array([0.62, 0.52, 0.44], f32) * beard[:, None]
    browm = np.exp(-(((ax - 0.30) / 0.21) ** 4 + ((h[:, 1] - 0.085 + 0.12 * (ax - 0.3)) / 0.05) ** 2)) * (h[:, 2] > 0.4)
    skin = skin * (1 - 0.85 * browm[:, None]) + np.array([0.16, 0.085, 0.04], f32) * 0.85 * browm[:, None]
    alb[m] = skin[m]
    spec[m] = (0.10 * ndh[m] ** 40 + 0.05 * ndh[m] ** 8) * (1 + 1.6 * lipm[m])
    # eyes
    m = mat == EYE
    gaze = to_head((np.array([-1.0, -0.9, 11.0], f32))[None, :])[0]
    for sx, ec in zip((-1, 1), EYES):
        mm = m & (np.sign(h[:, 0]) == sx)
        q = h[mm] - np.array(ec, f32)
        q /= np.linalg.norm(q, axis=1, keepdims=True)
        gd = gaze - np.array(ec, f32); gd /= np.linalg.norm(gd)
        c = (q * gd).sum(1)
        col = np.tile(np.array([0.55, 0.49, 0.42], f32), (mm.sum(), 1))
        iris = np.clip((c - 0.888) / 0.012, 0, 1)[:, None]
        radial = np.clip((c - 0.888) / (1 - 0.888), 0, 1)[:, None]
        col = col * (1 - iris) + (np.array([0.07, 0.04, 0.02], f32) * (1 - radial) + np.array([0.17, 0.09, 0.04], f32) * radial) * iris
        pup = np.clip((c - 0.978) / 0.004, 0, 1)[:, None]
        col = col * (1 - pup) + np.array([0.02, 0.015, 0.01], f32) * pup
        alb[mm] = col
        spec[mm] = 1.6 * ndh[mm] ** 260 + 0.25 * ndh[mm] ** 30
    m = mat == HAT
    alb[m] = (0.030, 0.022, 0.020); spec[m] = 0.012 * rim[m] ** 2
    m = mat == HAIR
    alb[m] = (0.075, 0.040, 0.018); spec[m] = 0.03 * ndh[m] ** 12
    m = mat == CLOAK
    furm = np.clip((P[:, 2] - 0.05) * 2.0, 0, 1) * np.clip((0.2 + P[:, 1] + 3.3) * 1.0, 0, 1) * np.clip(1.4 - np.abs(np.abs(P[:, 0] - 0.1) - 0.95 - 0.5 * (-2.0 - P[:, 1])), 0, 1)
    ca = np.tile(np.array([0.040, 0.027, 0.020], f32)[None], (len(idx), 1))
    alb[m] = ca[m]; spec[m] = 0.02 * rim[m] ** 3
    m = mat == LINEN
    alb[m] = (0.78, 0.74, 0.62); spec[m] = 0.0

    key = np.array([1.00, 0.88, 0.66], f32) * 1.22
    amb = np.array([0.040, 0.021, 0.010], f32)
    col = alb * (key[None] * diff[:, None] + amb[None] * (0.35 + 1.5 * fill[:, None]) * ao[:, None])
    # blood under the skin at the turning edge of the light
    term = np.exp(-((ndl - 0.05) / 0.22) ** 2) * sh * (mat == SKIN)
    col += term[:, None] * np.array([0.11, 0.022, 0.008], f32)
    col += spec[:, None] * sh[:, None] * key[None] * 0.8

    # the wall
    X = px.reshape(-1); Y = py.reshape(-1)
    bg = (np.array([0.012, 0.008, 0.005], f32)[None]
          + np.array([0.115, 0.080, 0.040], f32)[None] * np.exp(-(((X - 1.25) / 1.5) ** 2 + ((Y + 0.9) / 1.9) ** 2))[:, None]
          + np.array([0.035, 0.03, 0.02], f32)[None] * np.exp(-(((X + 1.6) / 1.0) ** 2 + ((Y + 3.2) / 1.2) ** 2))[:, None])
    img = bg.copy()
    # the body falls away into darkness toward the bottom, as it should
    fall = np.clip((P[:, 1] + 4.6) / 2.6, 0.0, 1) ** 1.3
    col *= np.where(np.isin(mat, (CLOAK,)), fall, 1.0)[:, None]
    img[idx] = col
    img = 1 - np.exp(-1.25 * img)
    img = np.clip(img, 0, 1) ** (1 / 2.0)
    img = img * img * (3 - 2 * img) * 0.55 + img * 0.45
    matimg = np.full(N, -1, np.int8); matimg[idx] = mat
    return img.reshape(HI, WI, 3), matimg.reshape(HI, WI)


if __name__ == "__main__":
    img, mat = render()
    np.save(OUT, img)
    np.save(OUT.replace(".npy", "_mat.npy"), mat)
    from PIL import Image
    Image.fromarray((img * 255).astype(np.uint8)).save(OUT.replace(".npy", ".png"))
    print("saved", OUT, img.shape)
