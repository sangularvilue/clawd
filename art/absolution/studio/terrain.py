"""The valley, built as real terrain and lit, for the landscape study.

A fractal, erosion-like height field (ranges either side of a winding valley,
a lake on its floor, forested shoulders close under the ledge) is ray-marched
from the painter's eye with dawn light coming through the far gap, height
mist in the valley and aerial perspective.  Like the maquette, it is only a
study to paint from.
"""
import math
import numpy as np
from numba import njit, prange

FLOOR = -0.35      # km, valley floor below the eye
PSUN = np.array([0.6, 1.2, -90.0])


@njit(cache=True)
def _h(ix, iy):
    n = (ix * 374761393 + iy * 668265263) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffffff) / 16777215.0


@njit(cache=True)
def noised(x, y):
    ix = math.floor(x); iy = math.floor(y)
    fx = x - ix; fy = y - iy
    ux = fx * fx * (3 - 2 * fx); uy = fy * fy * (3 - 2 * fy)
    dux = 6 * fx * (1 - fx); duy = 6 * fy * (1 - fy)
    a = _h(ix, iy); b = _h(ix + 1, iy); c = _h(ix, iy + 1); d = _h(ix + 1, iy + 1)
    k = a - b - c + d
    return a + (b - a) * ux + (c - a) * uy + k * ux * uy, dux * ((b - a) + k * uy), duy * ((c - a) + k * ux)


@njit(cache=True)
def tfbm(x, y, octv):
    a = 0.0; b = 1.0; dx = 0.0; dy = 0.0
    for i in range(octv):
        n, ddx, ddy = noised(x, y)
        dx += ddx; dy += ddy
        a += b * n / (1.0 + dx * dx + dy * dy)
        b *= 0.5
        x, y = (0.8 * x - 0.6 * y) * 2.0, (0.6 * x + 0.8 * y) * 2.0
    return a


@njit(cache=True)
def sstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


@njit(cache=True)
def axis(z):
    return 0.2 + 0.9 * math.sin((z + 26.0) * 0.28)


@njit(cache=True)
def height(x, z, octv):
    d = abs(x - axis(z))
    left = x < axis(z)
    A = sstep(0.9, 7.5, d) ** 1.3 * (2.3 if left else 2.0)
    A *= sstep(-37.0, -25.0, z)
    n = tfbm(x * 0.33 + 3.1, z * 0.33 + 7.7, octv)
    h = FLOOR + A * (0.22 + 1.05 * n) + 0.02 * n * sstep(0.2, 0.6, d)
    h += 1.7 * math.exp(-((x + 4.6) ** 2 + (z + 14.0) ** 2) / 2.6) * (0.45 + 0.8 * n)          # the great peak on the left
    h += 1.25 * math.exp(-((x - 3.2) ** 2 + (z + 15.0) ** 2) / 1.2) * (0.5 + 0.7 * n)            # three summits on the right
    h += 1.7 * math.exp(-((x - 4.4) ** 2 + (z + 14.2) ** 2) / 1.2) * (0.5 + 0.7 * n)
    h += 1.5 * math.exp(-((x - 5.6) ** 2 + (z + 13.6) ** 2) / 1.3) * (0.5 + 0.7 * n)
    h += 0.36 * math.exp(-((x + 2.3) ** 2 + (z + 2.0) ** 2) / 0.6) * (0.75 + 0.4 * n)          # wooded shoulders under the ledge
    h += 0.33 * math.exp(-((x - 2.1) ** 2 + (z + 2.3) ** 2) / 0.85) * (0.75 + 0.4 * n)
    return h


@njit(cache=True)
def water(x, z):
    """the lake on the valley floor and the river running into it from the gap"""
    e = ((x + 1.9) / 1.9) ** 2 + ((z + 6.4) / 2.5) ** 2 + 0.25 * (tfbm(x * 1.3, z * 1.3, 3) - 0.6)
    if e < 1.0:
        return 1.0
    if z < -8.6 and z > -60.0:
        w = 0.05 + 0.10 * sstep(-27.0, -9.0, z)
        if abs(x - axis(z) - 0.25 * math.sin(z * 1.7)) < w:
            return 1.0
    return 0.0


@njit(cache=True)
def march(ox, oy, oz, dx, dy, dz, t0, tmax):
    t = t0
    lt = t0; lh = oy + dy * t0 - height(ox + dx * t0, oz + dz * t0, 5)
    for i in range(700):
        py = oy + dy * t
        if py > 3.6 and dy > 0:
            return -1.0
        hh = py - height(ox + dx * t, oz + dz * t, 5)
        if hh < 0:
            a = lt; b = t
            for k in range(8):
                m = 0.5 * (a + b)
                if oy + dy * m - height(ox + dx * m, oz + dz * m, 7) < 0:
                    b = m
                else:
                    a = m
            return 0.5 * (a + b)
        lt = t; lh = hh
        t += max(0.008, min(0.012 * t, 0.4 * hh))
        if t > tmax:
            return -1.0
    return -1.0


