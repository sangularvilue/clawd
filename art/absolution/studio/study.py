"""Colour study and working guides.

The landscape colour study (sky, far hills, lie of the light on the snow) is
combined with the lit maquette of the figure group.  From it come the things a
painter prepares before touching the canvas: a value study, the contour
drawing to transfer, and per-brush-size notes of colour and direction.
"""
import sys, os
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import scene as sc
import paint as pt
import maquette as mq
import land

sc.SX, sc.SY = mq.SUNPX
sc.YH = mq.CY
W, H = 3840, 2160


class Land(sc.Scene):
    def crest(self):
        pts = np.array([(0, 1810), (700, 1780), (1200, 1730), (1600, 1682), (2000, 1668), (2600, 1668),
                        (3000, 1700), (3400, 1770), (3840, 1830)], float)
        x = np.arange(self.W) / self.k
        y = np.interp(x, pts[:, 0], pts[:, 1])
        ksz = int(240 * self.k) | 1
        return np.convolve(np.pad(y, ksz // 2, mode='edge'), np.ones(ksz) / ksz, 'valid')


def build(S):
    L = Land(1.0)
    img, L.ridges, L.extra = land.build2(L.rng)
    M = np.load(S + '/maquette.npz')
    up = lambda a, i=cv2.INTER_CUBIC: cv2.resize(a, (W, H), interpolation=i)
    mask = np.clip(up(M['mask']), 0, 1)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.2)
    rgb = np.clip(up(M['rgb']), 0, 1.4)
    mat = cv2.resize(M['mat'].astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    nrm = up(M['nrm'])
    gsh = np.clip(up(M['gsh'], cv2.INTER_LINEAR), 0, 1)
    # long blue shadows on the snow
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    p = np.clip((yy - sc.YH) / (H - sc.YH), 0, 1)
    sh = 1 - gsh
    sh = cv2.GaussianBlur(sh, (0, 0), 6) * (1 - p) + cv2.GaussianBlur(sh, (0, 0), 28) * p
    sh *= 0.80 * (0.82 + 0.36 * sc.fbm(H, W, 9, 14, 4, L.rng))
    sh = np.clip(sh, 0, 1)[..., None]
    shc = sc.ramp(p, [(0, (0.50, 0.52, 0.72)), (0.5, (0.36, 0.40, 0.63)), (1, (0.24, 0.28, 0.50))])
    img = img * (1 - sh) + shc * sh
    # the maquette takes its place in the landscape
    img = img * (1 - mask[..., None]) + rgb * mask[..., None]
    # light floods round what stands against it
    d = np.sqrt((xx - sc.SX) ** 2 + (yy - sc.SY) ** 2)
    bloom = (np.exp(-d / 60.0) * 0.50 + np.exp(-d / 240.0) * 0.20)[..., None]
    img = img + bloom * np.array([1.0, 0.86, 0.58], np.float32)
    hi = np.clip(img - 0.92, 0, 1)
    img += cv2.GaussianBlur(hi, (0, 0), 14) * 0.8
    v = ((xx - 2050) / 2700.0) ** 2 + ((yy - 1150) / 1500.0) ** 2
    img *= (1 - 0.46 * sc.smoothstep(0.30, 1.25, v))[..., None]
    lum = img.mean(-1, keepdims=True)
    img = np.clip(lum + (img - lum) * 0.92, 0, 1).astype(np.float32)
    return img, mask, mat, nrm, L


if __name__ == '__main__':
    S = sys.argv[1]
    img, mask, mat, nrm, L = build(S)
    cv2.imwrite(S + '/study.png', (img[:, :, ::-1] * 255).astype(np.uint8))
    rng = np.random.default_rng(5)
    base_noise = sc.fbm(H, W, 5, 8, 3, rng)
    out = {'study': (img * 255).astype(np.uint8), 'mask': (mask * 255).astype(np.uint8), 'mat': mat.astype(np.int8)}
    # notes for each brush size: the study seen 'squinting' at that scale, and the way the form runs
    for r in (60, 30, 15, 8, 4, 2):
        rb = cv2.GaussianBlur(img, (0, 0), max(r * 0.35, 0.6))
        ang = pt.orientation(img, 1.0, max(r * 0.12, 1.5), max(r * 0.45, 5), rng, base_noise)
        out['ref%d' % r] = (rb * 255).astype(np.uint8)
        out['ang%d' % r] = ang.astype(np.float16)
    # value study in umber
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    out['value'] = (cv2.GaussianBlur(g, (0, 0), 18) * 255).astype(np.uint8)
    # the drawing: outer contours and the main inner divisions (by material)
    lines = []
    m8 = (mask > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        if len(c) > 80:
            lines.append(cv2.approxPolyDP(c, 1.5, True)[:, 0, :].astype(np.float32))
    for mid in range(14):
        mm = ((mat == mid) & (mask > 0.5)).astype(np.uint8)
        mm = cv2.morphologyEx(mm, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            if len(c) > 120:
                lines.append(cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(np.float32))
    md = cv2.dilate((mask > 0.3).astype(np.uint8), np.ones((31, 31), np.uint8))
    out['maskd'] = md
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dsun = np.sqrt((xx - sc.SX) ** 2 + (yy - sc.SY) ** 2)
    det = np.maximum(0.16 + 0.34 * np.exp(-dsun / 500.0), cv2.GaussianBlur(md.astype(np.float32), (0, 0), 8))
    out['detail'] = (np.clip(det, 0, 1) * 255).astype(np.uint8)
    out.update(L.extra)
    out['nlines'] = np.array(len(lines))
    for i, l in enumerate(lines):
        out['line%d' % i] = l
    out['ridge1'] = np.nan_to_num(L.ridges['far'], nan=sc.YH).astype(np.float32)
    out['ridge2'] = np.fmin(np.nan_to_num(L.ridges['left'], nan=sc.YH), np.nan_to_num(L.ridges['right'], nan=sc.YH)).astype(np.float32)
    out['ridge3'] = L.ridges['edge'].astype(np.float32)
    np.savez(S + '/guides.npz', **out)
    cv2.imwrite(S + '/study_small.jpg', cv2.resize(img[:, :, ::-1] * 255, (1600, 900), interpolation=cv2.INTER_AREA))
    print('guides saved', len(lines), 'contours')
