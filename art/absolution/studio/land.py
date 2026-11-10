"""Landscape colour study in the Hudson River School manner.

The figures kneel on a snow ledge above a vast valley.  The composition is
read left to right as the passage the sacrament makes:

  left    - the storm drawing off round a cloud-wrapped, Sinai-like peak;
            dark forest, a river locked in ice in its shadow
  centre  - the sun rising in a notch between the ranges: the narrow gate,
            with the river running gold out of it
  right   - three summits in alpenglow over the village church by the water
"""
import os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import scene as sc

W, H = 3840, 2160

FAR = [(0, 900), (400, 830), (800, 870), (1200, 790), (1500, 905), (1750, 1040), (1900, 1080), (2200, 1082), (2400, 1035),
       (2700, 905), (3000, 835), (3300, 885), (3600, 805), (3840, 850)]
LEFT = [(0, 540), (300, 440), (600, 300), (700, 285), (800, 335), (950, 480), (1150, 600), (1350, 765), (1550, 935), (1720, 1052),
        (1810, 1094)]
RIGHT = [(2290, 1094), (2420, 1012), (2600, 900), (2800, 745), (2950, 560), (3050, 605), (3180, 470), (3300, 565), (3420, 430),
         (3560, 600), (3700, 560), (3840, 590)]
LSPUR = [(0, 1005), (500, 1062), (900, 1124), (1250, 1196), (1480, 1262), (1600, 1320)]
RSPUR = [(3840, 1215), (3500, 1262), (3150, 1322), (2850, 1384), (2640, 1440)]
EDGE = [(0, 1502), (600, 1482), (1200, 1458), (1800, 1442), (2400, 1438), (3000, 1452), (3500, 1492), (3840, 1532)]
RIVER_R = ([(2420, 1100), (2700, 1114), (3000, 1136), (3330, 1176), (3150, 1232), (2800, 1280), (2480, 1330)], [5, 9, 16, 30, 46, 60, 74])
RIVER_L = ([(1620, 1345), (1250, 1318), (850, 1345), (450, 1402), (-40, 1450)], [70, 92, 112, 138, 160])


def ridge(pts, rng, jag, x):
    P = np.array(pts, float)
    o = np.argsort(P[:, 0]); P = P[o]
    y = np.interp(x, P[:, 0], P[:, 1], left=np.nan, right=np.nan)
    n = np.zeros(len(x)); amp = 1.0; cells = 12
    for _ in range(6):
        g = rng.random(cells + 2)
        n += amp * np.interp(np.linspace(0, cells, len(x)), np.arange(cells + 2), g); amp *= 0.55; cells *= 2
    n = (n / n.std() - (n / n.std()).mean())
    return y + n * jag


