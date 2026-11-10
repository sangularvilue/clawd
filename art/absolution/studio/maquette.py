"""The maquette: a small 'clay' model of the figure group, posed in 3D and lit
by a low sun from behind, as painters from Tintoretto to Poussin built wax
figures on a little stage to study the fall of light before painting.
Signed-distance modelling + ray marching.  Output is only a reference study;
no pixel of it reaches the canvas except through a brush stroke.
"""
import math
import sys
import numpy as np
from numba import njit, prange

W0, H0 = 3840, 2160
F, CX, CY = 4200.0, 2000.0, 1090.0
EYE = np.array([0.0, 0.95, 7.0])
SUNPX = (2032.0, 1058.0)
SUN = np.array([(SUNPX[0] - CX) / F, (CY - SUNPX[1]) / F, -1.0]); SUN /= np.linalg.norm(SUN)
SUNG = np.array([(SUNPX[0] - CX) / F, 0.035, -1.0]); SUNG /= np.linalg.norm(SUNG)   # for ground shadows

SKIN, SHIRT, TROUS, HAIR, CLOAK, CASS, STOLE, WHITE, WOOD, CORPUS, SNOW, BARK, GOLD, LINEN = range(14)
ALBEDO = np.array([
    (0.80, 0.60, 0.50), (0.86, 0.83, 0.76), (0.26, 0.20, 0.17), (0.15, 0.105, 0.085), (0.74, 0.075, 0.06),
    (0.095, 0.09, 0.105), (0.43, 0.17, 0.60), (0.86, 0.86, 0.89), (0.21, 0.155, 0.125), (0.70, 0.61, 0.53),
    (0.90, 0.92, 0.98), (0.23, 0.175, 0.14), (0.85, 0.65, 0.25), (0.88, 0.87, 0.84)], np.float64)


def proj(X, Y, Z):
    d = EYE[2] - Z
    return CX + F * (X - EYE[0]) / d, CY - F * (Y - EYE[1]) / d


P = []


def cap(a, b, r1, r2, mat, grp, k=0.03):
    P.append([0, *a, *b, r1, r2, 0, 0, mat, grp, k])


def ell(c, r, rot, mat, grp, k=0.03, famp=0.0, ffreq=0.0):
    P.append([1, *c, *r, rot, 0, famp, ffreq, mat, grp, k])


def slab(a, b, zc, th, hw, mat, grp, k=0.03, famp=0.0, ffreq=0.0):
    P.append([2, a[0], a[1], zc, b[0], b[1], 0, th, hw, famp, ffreq, mat, grp, k])


def box(c, h, rot, rnd, mat, grp, k=0.0):
    P.append([3, *c, *h, rot, rnd, 0, 0, mat, grp, k])


def head(c, pitch, f, old, gskin, ghair, neck):
    ph = math.radians(pitch)

    def w(lx, ly, z=0.0):
        return (c[0] + f * (lx * math.cos(ph) - ly * math.sin(ph)), c[1] + lx * math.sin(ph) + ly * math.cos(ph), c[2] + z)
    rot = f * ph
    ell(w(0, 0.02), (0.098, 0.105, 0.078), rot, SKIN, gskin, 0.02)
    ell(w(0.036, -0.048), (0.060, 0.082, 0.060), rot, SKIN, gskin, 0.025)
    cap(w(0.086, 0.004), w(0.118, -0.036), 0.013, 0.012, SKIN, gskin, 0.012)
    ell(w(0.082, 0.026), (0.020, 0.013, 0.050), rot, SKIN, gskin, 0.012)
    ell(w(0.066, -0.112), (0.030, 0.028, 0.034), rot, SKIN, gskin, 0.02)
    ell(w(0.086, -0.066), (0.016, 0.012, 0.026), rot, SKIN, gskin, 0.012)      # lips
    for s in (-1, 1):
        ell(w(-0.012, -0.012, s * 0.078), (0.016, 0.03, 0.012), rot, SKIN, gskin, 0.01)
    cap(w(-0.03, -0.07), neck, 0.052, 0.058, SKIN, gskin, 0.03)
    if not old:
        ell(w(-0.022, 0.040), (0.108, 0.102, 0.090), rot, HAIR, ghair, 0.02, 0.006, 60)
        ell(w(-0.075, -0.045), (0.050, 0.085, 0.080), rot, HAIR, ghair, 0.03, 0.006, 60)
        ell(w(0.070, 0.070), (0.040, 0.030, 0.070), rot, HAIR, ghair, 0.03, 0.006, 60)   # forelock
    else:
        ell(w(-0.050, -0.015), (0.070, 0.070, 0.086), rot, WHITE, ghair, 0.02, 0.004, 70)
        ell(w(0.058, -0.105), (0.050, 0.062, 0.056), rot, WHITE, ghair, 0.02, 0.005, 70)  # beard
        ell(w(0.086, 0.030), (0.020, 0.010, 0.050), rot, WHITE, ghair, 0.01)            # brows