@njit(cache=True)
def shade(px, py, pz, t, rdx, rdy, rdz, col):
    e = max(0.0015 * t, 0.002)
    h0 = height(px, pz, 9)
    nx = h0 - height(px + e, pz, 9); nz = h0 - height(px, pz + e, 9); ny = e
    nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
    alt = py - FLOOR
    t1 = tfbm(px * 1.6 + 9.0, pz * 1.6, 3)
    t2 = tfbm(px * 55.0, pz * 55.0, 2)
    rock = sstep(0.60, 0.40, ny + 0.12 * (t1 - 0.5))
    forest = sstep(0.75, 0.30, alt + 0.45 * (t1 - 0.55)) * sstep(0.50, 0.72, ny) * sstep(0.02, 0.06, alt)
    ar, ag, ab = 0.90, 0.92, 0.98
    ar = ar * (1 - rock) + 0.17 * rock; ag = ag * (1 - rock) + 0.16 * rock; ab = ab * (1 - rock) + 0.20 * rock
    f = forest * (0.88 + 0.12 * sstep(0.25, 0.6, t2))
    ar = ar * (1 - f) + 0.035 * f; ag = ag * (1 - f) + 0.055 * f; ab = ab * (1 - f) + 0.055 * f
    lx = PSUN[0] - px; ly = PSUN[1] - py; lz = PSUN[2] - pz
    ll = math.sqrt(lx * lx + ly * ly + lz * lz); lx /= ll; ly /= ll; lz /= ll
    # the glow of the gap: faces turned toward the valley take the light
    lx += 0.95 * (1.0 if px < axis(pz) else -1.0); ly += 0.22
    ll = math.sqrt(lx * lx + ly * ly + lz * lz); lx /= ll; ly /= ll; lz /= ll
    ndl = max(nx * lx + ny * ly + nz * lz, 0.0)
    sh = 1.0
    if ndl > 0:
        s = 0.05
        for k in range(26):
            hh = py + ly * s + 0.01 - height(px + lx * s, pz + lz * s, 5)
            if hh < 0:
                sh = 0.0
                break
            sh = min(sh, 10.0 * hh / s)
            s += max(0.04, 0.5 * hh)
            if s > 9.0:
                break
    sun = 3.4 * (0.10 + 0.90 * sstep(0.15, 1.5, alt)) * ndl ** 0.7 * max(sh, 0.0)
    sky = 0.5 + 0.5 * ny
    col[0] = ar * (1.00 * sun + 0.36 * sky + 0.08)
    col[1] = ag * (0.66 * sun + 0.40 * sky + 0.08)
    col[2] = ab * (0.50 * sun + 0.60 * sky + 0.10)
    return forest, ny


@njit(cache=True)
def fog(col, t, oy, dy, rdx, rdy, rdz):
    Hm = 0.16
    b = max(abs(dy) * t / Hm, 1e-4)
    od = 0.28 * t * math.exp(-(oy - FLOOR) / Hm) * (1 - math.exp(-b)) / b if dy > 0 else \
        0.28 * t * math.exp(-(oy + dy * t - FLOOR) / Hm) * (1 - math.exp(-b)) / b
    f = 1 - math.exp(-t * 0.034 - od * 0.5)
    sl = math.sqrt(PSUN[0] ** 2 + PSUN[1] ** 2 + PSUN[2] ** 2)
    c = max((rdx * PSUN[0] + rdy * PSUN[1] + rdz * PSUN[2]) / sl, 0.0)
    w = c ** 10
    w2 = c ** 90
    fr = 0.55 * (1 - w) + 1.00 * w + 0.10 * w2; fg = 0.55 * (1 - w) + 0.80 * w + 0.12 * w2; fb = 0.74 * (1 - w) + 0.60 * w + 0.10 * w2
    col[0] = col[0] * (1 - f) + fr * f; col[1] = col[1] * (1 - f) + fg * f; col[2] = col[2] * (1 - f) + fb * f


@njit(parallel=True, cache=True)
def render(w, h, step, f, cx, cy, sky):
    rgb = np.zeros((h, w, 3), np.float32); hit = np.zeros((h, w), np.float32)
    depth = np.zeros((h, w), np.float32); forest = np.zeros((h, w), np.float32); wat = np.zeros((h, w), np.float32)
    for j in prange(h):
        col = np.zeros(3); c2 = np.zeros(3)
        for i in range(w):
            sx = i * step; sy = j * step
            dx = (sx - cx) / f; dy = -(sy - cy) / f; dz = -1.0
            dl = math.sqrt(dx * dx + dy * dy + 1); dx /= dl; dy /= dl; dz /= dl
            t = march(0.0, 0.0, 0.0, dx, dy, dz, 0.25, 70.0)
            if t < 0:
                continue
            px = dx * t; py = dy * t; pz = dz * t
            fo, ny = shade(px, py, pz, t, dx, dy, dz, col)
            wm = water(px, pz) if py < FLOOR + 0.012 else 0.0
            if wm > 0:
                # still water and black ice: the mountains and the sky stand in it
                t2 = march(px, FLOOR + 0.002, pz, dx, -dy, dz, 0.05, 60.0)
                if t2 > 0:
                    shade(px + dx * t2, FLOOR - dy * t2, pz + dz * t2, t + t2, dx, -dy, dz, c2)
                    fog(c2, t + t2, 0.0, -dy, dx, -dy, dz)
                else:
                    jj = int(min(max((2 * cy - sy) / step, 0), sky.shape[0] - 1))
                    c2[0] = sky[jj, i, 0]; c2[1] = sky[jj, i, 1]; c2[2] = sky[jj, i, 2]
                ice = sstep(0.50, 0.62, tfbm(px * 2.2 + 4.0, pz * 2.2, 4)) * sstep(-0.2, -1.6, px)
                col[0] = (c2[0] * 0.80 + 0.01) * (1 - ice) + 0.50 * ice
                col[1] = (c2[1] * 0.80 + 0.015) * (1 - ice) + 0.56 * ice
                col[2] = (c2[2] * 0.84 + 0.03) * (1 - ice) + 0.74 * ice
                fo = 0.0
            fog(col, t, 0.0, dy, dx, dy, dz)
            rgb[j, i, 0] = col[0]; rgb[j, i, 1] = col[1]; rgb[j, i, 2] = col[2]
            hit[j, i] = 1.0; depth[j, i] = t; forest[j, i] = fo; wat[j, i] = wm
    return rgb, hit, depth, forest, wat