def build(rng):
    S = sc.Scene(1.0)
    S.sky()
    img = S.img.astype(np.float32)
    dn = S.dn
    xx, yy = S.xx, S.yy
    x = np.arange(W, dtype=float)
    SX, SY, YH = sc.SX, sc.SY, sc.YH
    # light slanting up out of the notch across the under-side of the storm
    ang = np.arctan2(yy - SY, xx - SX)
    rn = np.interp((ang + np.pi) / (2 * np.pi) * 360, np.arange(361), np.convolve(rng.random(375), np.ones(15) / 15, 'valid') * 1.6 - 0.3)
    rays = sc.smoothstep(0.50, 0.66, rn) * np.exp(-dn / 0.20) * (yy < SY) * 0.085
    img += rays[..., None] * np.array([1.0, 0.82, 0.56], np.float32)
    glow = np.exp(-dn / 0.11)[..., None]
    tex = sc.fbm(H, W, 26, 34, 5, rng)
    big = sc.fbm(H, W, 5, 7, 4, rng)
    fine = sc.fbm(H, W, 90, 120, 3, rng)
    rib = cv2.GaussianBlur(sc.fbm(H, W, 3, 64, 4, rng), (0, 0), 3)      # ribs and couloirs running down the faces
    rib2 = sc.fbm(H, W, 4, 90, 4, rng)
    gxs = (np.roll(big, -60, 1) - np.roll(big, 60, 1)) * 4      # only the big planes; the rest is painted by hand

    def massif(rd, base, shadow, light, rock, haze, sgn, litbias, snowline=0.0):
        nonlocal img
        m = sc.smoothstep(-2, 2, yy - rd[None, :]) * sc.smoothstep(2, -2, yy - base)
        m = np.nan_to_num(m)
        lit = sc.smoothstep(-0.10, 0.22, -sgn * gxs + litbias) * 0.6
        dep = np.clip((yy - np.nan_to_num(rd, nan=0)[None, :]) / 500.0, 0, 1)
        rk = sc.smoothstep(0.52, 0.72, rib2 * 0.6 + fine * 0.25 + tex * 0.15 + dep * 0.22 - snowline) * (1 - 0.6 * lit)
        col = np.array(shadow, np.float32) * (1 - lit[..., None]) + np.array(light, np.float32) * lit[..., None]
        rc = np.array(rock, np.float32) * (0.7 + 0.9 * lit[..., None])
        col = col * (1 - rk[..., None] * 0.15) + rc * rk[..., None] * 0.15
        hz = np.clip(haze + 0.55 * glow[..., 0] + 0.35 * sc.smoothstep(base - 260, base, yy), 0, 0.95)[..., None]
        hc = sc.ramp(np.clip(dn * 0.9, 0, 1), [(0, (1.0, 0.90, 0.66)), (0.12, (0.98, 0.74, 0.58)), (0.3, (0.66, 0.58, 0.72)),
                                                (0.6, (0.42, 0.44, 0.62))])
        col = col * (1 - hz) + hc * hz
        img = img * (1 - m[..., None]) + col * m[..., None]
        return m

    rf = ridge(FAR, rng, 14, x)
    massif(rf, 1100.0, (0.60, 0.57, 0.74), (1.0, 0.84, 0.74), (0.46, 0.44, 0.62), 0.42, np.sign(x - SX)[None, :] * -1, 0.02)
    rl = ridge(LEFT, rng, 24, x)
    ml = massif(rl, 1240.0, (0.30, 0.33, 0.52), (0.99, 0.76, 0.66), (0.115, 0.125, 0.20), 0.10, 1.0, -0.16)
    rr = ridge(RIGHT, rng, 22, x)
    mr = massif(rr, 1240.0, (0.44, 0.42, 0.62), (1.0, 0.80, 0.68), (0.22, 0.20, 0.32), 0.14, -1.0, 0.10, 0.08)
    # the valley floor, seen from above: snow meadows going from gold at the gate to blue under the left-hand range
    ed = np.interp(x, [p[0] for p in EDGE], [p[1] for p in EDGE]) + (sc.fbm(8, W, 1, 14, 5, rng)[4] - 0.5) * 60
    vm = sc.smoothstep(-1.5, 1.5, yy - YH)
    p = np.clip((yy - YH) / 360.0, 0, 1)
    wp = np.exp(-((xx - SX) / (420 + 2.2 * (yy - YH))) ** 2)
    vl = np.clip(0.75 * np.exp(-p / 0.35) + 0.55 * wp + 0.35 * sc.smoothstep(0.45, 0.75, big) * sc.smoothstep(1200, 2000, xx) - 0.25 * sc.smoothstep(2000, 1200, xx) * p, 0, 1)
    vsh = np.array([0.36, 0.40, 0.62], np.float32); vli = np.array([1.0, 0.88, 0.70], np.float32)
    vcol = vsh * (1 - vl[..., None]) + vli * vl[..., None]
    vcol = vcol * (0.92 + 0.16 * tex[..., None])
    img = img * (1 - vm[..., None]) + vcol * vm[..., None]

    def band(cl, ws, col_fn):
        nonlocal img
        pg = np.array(sc.ribbon(cl, ws, 120), np.int32)
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [pg], 255)
        m = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 2.0)
        img = img * (1 - m[..., None]) + col_fn() * m[..., None]
        return m
    # river: open and golden where it comes out of the light ...
    wr = sc.ramp(np.clip((yy - YH) / 260.0, 0, 1), [(0, (1.0, 0.92, 0.70)), (0.4, (1.0, 0.80, 0.56)), (1.0, (0.86, 0.62, 0.56))])
    band(*RIVER_R, lambda: wr)
    # ... still bound in ice under the mountain's shadow
    ice = np.array([0.58, 0.64, 0.82], np.float32)[None, None] * (0.86 + 0.28 * tex[..., None]) \
        - sc.smoothstep(0.62, 0.72, fine)[..., None] * np.array([0.30, 0.30, 0.28], np.float32)
    band(*RIVER_L, lambda: ice)

    def spur(pts, col, base):
        nonlocal img
        rd = ridge(pts, rng, 7, x)
        m = np.nan_to_num(sc.smoothstep(-2, 2, yy - rd[None, :]))
        c_ = np.array(col, np.float32)[None, None] * (0.75 + 0.5 * tex[..., None])
        dep = np.clip((yy - np.nan_to_num(rd)[None, :]) / 260.0, 0, 1)[..., None]
        c_ = c_ * (1 - 0.25 * dep) + np.array([0.30, 0.33, 0.52], np.float32) * 0.25 * dep
        c_ = c_ * (1 - glow * 0.5) + np.array([0.9, 0.62, 0.48], np.float32) * glow * 0.5
        img = img * (1 - m[..., None]) + c_ * m[..., None]
    spur(LSPUR, (0.085, 0.10, 0.155), 1500)
    spur(RSPUR, (0.14, 0.14, 0.23), 1500)
    # mist lying in the valley and at the mountain feet
    for (cy, amp, x0, x1) in [(1118, 0.50, 0, 1900), (1128, 0.36, 2250, 3840), (1250, 0.34, 0, 1700), (1330, 0.22, 2400, 3840)]:
        mn = sc.fbm(H, W, 30, 6, 3, rng)
        mm = np.exp(-((yy - cy - (mn - 0.5) * 60) / 24.0) ** 2) * amp * sc.smoothstep(x0 - 200, x0 + 100, xx) * sc.smoothstep(x1 + 200, x1 - 100, xx)
        mc = sc.ramp(np.clip(dn, 0, 1), [(0, (1.0, 0.90, 0.70)), (0.15, (0.96, 0.76, 0.66)), (0.35, (0.66, 0.62, 0.78)), (0.7, (0.50, 0.52, 0.70))])
        img = img * (1 - mm[..., None]) + mc * mm[..., None]
    # the ledge itself
    L = sc.Scene(1.0)
    L.img = img.copy()
    L.dn = dn
    L.crest = lambda: np.full(W, 3000.0)
    L.ground()
    lm = sc.smoothstep(-2, 2, yy - ed[None, :])[..., None]
    g = L.img.astype(np.float32)
    # the lip of the ledge takes a line of light; just under it the snow is in its own shadow
    lip = np.exp(-((yy - ed[None, :] - 6) / 6.0) ** 2)[..., None] * (0.25 + 0.5 * wp[..., None])
    g = g * (1 - 0.30 * np.exp(-np.clip(yy - ed[None, :], 0, None) / 120.0)[..., None]) + lip * np.array([0.5, 0.4, 0.3], np.float32)
    img = img * (1 - lm) + g * lm
    ridges = {'far': rf, 'left': rl, 'right': rr, 'edge': ed}
    return img.astype(np.float32), ridges