def build():
    # ---------------- penitent: kneeling, sunk back on his heels, bowed ----------------
    for s in (1, -1):
        z = s * 0.11
        cap((-0.46, 0.40, z), (-0.13, 0.085, z * 1.1), 0.095, 0.072, TROUS, 1, 0.05)       # thigh
        cap((-0.13, 0.075, z * 1.1), (-0.66, 0.075, z), 0.066, 0.045, TROUS, 1, 0.04)     # shin
        cap((-0.66, 0.07, z), (-0.86, 0.035, z), 0.040, 0.030, SKIN, 2, 0.03)             # foot, sole up
        ell((-0.88, 0.04, z), (0.035, 0.025, 0.045), 0, SKIN, 2, 0.03)
    ell((-0.47, 0.42, 0), (0.17, 0.15, 0.185), 0, TROUS, 1, 0.06)
    cap((-0.46, 0.46, 0), (-0.35, 0.72, 0), 0.165, 0.175, SHIRT, 0, 0.06)
    cap((-0.35, 0.72, 0), (-0.235, 0.895, 0), 0.175, 0.125, SHIRT, 0, 0.06)
    ell((-0.33, 0.78, 0), (0.15, 0.13, 0.215), -0.5, SHIRT, 0, 0.06)                      # shoulder girdle
    ell((-0.47, 0.40, 0), (0.20, 0.10, 0.21), 0, SHIRT, 0, 0.05)                          # shirt tail
    for s in (1, -1):
        sh = (-0.25, 0.86, s * 0.20)
        el = (-0.10, 0.62, s * 0.19)
        hd = (0.085, 0.80, s * 0.03)
        cap(sh, el, 0.066, 0.055, SHIRT, 0, 0.04)
        cap(el, hd, 0.055, 0.042, SHIRT, 0, 0.04)
    ell((0.105, 0.815, 0.0), (0.050, 0.058, 0.060), 0.3, SKIN, 2, 0.02)                  # clasped hands
    cap((0.09, 0.85, 0.035), (0.13, 0.80, 0.035), 0.014, 0.014, SKIN, 2, 0.01)
    head((-0.065, 0.995, 0.0), -42, 1, False, 2, 3, (-0.215, 0.90, 0.0))
    # the scarlet cloak, slipped from the shoulders, pooling behind into the tracks
    slab((-0.22, 1.00), (-0.37, 0.93), 0.0, 0.030, 0.25, CLOAK, 4, 0.05, 0.010, 26)
    slab((-0.37, 0.93), (-0.55, 0.74), 0.0, 0.032, 0.28, CLOAK, 4, 0.05, 0.012, 26)
    slab((-0.55, 0.74), (-0.665, 0.45), 0.0, 0.034, 0.31, CLOAK, 4, 0.05, 0.014, 26)
    slab((-0.665, 0.45), (-0.74, 0.14), 0.0, 0.036, 0.36, CLOAK, 4, 0.05, 0.016, 24)
    slab((-0.74, 0.14), (-1.00, 0.055), 0.03, 0.040, 0.42, CLOAK, 4, 0.06, 0.018, 22)
    slab((-1.00, 0.055), (-1.70, 0.035), 0.08, 0.032, 0.40, CLOAK, 4, 0.06, 0.016, 20)
    ell((-0.50, 0.62, 0.20), (0.11, 0.36, 0.075), 0.32, CLOAK, 4, 0.06, 0.012, 30)       # fall over the near shoulder
    ell((-0.34, 0.93, 0.17), (0.12, 0.085, 0.10), 0.5, CLOAK, 4, 0.05)
    ell((-0.80, 0.07, 0.30), (0.34, 0.06, 0.26), 0, CLOAK, 4, 0.06, 0.014, 22)

    # ---------------- priest: seated on a log, bent toward him ----------------
    cap((0.50, 0.23, -0.16), (1.42, 0.23, 0.02), 0.225, 0.225, BARK, 9, 0.0)
    ell((1.18, 0.455, -0.03), (0.30, 0.055, 0.17), 0.0, SNOW, 13, 0.03)
    for s in (1, -1):
        z = s * 0.12
        cap((0.60, 0.53, z), (0.24, 0.53, z * 1.15), 0.10, 0.085, CASS, 5, 0.06)
        cap((0.24, 0.52, z * 1.15), (0.21, 0.10, z), 0.085, 0.07, CASS, 5, 0.06)
        cap((0.20, 0.05, z), (0.07, 0.04, z), 0.045, 0.038, CASS, 5, 0.02)               # shoe
    ell((0.36, 0.30, 0.0), (0.25, 0.33, 0.27), -0.12, CASS, 5, 0.07, 0.016, 15)          # skirt of the cassock
    ell((0.34, 0.07, 0.0), (0.30, 0.08, 0.30), 0, CASS, 5, 0.06, 0.012, 15)
    cap((0.60, 0.56, 0), (0.50, 0.88, 0), 0.185, 0.185, CASS, 5, 0.06)
    cap((0.50, 0.88, 0), (0.405, 1.075, 0), 0.185, 0.12, CASS, 5, 0.06)
    ell((0.50, 0.93, 0), (0.185, 0.17, 0.255), 0.45, CASS, 5, 0.07, 0.008, 18)           # shoulder cape
    ell((0.63, 0.66, 0), (0.17, 0.36, 0.25), 0.25, CASS, 5, 0.07, 0.012, 16)             # cape down the back
    # near (left) arm, reaching to cover the penitent's hands
    cap((0.43, 1.03, 0.22), (0.33, 0.80, 0.25), 0.075, 0.066, CASS, 5, 0.04)
    cap((0.33, 0.80, 0.25), (0.175, 0.815, 0.075), 0.068, 0.056, CASS, 5, 0.04)
    ell((0.135, 0.822, 0.055), (0.060, 0.046, 0.055), -0.2, SKIN, 6, 0.02)
    cap((0.175, 0.815, 0.075), (0.16, 0.815, 0.07), 0.058, 0.058, WHITE, 7, 0.0)         # cuff
    # far (right) arm raised in absolution
    cap((0.41, 1.04, -0.21), (0.20, 1.13, -0.23), 0.072, 0.062, CASS, 5, 0.04)
    cap((0.20, 1.13, -0.23), (0.045, 1.33, -0.18), 0.062, 0.052, CASS, 5, 0.04)
    cap((0.045, 1.33, -0.18), (0.035, 1.345, -0.18), 0.054, 0.054, WHITE, 7, 0.0)
    ell((0.005, 1.39, -0.18), (0.030, 0.050, 0.042), 0.5, SKIN, 6, 0.015)                 # palm
    cap((-0.01, 1.42, -0.165), (-0.05, 1.505, -0.165), 0.0125, 0.010, SKIN, 6, 0.008)     # index
    cap((-0.005, 1.425, -0.19), (-0.04, 1.515, -0.19), 0.0125, 0.010, SKIN, 6, 0.008)     # middle
    cap((0.01, 1.42, -0.21), (0.012, 1.40, -0.215), 0.013, 0.012, SKIN, 6, 0.008)         # folded
    cap((-0.01, 1.375, -0.15), (-0.05, 1.41, -0.14), 0.013, 0.011, SKIN, 6, 0.008)        # thumb
    head((0.275, 1.215, 0.0), -30, -1, True, 6, 7, (0.40, 1.08, 0.0))
    cap((0.365, 1.115, 0.0), (0.375, 1.105, 0.0), 0.064, 0.064, WHITE, 7, 0.0)           # roman collar
    # violet stole
    for s, zz in ((1, 0.075), (-1, -0.075)):
        slab((0.40, 1.11), (0.335, 0.86), zz * 1.3, 0.014, 0.052, STOLE, 8, 0.012)
        slab((0.335, 0.86), (0.305, 0.66), zz * 1.4, 0.014, 0.054, STOLE, 8, 0.012)
        slab((0.305, 0.66), (0.20, 0.625), zz * 1.5, 0.012, 0.047, STOLE, 8, 0.012)
        slab((0.20, 0.625), (0.115, 0.50), zz * 1.7, 0.012, 0.048, STOLE, 8, 0.012)
        slab((0.115, 0.50), (0.095, 0.20 + 0.04 * s), zz * 1.7, 0.012, 0.050, STOLE, 8, 0.012)
        slab((0.095, 0.20 + 0.04 * s), (0.094, 0.165 + 0.04 * s), zz * 1.7, 0.013, 0.050, GOLD, 12, 0.0)

    # ---------------- wayside crucifix ----------------
    cz, cx = -3.0, 0.95
    n0 = len(P)
    box((cx, 1.32, cz), (0.075, 1.32, 0.075), 0, 0.01, WOOD, 10)
    box((cx, 2.05, cz), (0.78, 0.065, 0.065), 0, 0.01, WOOD, 10)
    for s in (1, -1):
        a = (cx, 2.78); b = (cx + s * 0.92, 2.22)
        slab(a, b, cz, 0.03, 0.22, WOOD, 10, 0.0)
        slab((a[0], a[1] + 0.055), (b[0], b[1] + 0.055), cz, 0.03, 0.235, SNOW, 13, 0.03)
    box((cx, 2.36, cz + 0.08), (0.10, 0.045, 0.012), 0, 0.004, LINEN, 13)                # titulus
    ell((cx - 0.60, 2.125, cz), (0.14, 0.03, 0.08), 0, SNOW, 13, 0.02)
    ell((cx + 0.62, 2.125, cz), (0.12, 0.03, 0.08), 0, SNOW, 13, 0.02)
    z = cz + 0.13
    for s in (1, -1):
        cap((cx + s * 0.66, 2.06, z - 0.03), (cx + s * 0.36, 1.985, z), 0.028, 0.036, CORPUS, 11, 0.03)
        cap((cx + s * 0.36, 1.985, z), (cx + s * 0.155, 1.905, z), 0.038, 0.050, CORPUS, 11, 0.03)
        ell((cx + s * 0.69, 2.065, z - 0.03), (0.035, 0.022, 0.02), 0, CORPUS, 11, 0.02)
    cap((cx - 0.01, 1.84, z), (cx + 0.015, 1.60, z + 0.01), 0.125, 0.095, CORPUS, 11, 0.04)   # chest
    cap((cx + 0.015, 1.60, z + 0.01), (cx + 0.03, 1.47, z + 0.02), 0.095, 0.105, CORPUS, 11, 0.04)
    ell((cx + 0.03, 1.45, z + 0.02), (0.125, 0.085, 0.10), 0, LINEN, 13, 0.02, 0.008, 40)     # loincloth
    cap((cx + 0.15, 1.44, z + 0.06), (cx + 0.19, 1.30, z + 0.05), 0.03, 0.015, LINEN, 13, 0.02)
    for s in (1, -1):
        cap((cx + 0.03 + s * 0.055, 1.42, z + 0.02), (cx - 0.05 + s * 0.04, 1.22, z + 0.12), 0.062, 0.048, CORPUS, 11, 0.03)
        cap((cx - 0.05 + s * 0.04, 1.22, z + 0.12), (cx + s * 0.012, 1.02, z + 0.03), 0.046, 0.034, CORPUS, 11, 0.03)
        cap((cx + s * 0.012, 1.02, z + 0.03), (cx + s * 0.02, 0.94, z + 0.07), 0.032, 0.026, CORPUS, 11, 0.02)
    cap((cx - 0.01, 1.88, z), (cx - 0.035, 1.95, z + 0.03), 0.045, 0.045, CORPUS, 11, 0.03)
    ell((cx - 0.055, 2.005, z + 0.05), (0.075, 0.092, 0.078), 0.35, CORPUS, 11, 0.03)        # head sunk toward the penitent
    ell((cx - 0.05, 2.02, z + 0.03), (0.092, 0.098, 0.085), 0.35, HAIR, 3, 0.02, 0.006, 60)
    ell((cx - 0.12, 1.94, z + 0.03), (0.04, 0.09, 0.06), 0.2, HAIR, 3, 0.03)
    ell((cx - 0.07, 1.935, z + 0.085), (0.045, 0.04, 0.04), 0.3, HAIR, 3, 0.02)              # beard
    box((cx, 0.90, cz + 0.11), (0.07, 0.02, 0.04), 0, 0.005, WOOD, 10)
    for q in P[n0:]:          # stand the whole crucifix on a taller post
        q[2] += 0.62
        if q[0] in (0, 2):
            q[5] += 0.62
    box((cx, 0.5, cz), (0.075, 0.6, 0.075), 0, 0.01, WOOD, 10)
    ell((cx, 0.02, cz + 0.1), (0.5, 0.16, 0.3), 0, SNOW, 13, 0.05)
    return np.array(P, np.float64)


