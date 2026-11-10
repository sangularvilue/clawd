#!/usr/bin/env python3
"""
Self-portrait as a vanitas still life - stage 1, the study.

A table by a north window: three old books, a letter leaning against them,
a candle burning down in a brass stick, a quill, and a mirrored glass ball.
The Dutch still-life painters put themselves into such pictures as a tiny
reflection at the easel. Here the ball reflects the room, the window, the
easel and the stool - and no one.

Everything is a signed-distance field, sphere-traced, lit by the window and
the flame, with one bounce of reflection for the ball and the brass.
Stage 2 (old_master_paint.py) paints from this study.

usage: python3 vanitas_model.py [width] [out.npy]
"""
import sys
import numpy as np
from scipy import ndimage as ndi

WI = int(sys.argv[1]) if len(sys.argv) > 1 else 600
OUT = sys.argv[2] if len(sys.argv) > 2 else "vanitas.npy"
HI = WI * 4 // 3
f32 = np.float32


def norm(v):
    v = np.asarray(v, f32)
    return v / np.linalg.norm(v)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def box(p, c, b, r=0.0):
    q = np.abs(p - np.asarray(c, f32)) - (np.asarray(b, f32) - r)
    return np.sqrt((np.maximum(q, 0) ** 2).sum(-1)) + np.minimum(q.max(-1), 0) - r


def sph(p, c, r):
    return np.sqrt(((p - np.asarray(c, f32)) ** 2).sum(-1)) - r


def ell(p, c, r):
    q = (p - np.asarray(c, f32)) / np.asarray(r, f32)
    k0 = np.sqrt((q * q).sum(-1))
    k1 = np.sqrt(((q / np.asarray(r, f32)) ** 2).sum(-1)) + 1e-9
    return k0 * (k0 - 1) / k1


def cap(p, a, b, ra, rb=None):
    a = np.asarray(a, f32); b = np.asarray(b, f32)
    rb = ra if rb is None else rb
    pa, ba = p - a, b - a
    h = np.clip((pa * ba).sum(-1) / (ba * ba).sum(), 0, 1)
    return np.sqrt(((pa - ba * h[..., None]) ** 2).sum(-1)) - (ra + (rb - ra) * h)


def cyl(p, c, r, h, rr=0.0):
    q = p - np.asarray(c, f32)
    dx = np.sqrt(q[..., 0] ** 2 + q[..., 2] ** 2) - (r - rr)
    dy = np.abs(q[..., 1]) - (h - rr)
    return np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) + np.minimum(np.maximum(dx, dy), 0) - rr