def build2(rng):
    """the landscape study from the 3D valley (terrain.py), sky and snow ledge"""
    import terrain as tr
    import maquette as mq
    S = sc.Scene(1.0)
    S.sky()
    img = S.img.astype(np.float32)
    dn = S.dn
    xx, yy = S.xx, S.yy
    SX, SY, YH = sc.SX, sc.SY, sc.YH
    x = np.arange(W, dtype=float)
    ang = np.arctan2(yy - SY, xx - SX)
    rn = np.interp((ang + np.pi) / (2 * np.pi) * 360, np.arange(361), np.convolve(rng.random(375), np.ones(15) / 15, 'valid') * 1.6 - 0.3)
    rays = sc.smoothstep(0.50, 0.66, rn) * np.exp(-dn / 0.20) * (yy < SY) * 0.085
    img += rays[..., None] * np.array([1.0, 0.82, 0.56], np.float32)
    hh = 800
    skyh = np.ascontiguousarray(np.clip(cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA), 0, 1))
    rgb, hit, depth, forest, wat = tr.render(W // 2, hh, 2.0, mq.F, mq.CX, mq.CY, skyh)
    up = lambda a: cv2.resize(a, (W, hh * 2), interpolation=cv2.INTER_CUBIC)
    m = np.clip(cv2.GaussianBlur(up(hit), (0, 0), 1.0), 0, 1)[..., None]
    img[:hh * 2] = img[:hh * 2] * (1 - m) + np.clip(up(rgb), 0, 1) * m
    ed = np.interp(x, [p[0] for p in EDGE], [p[1] for p in EDGE]) + (sc.fbm(8, W, 1, 14, 5, rng)[4] - 0.5) * 60
    wp = np.exp(-((xx - SX) / (420 + 2.2 * (yy - YH))) ** 2)
    L = sc.Scene(1.0)
    L.img = img.copy(); L.dn = dn
    L.crest = lambda: np.full(W, 3000.0)
    L.ground()
    lm = sc.smoothstep(-2, 2, yy - ed[None, :])[..., None]
    g = L.img.astype(np.float32)
    lip = np.exp(-((yy - ed[None, :] - 6) / 6.0) ** 2)[..., None] * (0.25 + 0.5 * wp[..., None])
    g = g * (1 - 0.30 * np.exp(-np.clip(yy - ed[None, :], 0, None) / 120.0)[..., None]) + lip * np.array([0.5, 0.4, 0.3], np.float32)
    img = img * (1 - lm) + g * lm
    hf = up(hit) > 0.5
    skyline = np.where(hf.any(0), hf.argmax(0), YH).astype(float)
    ridges = {'far': skyline, 'left': skyline, 'right': skyline, 'edge': ed}
    extra = {'forest': (np.clip(forest, 0, 1) * 255).astype(np.uint8), 'depth': depth.astype(np.float16), 'water': (wat * 255).astype(np.uint8)}
    return img.astype(np.float32), ridges, extra