@njit(cache=True)
def smin(a, b, k):
    if k <= 0:
        return min(a, b)
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


@njit(cache=True)
def sdf(px, py, pz, prims, gd):
    for i in range(gd.shape[0]):
        gd[i] = 1e9
    best = 1e9
    bm = -1
    for i in range(prims.shape[0]):
        q = prims[i]
        t = int(q[0])
        if t == 0:
            ax, ay, az = px - q[1], py - q[2], pz - q[3]
            bx, by, bz = q[4] - q[1], q[5] - q[2], q[6] - q[3]
            bb = bx * bx + by * by + bz * bz
            h = (ax * bx + ay * by + az * bz) / bb if bb > 1e-12 else 0.0
            h = min(max(h, 0.0), 1.0)
            dx, dy, dz = ax - bx * h, ay - by * h, az - bz * h
            d = math.sqrt(dx * dx + dy * dy + dz * dz) - (q[7] + (q[8] - q[7]) * h)
        elif t == 1:
            c, s = math.cos(q[7]), math.sin(q[7])
            x, y, z = px - q[1], py - q[2], pz - q[3]
            lx, ly = c * x + s * y, -s * x + c * y
            k0 = math.sqrt((lx / q[4]) ** 2 + (ly / q[5]) ** 2 + (z / q[6]) ** 2)
            k1 = math.sqrt((lx / q[4] ** 2) ** 2 + (ly / q[5] ** 2) ** 2 + (z / q[6] ** 2) ** 2)
            d = k0 * (k0 - 1.0) / k1 if k1 > 1e-9 else -min(q[4], q[5], q[6])
            if q[9] > 0:
                d += q[9] * math.sin(q[10] * (lx * 0.6 + z)) * math.sin(3.0 + 9.0 * ly)
        elif t == 2:
            ax, ay = px - q[1], py - q[2]
            bx, by = q[4] - q[1], q[5] - q[2]
            bb = bx * bx + by * by
            h = min(max((ax * bx + ay * by) / bb, 0.0), 1.0)
            d2 = math.sqrt((ax - bx * h) ** 2 + (ay - by * h) ** 2) - q[7]
            zz = pz - q[3]
            if q[9] > 0:
                d2 += q[9] * math.sin(q[10] * zz + 5.0 * h) * (0.6 + 0.4 * math.sin(7.0 * h + zz * 9.0))
            dz = abs(zz) - q[8]
            d = math.sqrt(max(d2, 0.0) ** 2 + max(dz, 0.0) ** 2) + min(max(d2, dz), 0.0) - 0.012
        else:
            c, s = math.cos(q[7]), math.sin(q[7])
            x, y, z = px - q[1], py - q[2], pz - q[3]
            lx, ly = c * x + s * y, -s * x + c * y
            qx, qy, qz = abs(lx) - q[4], abs(ly) - q[5], abs(z) - q[6]
            d = math.sqrt(max(qx, 0.0) ** 2 + max(qy, 0.0) ** 2 + max(qz, 0.0) ** 2) + min(max(qx, max(qy, qz)), 0.0) - q[8]
        g = int(q[12])
        gd[g] = smin(gd[g], d, q[13])
        if d < best:
            best = d
            bm = int(q[11])
    dm = 1e9
    for i in range(gd.shape[0]):
        if gd[i] < dm:
            dm = gd[i]
    # clay roughness / small creases
    dm += 0.0035 * math.sin(41.0 * px + 3.0 * py) * math.sin(37.0 * py) * math.sin(43.0 * pz + 2.0 * px)
    return dm, bm