def roty(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([c * p[..., 0] + s * p[..., 2], p[..., 1], -s * p[..., 0] + c * p[..., 2]], -1)


def rotx(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([p[..., 0], c * p[..., 1] - s * p[..., 2], s * p[..., 1] + c * p[..., 2]], -1)


TABLE, BOOK1, BOOK2, BOOK3, PAGES, LETTER, WAX, BRASS, BALL, FLAME, QUILL, ROOM = range(12)
BOOKS = [  # centre, half-size, turn about y
    ((-0.42, 0.185, 0.18), (1.02, 0.185, 0.68), 0.20),
    ((-0.38, 0.515, 0.12), (0.86, 0.145, 0.60), np.pi - 0.22),
    ((-0.52, 0.765, 0.10), (0.60, 0.105, 0.44), 0.55),
]
BALL_C, BALL_R = np.array([1.02, 0.60, 0.98], f32), 0.60
CANDLE = np.array([0.42, 0.0, -1.05], f32)
FLAME_C = CANDLE + np.array([0.0, 2.36, 0.0], f32)
LET_BASE, LET_YAW, LET_TILT = np.array([-1.02, 0.0, 1.30], f32), 0.30, -0.40


def book_local(p, i):
    c, b, a = BOOKS[i]
    return roty(p - np.asarray(c, f32), -a), np.asarray(b, f32)


def book(p, i):
    q, b = book_local(p, i)
    ct = 0.028
    cov = np.minimum(box(q, (0, b[1] - ct / 2, 0), (b[0], ct / 2, b[2]), 0.008),
                     box(q, (0, -b[1] + ct / 2, 0), (b[0], ct / 2, b[2]), 0.008))
    spine = box(q, (0, 0, b[2] - 0.03), (b[0], b[1], 0.03), 0.028)
    bands = sum(np.exp(-((q[..., 0] - xb * b[0]) / 0.022) ** 2) for xb in (-0.62, -0.2, 0.2, 0.62))
    spine = spine - 0.014 * bands * (q[..., 2] > b[2] - 0.1)
    cov = np.minimum(cov, spine)
    pages = box(q, (0, 0, -0.035), (b[0] - 0.045, b[1] - ct, b[2] - 0.05), 0.004)
    pages = pages + 0.0025 * np.sin(q[..., 1] * 260)
    return cov, pages


def letter_local(p):
    return rotx(roty(p - LET_BASE, -LET_YAW), -LET_TILT)


def scene(p):
    out = np.full((12,) + p.shape[:-1], 1e3, f32)
    out[TABLE] = np.minimum(box(p, (0, -0.16, -0.6), (7, 0.16, 2.7), 0.025), box(p, (0, -1.6, -0.9), (7, 1.3, 2.75), 0.02))
    pages = np.full(p.shape[:-1], 1e3, f32)
    for i, g in enumerate((BOOK1, BOOK2, BOOK3)):
        cv, pg = book(p, i)
        out[g] = cv
        pages = np.minimum(pages, pg)
    out[PAGES] = pages
    q = letter_local(p)
    bend = 0.05 * (q[..., 0] / 0.43) ** 2 + 0.03 * np.sin(q[..., 1] * 4.0)       # paper never lies flat
    qq = q.copy(); qq[..., 2] -= bend
    out[LETTER] = box(qq, (0, 0.63, 0), (0.43, 0.63, 0.007)) * 0.8
    c = p - CANDLE
    rad = np.sqrt(c[..., 0] ** 2 + c[..., 2] ** 2)
    wax = cyl(c, (0, 1.58, 0), 0.10, 0.52, 0.02)
    wax = np.maximum(wax, -sph(c, (0, 2.13, 0), 0.075))                          # the burnt hollow
    drip = cap(c, (0.095, 2.02, 0.03), (0.105, 1.55, 0.035), 0.022, 0.03)
    drip = np.minimum(drip, cap(c, (-0.05, 2.05, 0.085), (-0.055, 1.78, 0.095), 0.018, 0.026))
    out[WAX] = np.minimum(smin(wax, drip, 0.03), cap(c, (0, 2.06, 0), (0.012, 2.17, 0), 0.008))
    br = cyl(c, (0, 0.035, 0), 0.40, 0.035, 0.02)
    br = smin(br, cyl(c, (0, 0.11, 0), 0.26, 0.05, 0.03), 0.05)
    br = smin(br, cap(c, (0, 0.1, 0), (0, 0.98, 0), 0.06, 0.05), 0.05)
    for yk, rk in ((0.36, 0.125), (0.62, 0.10), (0.80, 0.085)):
        br = smin(br, ell(c, (0, yk, 0), (rk, rk * 0.7, rk)), 0.03)
    br = smin(br, cyl(c, (0, 1.0, 0), 0.30, 0.018, 0.015), 0.04)
    br = np.minimum(br, np.maximum(cyl(c, (0, 1.09, 0), 0.135, 0.08, 0.01), -(rad - 0.10)))
    out[BRASS] = br
    out[BALL] = sph(p, BALL_C, BALL_R)
    out[FLAME] = ell(c, (0.006, 2.345, 0), (0.05 , 0.175, 0.05)) + 0.02 * np.clip(2.30 - c[..., 1], 0, 1)
    sh = cap(p, (-0.62, 0.028, 1.86), (0.78, 0.05, 1.70), 0.012, 0.02)
    qv = roty(p - np.array([0.02, 0.055, 1.78], f32), -0.114)
    vane = ell(qv, (0, 0, 0), (0.50, 0.012, 0.085)) + 0.004 * np.sin(qv[..., 0] * 70 + qv[..., 2] * 40)
    out[QUILL] = np.minimum(sh, vane)
    # the room behind the viewer: an easel, a canvas seen from the back, an empty stool
    e = roty(p - np.array([1.35, 0, 11.9], f32), 0.45)
    room = box(e, (0, 2.55, 0), (0.95, 1.25, 0.04))
    room = np.minimum(room, cap(e, (-0.8, 0, 0.15), (-0.55, 4.3, -0.1), 0.05))
    room = np.minimum(room, cap(e, (0.8, 0, 0.15), (0.55, 4.3, -0.1), 0.05))
    room = np.minimum(room, cap(e, (0, 0, -1.1), (0, 4.2, -0.1), 0.05))
    room = np.minimum(room, box(e, (0, 1.25, 0.1), (1.0, 0.05, 0.1)))
    s = p - np.array([-0.15, 0, 11.6], f32)
    room = np.minimum(room, cyl(s, (0, 1.22, 0), 0.42, 0.045, 0.02))
    for ax_, az_ in ((0.3, 0.3), (-0.3, 0.3), (0.3, -0.3), (-0.3, -0.3)):
        room = np.minimum(room, cap(s, (ax_ * 1.25, 0, az_ * 1.25), (ax_ * 0.8, 1.2, az_ * 0.8), 0.035))
    out[ROOM] = room
    return out


def dist(p):
    return scene(p).min(0)


def march(ro, rd, tmax=40.0, steps=120, t0=0.0):
    N = len(rd)
    t = np.full(N, t0, f32)
    hit = np.zeros(N, bool)
    act = np.arange(N)
    for _ in range(steps):
        d = dist(ro[act] + rd[act] * t[act, None])
        t[act] += d * 0.92
        done = d < 0.0012
        hit[act[done]] = True
        act = act[(~done) & (t[act] < tmax)]
        if len(act) == 0:
            break
    return t, hit


L = norm([-0.74, 0.56, 0.38])
KEY = np.array([1.00, 0.93, 0.80], f32) * 1.55
FLAMECOL = np.array([1.0, 0.50, 0.16], f32)
AMB = np.array([0.050, 0.036, 0.024], f32)


def env(ro, rd):
    """the room: back wall with the fall of window light, the window itself, darkness elsewhere"""
    col = np.zeros((len(rd), 3), f32)
    best = np.full(len(rd), 1e9, f32)
    which = np.zeros(len(rd), np.int8)
    planes = ((2, -2.7), (0, -6.5), (0, 7.5), (2, 16.0), (1, 8.0), (1, -3.2))
    for i, (ax, v) in enumerate(planes):
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (v - ro[:, ax]) / rd[:, ax]
        ok = (t > 1e-3) & (t < best)
        best[ok] = t[ok]; which[ok] = i
    P = ro + rd * best[:, None]
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # back wall
    m = which == 0
    fall = 1 / (1 + np.exp(-((x * 0.50 - (y - 2.25) * 0.86) * 1.9)))             # the diagonal of the window's light
    fall = fall * (0.55 + 0.45 * np.exp(-((x - 1.4) / 3.0) ** 2))
    plaster = np.array([0.36, 0.30, 0.215], f32)
    df = P - FLAME_C
    fl = 0.9 / ((df * df).sum(1) + 0.9)
    wall = plaster[None] * (0.030 + 0.36 * fall[:, None]) * KEY[None] + plaster[None] * fl[:, None] * FLAMECOL[None] * 1.1
    col[m] = wall[m]
    # window wall
    m = which == 1
    win = (np.abs(z - 5.2) < 2.3) & (np.abs(y - 4.2) < 2.6)
    bars = (np.abs(((z - 5.2 + 2.3) % 1.15) - 0.575) > 0.52) | (np.abs(((y - 4.2 + 2.6) % 1.3) - 0.65) > 0.60)
    sky = np.array([3.4, 3.7, 4.2], f32)[None] * (0.75 + 0.25 * np.clip((y - 2) / 4, 0, 1))[:, None]
    wcol = np.where((win & ~bars)[:, None], sky, np.array([0.035, 0.028, 0.02], f32)[None])
    col[m] = wcol[m]
    for i, c in ((2, (0.05, 0.04, 0.028)), (3, (0.06, 0.047, 0.032)), (4, (0.03, 0.024, 0.018)), (5, (0.07, 0.05, 0.03))):
        m = which == i
        lit = 1.0 + (2.5 * np.exp(-(((x + 1.5) / 3.5) ** 2 + ((z - 6) / 3.5) ** 2)) if i == 5 else 0.0) * np.ones(len(rd), f32)
        col[m] = (np.array(c, f32)[None] * lit[:, None])[m]
    return col


def shade(P, rd, with_shadow=True):
    g = scene(P)
    mat = g.argmin(0)
    e = 0.003
    k = np.array([[1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]], f32)
    N = sum(kk[None, :] * dist(P + kk * e)[:, None] for kk in k)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    V = -rd
    n = len(P)
    sh = np.ones(n, f32)
    if with_shadow:
        ts = np.full(n, 0.02, f32)
        a2 = np.arange(n)
        for _ in range(64):
            d = dist(P[a2] + N[a2] * 0.012 + L * ts[a2, None])
            sh[a2] = np.minimum(sh[a2], np.clip(7.0 * d / ts[a2], 0, 1))
            ts[a2] += np.clip(d, 0.012, 0.35)
            a2 = a2[(ts[a2] < 7.0) & (sh[a2] > 0.01)]
            if len(a2) == 0:
                break
    ao = np.ones(n, f32)
    for j, hs in enumerate((0.03, 0.09, 0.2, 0.42)):
        ao -= 0.5 / (j + 1.3) * np.clip(hs - dist(P + N * hs), 0, 1) / hs
    ao = np.clip(ao, 0, 1)
    ndl = (N * L).sum(1)
    diff = np.clip(ndl, 0, 1) * sh
    Hv = L + V; Hv /= np.linalg.norm(Hv, axis=1, keepdims=True)
    ndh = np.clip((N * Hv).sum(1), 0, 1)
    fd = FLAME_C - P
    fr2 = (fd * fd).sum(1)
    fdir = fd / np.sqrt(fr2)[:, None]
    fdiff = np.clip((N * fdir).sum(1) * 0.8 + 0.2, 0, 1) * 0.55 / (fr2 + 0.35)

    alb = np.zeros((n, 3), f32)
    spec = np.zeros(n, f32); shin = np.full(n, 20.0, f32)
    emis = np.zeros((n, 3), f32)
    refl = np.zeros(n, f32)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]

    m = mat == TABLE
    grain = np.sin(z * 34 + 3.0 * np.sin(x * 1.3 + 2 * np.sin(z * 2.1)) + 1.5 * np.sin(x * 0.4)) * 0.5 + 0.5
    fine = np.sin(z * 240 + 6 * np.sin(x * 3.0)) * 0.5 + 0.5
    wood = np.array([0.150, 0.075, 0.034], f32)[None] * (0.75 + 0.3 * grain[:, None] ** 2) * (0.93 + 0.1 * fine[:, None])
    wood = wood * np.where((y < -0.02)[:, None], 0.55, 1.0)
    alb[m] = wood[m]; spec[m] = 0.10; shin[m] = 30
    for i, (gid, base, sp) in enumerate(((BOOK1, (0.27, 0.060, 0.045), 0.22), (BOOK2, (0.070, 0.082, 0.058), 0.16), (BOOK3, (0.50, 0.375, 0.215), 0.10))):
        m = mat == gid
        if not m.any():
            continue
        q, b = book_local(P[m], i)
        c = np.tile(np.array(base, f32), (m.sum(), 1))
        wear = 0.5 + 0.5 * np.sin(q[:, 0] * 9 + 4 * np.sin(q[:, 2] * 5 + i)) * np.sin(q[:, 2] * 7 + 2 * i)
        c = c * (0.8 + 0.35 * wear[:, None])
        edge = np.clip(1 - (b[0] - np.abs(q[:, 0])) / 0.05, 0, 1) + np.clip(1 - (b[2] - np.abs(q[:, 2])) / 0.05, 0, 1) * (np.abs(q[:, 1]) > b[1] - 0.04)
        c = c * (1 + 0.5 * np.clip(edge, 0, 1)[:, None])                                # rubbed corners
        onspine = q[:, 2] > b[2] - 0.03
        gold = np.zeros(m.sum(), bool)
        for xb in (-0.62, -0.2, 0.2, 0.62):
            dxb = np.abs(q[:, 0] - xb * b[0])
            gold |= (np.abs(dxb - 0.05) < 0.007)
        gold |= (np.abs(q[:, 0]) < 0.15 * b[0]) & (np.abs(np.abs(q[:, 1]) - 0.35 * b[1]) < 0.009)
        gold &= onspine & (i != 1)
        c[gold] = (0.62, 0.43, 0.13)
        alb[m] = c
        s_ = np.full(m.sum(), sp, f32); s_[gold] = 0.8
        spec[m] = s_; shin[m] = 26
    m = mat == PAGES
    pg = np.array([0.66, 0.56, 0.385], f32)[None] * (0.78 + 0.22 * np.sin(y * 300 + 2 * np.sin(x * 7 + z * 5)))[:, None]
    pg = pg * (0.85 + 0.15 * np.sin(x * 23 + z * 17) * np.sin(y * 40))[:, None]
    alb[m] = pg[m]
    m = mat == LETTER
    if m.any():
        q = letter_local(P[m])
        u, v = q[:, 0], q[:, 1]
        paper = np.tile(np.array([0.80, 0.735, 0.585], f32), (m.sum(), 1))
        paper *= (0.92 + 0.08 * np.sin(u * 13 + 3 * np.sin(v * 7)) * np.sin(v * 9))[:, None]
        paper *= (1 - 0.18 * np.exp(-((np.abs(v - 0.63) - 0.0) / 0.012) ** 2))[:, None]   # the fold
        line = (1.14 - v) / 0.073
        li = np.floor(line)
        fv = (line - li - 0.5) * 0.073
        script = 0.017 * np.sin(u * 92 + li * 1.7 + 2.2 * np.sin(u * 37 + li)) * (0.6 + 0.4 * np.sin(u * 23 + li * 5))
        asc = 0.02 * np.maximum(0, np.sin(u * 41 + li * 3.1)) ** 8
        ink = np.abs(fv - script - asc) < 0.0052
        words = np.sin(u * 15.5 + li * 2.3 + 1.5 * np.sin(li * 7.7)) > -0.62
        right = 0.35 - 0.20 * (np.sin(li * 5.3) > 0.55) - 0.35 * (li == 13)
        ink &= words & (u > -0.35 + 0.06 * (li == 0)) & (u < right) & (li >= 1) & (li <= 13)
        paper[ink] = paper[ink] * 0.22 + np.array([0.035, 0.022, 0.012], f32)
        seal = np.hypot(u - 0.21, (v - 0.115)) < 0.062 + 0.008 * np.sin(np.arctan2(v - 0.115, u - 0.21) * 5)
        paper[seal] = (0.52, 0.045, 0.035)
        alb[m] = paper
        s_ = np.zeros(m.sum(), f32); s_[seal] = 0.5
        spec[m] = s_
    m = mat == WAX
    cy = y - CANDLE[1]
    waxc = np.array([0.80, 0.735, 0.56], f32)[None] * np.ones((n, 1), f32)
    wick = (cy > 2.07) & (np.hypot(x - CANDLE[0], z - CANDLE[2]) < 0.03)
    waxc[wick] = (0.03, 0.02, 0.015)
    alb[m] = waxc[m]; spec[m] = 0.08
    glow = np.exp(-np.clip(2.12 - cy, 0, 9) / 0.33) * 0.85                            # light soaking down through the wax
    emis[m] = (glow[:, None] * np.array([1.0, 0.52, 0.16], f32)[None])[m] * (~wick[m])[:, None]
    m = mat == BRASS
    alb[m] = (0.30, 0.19, 0.055); spec[m] = 1.3; shin[m] = 70; refl[m] = 0.55
    m = mat == BALL
    alb[m] = (0.012, 0.012, 0.014); spec[m] = 0.0; refl[m] = 0.90
    m = mat == FLAME
    fy = np.clip((y - (FLAME_C[1] - 0.19)) / 0.36, 0, 1)
    fcol = np.array([2.2, 1.9, 2.6], f32)[None] * (1 - fy[:, None]) ** 3 * 0.5 + np.array([7.5, 5.2, 2.2], f32)[None] * np.clip(fy * 2.2, 0.25, 1)[:, None]
    emis[m] = fcol[m]
    m = mat == QUILL
    barb = 0.82 + 0.18 * np.sin((x * 0.75 + np.abs(z - 1.775) * 1.3) * 150)
    alb[m] = (np.array([0.70, 0.66, 0.57], f32)[None] * barb[:, None])[m]; spec[m] = 0.05
    m = mat == ROOM
    rc = np.where((y > 1.3)[:, None] & (z > 12.0)[:, None], np.array([0.62, 0.52, 0.36], f32)[None], np.array([0.24, 0.14, 0.07], f32)[None])
    alb[m] = rc[m]

    col = alb * (KEY[None] * diff[:, None] + AMB[None] * ao[:, None] + FLAMECOL[None] * (fdiff * ao)[:, None] * 1.5)
    col += (spec * ndh ** shin * sh)[:, None] * KEY[None] * np.where((mat == BRASS)[:, None], np.array([1.0, 0.72, 0.30], f32)[None], 1.0)
    Hf = fdir + V; Hf /= np.linalg.norm(Hf, axis=1, keepdims=True)
    col += (spec * np.clip((N * Hf).sum(1), 0, 1) ** shin * 0.5 / (fr2 + 0.4))[:, None] * FLAMECOL[None] * 2.0
    col += emis
    return col, mat, N, refl


def render():
    cam = np.array([0.0, 2.75, 10.5], f32)
    tgt = np.array([0.06, 1.26, 0.0], f32)
    fw = norm(tgt - cam)
    rt = norm(np.cross(fw, [0, 1, 0]))
    upv = np.cross(rt, fw)
    D = np.linalg.norm(tgt - cam)
    hw = 1.86
    u = np.linspace(-hw, hw, WI, dtype=f32)
    v = np.linspace(hw * 4 / 3, -hw * 4 / 3, HI, dtype=f32)
    uu, vv = np.meshgrid(u, v)
    rd = fw[None] * D + uu.reshape(-1, 1) * rt[None] + vv.reshape(-1, 1) * upv[None]
    rd = (rd / np.linalg.norm(rd, axis=1, keepdims=True)).astype(f32)
    ro = np.tile(cam, (len(rd), 1))
    print("primary"); sys.stdout.flush()
    t, hit = march(ro, rd, tmax=22.0, t0=6.0)
    img = env(ro, rd)
    idx = np.flatnonzero(hit)
    P = ro[idx] + rd[idx] * t[idx, None]
    print("shading", len(idx)); sys.stdout.flush()
    col, mat, N, refl = shade(P, rd[idx])
    # one bounce for the ball and the brass
    r = np.flatnonzero(refl > 0)
    print("reflections", len(r)); sys.stdout.flush()
    I = rd[idx][r]
    R = I - 2 * (I * N[r]).sum(1, keepdims=True) * N[r]
    R /= np.linalg.norm(R, axis=1, keepdims=True)
    ro2 = P[r] + N[r] * 0.01
    t2, hit2 = march(ro2, R, tmax=30.0, steps=140)
    rc = env(ro2, R)
    h2 = np.flatnonzero(hit2)
    if len(h2):
        c2, m2, _, _ = shade(ro2[h2] + R[h2] * t2[h2, None], R[h2])
        rc[h2] = c2
    fres = refl[r] + (1 - refl[r]) * (1 - np.clip(-(I * N[r]).sum(1), 0, 1)) ** 5
    tint = np.where((mat[r] == BRASS)[:, None], np.array([1.0, 0.70, 0.30], f32)[None], np.array([0.93, 0.92, 0.90], f32)[None])
    col[r] = col[r] + rc * tint * fres[:, None]
    img[idx] = col
    matimg = np.full(len(rd), -1, np.int8); matimg[idx] = mat
    img = img.reshape(HI, WI, 3)
    # the flame's halo in the air of the room
    bright = np.clip(img - 1.2, 0, 6) * (matimg.reshape(HI, WI) == FLAME)[..., None]
    s = WI / 600
    halo = sum(ndi.gaussian_filter(bright, (sg * s, sg * s, 0)) * w for sg, w in ((4, 0.5), (14, 0.7), (45, 0.8)))
    img = img + halo * np.array([1.0, 0.62, 0.28], f32)
    img = 1 - np.exp(-1.15 * img)
    img = np.clip(img, 0, 1) ** (1 / 2.0)
    img = img * img * (3 - 2 * img) * 0.5 + img * 0.5
    return img, matimg.reshape(HI, WI)


if __name__ == "__main__":
    img, mat = render()
    np.save(OUT, img)
    # for the painter: 1 = finest handling (ball, flame), 5 = paper, 0 = other objects, -1 = wall and table
    pm = np.full(mat.shape, -1, np.int8)
    pm[np.isin(mat, (BOOK1, BOOK2, BOOK3, PAGES, WAX, BRASS, QUILL))] = 0
    pm[np.isin(mat, (BALL, FLAME))] = 1
    pm[mat == LETTER] = 5
    np.save(OUT.replace(".npy", "_mat.npy"), pm)
    from PIL import Image
    Image.fromarray((img * 255).astype(np.uint8)).save(OUT.replace(".npy", ".png"))
    print("saved", OUT, img.shape)