@njit(cache=True)
def shadow(ox, oy, oz, lx, ly, lz, prims, gd, tmax):
    res = 1.0
    t = 0.03
    for _ in range(48):
        d, m = sdf(ox + lx * t, oy + ly * t, oz + lz * t, prims, gd)
        if d < 0.002:
            return 0.0
        res = min(res, 14.0 * d / t)
        t += max(d, 0.02)
        if t > tmax:
            break
    return res


@njit(parallel=True, cache=True)
def render(prims, x0, y0, w, h, step, eye, sun, sung, albedo, f, cx, cy):
    rgb = np.zeros((h, w, 3)); mask = np.zeros((h, w)); mat = -np.ones((h, w), np.int32)
    nrm = np.zeros((h, w, 3)); gsh = np.ones((h, w))
    for j in prange(h):
        gd = np.zeros(16)
        for i in range(w):
            sx = x0 + i * step; sy = y0 + j * step
            dx, dy, dz = (sx - cx) / f, -(sy - cy) / f, -1.0
            dl = math.sqrt(dx * dx + dy * dy + dz * dz)
            dx /= dl; dy /= dl; dz /= dl
            t = 4.5
            hit = False
            m = -1
            for _ in range(160):
                d, m = sdf(eye[0] + dx * t, eye[1] + dy * t, eye[2] + dz * t, prims, gd)
                if d < 0.0015:
                    hit = True
                    break
                t += d * 0.8
                if t > 13.5:
                    break
            if not hit:
                if dy < -1e-6:      # snow plane: only the shadow thrown on it matters
                    tg = -eye[1] / dy
                    gx, gz = eye[0] + dx * tg, eye[2] + dz * tg
                    if tg < 40:
                        gsh[j, i] = shadow(gx, 0.01, gz, sung[0], sung[1], sung[2], prims, gd, 9.0)
                continue
            px, py, pz = eye[0] + dx * t, eye[1] + dy * t, eye[2] + dz * t
            e = 0.002
            d0, _m = sdf(px, py, pz, prims, gd)
            d1, _m = sdf(px + e, py, pz, prims, gd)
            d2, _m = sdf(px, py + e, pz, prims, gd)
            d3, _m = sdf(px, py, pz + e, prims, gd)
            nx, ny, nz = d1 - d0, d2 - d0, d3 - d0
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
            nx /= nl; ny /= nl; nz /= nl
            ao = 0.0
            for q in range(1, 6):
                hh = 0.035 * q
                dd, _m = sdf(px + nx * hh, py + ny * hh, pz + nz * hh, prims, gd)
                ao += (hh - dd) / (1.6 ** q)
            ao = min(max(1.0 - 2.2 * ao, 0.0), 1.0)
            ndl = nx * sun[0] + ny * sun[1] + nz * sun[2]
            sh = shadow(px + nx * 0.02, py + ny * 0.02, pz + nz * 0.02, sun[0], sun[1], sun[2], prims, gd, 3.0)
            wrap = min(max((ndl + 0.62) / 1.62, 0.0), 1.0) ** 2.6 * (0.35 + 0.65 * sh)
            direct = max(ndl, 0.0) * sh
            sky = (0.55 + 0.45 * ny) * ao
            fill = max(nz, 0.0) * (0.5 + 0.5 * ao)
            bounce = (0.5 - 0.5 * ny) ** 1.5 * ao
            # ground contact darkening
            a = albedo[m]
            lr = 2.6 * direct + 1.55 * wrap + 0.34 * sky + 0.20 * fill + 0.52 * bounce
            lg = 2.1 * direct + 1.20 * wrap + 0.39 * sky + 0.22 * fill + 0.44 * bounce
            lb = 1.4 * direct + 0.72 * wrap + 0.56 * sky + 0.33 * fill + 0.42 * bounce
            rgb[j, i, 0] = a[0] * lr; rgb[j, i, 1] = a[1] * lg; rgb[j, i, 2] = a[2] * lb
            mask[j, i] = 1.0; mat[j, i] = m
            nrm[j, i, 0] = nx; nrm[j, i, 1] = ny; nrm[j, i, 2] = nz
    return rgb, mask, mat, nrm, gsh


if __name__ == '__main__':
    out = sys.argv[1]
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    prims = build()
    w, h = int(W0 / step), int(H0 / step)
    rgb, mask, mat, nrm, gsh = render(prims, 0.0, 0.0, w, h, step, EYE, SUN, SUNG, ALBEDO, F, CX, CY)
    np.savez_compressed(out + '/maquette.npz', rgb=rgb.astype(np.float32), mask=mask.astype(np.float32), mat=mat,
                        nrm=nrm.astype(np.float32), gsh=gsh.astype(np.float32))
    import cv2
    bg = np.ones_like(rgb) * np.array([0.93, 0.80, 0.66]) * gsh[..., None] ** 0.5
    im = np.where(mask[..., None] > 0, np.clip(rgb, 0, 1), bg)
    cv2.imwrite(out + '/maquette.png', (im[:, :, ::-1] * 255).astype(np.uint8))
