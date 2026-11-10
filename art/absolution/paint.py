"""Stroke-by-stroke oil painting simulation.

Takes the colour study from scene.py and paints it again on a toned, woven
ground: big bristle brushes first, smaller ones only where the picture still
disagrees with the study.  Every stroke has individual bristles, runs dry
along its length, drags the wet paint beneath it, and leaves a ridge of
impasto that is finally lit by a raking light.
"""
import math
import sys
import numpy as np
import cv2
from numba import njit

from scene import Scene, fbm, smoothstep


@njit(cache=True)
def _stroke(canvas, hmap, weave, px, py, n, r, col, pick, opacity, thick, dry, smear, tonevar,
            dmin, uu, ss, btone, bgap, bh):
    H, W, _ = canvas.shape
    x0 = W; x1 = 0; y0 = H; y1 = 0
    for i in range(n):
        if px[i] < x0: x0 = int(px[i])
        if px[i] > x1: x1 = int(px[i])
        if py[i] < y0: y0 = int(py[i])
        if py[i] > y1: y1 = int(py[i])
    pad = int(r) + 2
    x0 = max(x0 - pad, 0); y0 = max(y0 - pad, 0)
    x1 = min(x1 + pad + 1, W); y1 = min(y1 + pad + 1, H)
    bw = x1 - x0; bhh = y1 - y0
    if bw <= 0 or bhh <= 0 or bw > dmin.shape[1] or bhh > dmin.shape[0]:
        return
    for y in range(bhh):
        for x in range(bw):
            dmin[y, x] = 1e9
    cum = 0.0
    for i in range(n - 1):
        ax = px[i]; ay = py[i]; bx = px[i + 1]; by = py[i + 1]
        ex = bx - ax; ey = by - ay
        L2 = ex * ex + ey * ey
        L = math.sqrt(L2)
        if L < 1e-6:
            continue
        sx0 = max(int(min(ax, bx) - r) - 1, x0); sx1 = min(int(max(ax, bx) + r) + 2, x1)
        sy0 = max(int(min(ay, by) - r) - 1, y0); sy1 = min(int(max(ay, by) + r) + 2, y1)
        for y in range(sy0, sy1):
            for x in range(sx0, sx1):
                qx = x - ax; qy = y - ay
                t = (qx * ex + qy * ey) / L2
                over = 0.0
                if t < 0.0:
                    over = -t * L; t = 0.0
                if t > 1.0:
                    over = (t - 1.0) * L; t = 1.0
                if over > 0.0 and (i == 0 or i == n - 2):
                    # a flat hog-hair brush: square, slightly ragged ends
                    if over > 0.38 * r:
                        continue
                    d = abs(ex * qy - ey * qx) / L
                else:
                    dx = qx - t * ex; dy = qy - t * ey
                    d = math.sqrt(dx * dx + dy * dy)
                if d < r and d < dmin[y - y0, x - x0]:
                    dmin[y - y0, x - x0] = d
                    side = 1.0 if (ex * qy - ey * qx) >= 0 else -1.0
                    uu[y - y0, x - x0] = side * d / r
                    ss[y - y0, x - x0] = cum + t * L
        cum += L
    if cum < 1e-6:
        return
    nb = len(btone)
    aa = max(1.0, 0.24 * r)
    for y in range(bhh):
        for x in range(bw):
            d = dmin[y, x]
            if d >= r:
                continue
            u = uu[y, x]; f = ss[y, x] / cum
            b = int((u * 0.5 + 0.5) * nb)
            if b < 0: b = 0
            if b >= nb: b = nb - 1
            Y = y + y0; X = x + x0
            e = (r - d) / aa
            if e > 1.0: e = 1.0
            # paint runs out toward the end of the stroke; some bristles give out first
            dep = dry * f ** 1.6
            a = opacity * e
            if bgap[b] < dep * 1.15:
                a *= 0.12
            # a starved brush only catches the crowns of the weave
            a *= 1.0 - dep * 0.85 * (1.0 - weave[Y, X])
            # ragged start
            if f < 0.06 and bgap[b] > 0.75:
                a *= 0.3
            if a < 0.004:
                continue
            tone = 1.0 + tonevar * btone[b]
            sm = smear * (0.35 + 0.65 * f)
            hnew = thick * (0.35 + 0.65 * bh[b]) * (1.0 - 0.55 * dep)
            au = abs(u)
            if au > 0.72:
                hnew += thick * 0.14 * (au - 0.72) / 0.28 * e   # ridge pushed up at the edge
            if f > 0.88:
                hnew += thick * 0.5 * (f - 0.88) / 0.12          # paint piled where the brush lifts
            for c in range(3):
                v = (col[c] * (1.0 - sm) + pick[c] * sm) * tone
                canvas[Y, X, c] = canvas[Y, X, c] * (1.0 - a) + v * a
            hmap[Y, X] = hmap[Y, X] * (1.0 - 0.75 * a) + hnew * a


@njit(cache=True)
def paint_layer(canvas, hmap, ref, ang, thr, weave, r, grid, lmin, lmax, opacity, thick, dry0,
                smear, jit, tonevar, curv, seed, always):
    H, W, _ = canvas.shape
    np.random.seed(seed)
    ny = int(H / grid) + 1
    nx = int(W / grid) + 1
    order = np.random.permutation(ny * nx)
    maxpts = 40
    px = np.zeros(maxpts); py = np.zeros(maxpts)
    bs = int(2 * r + lmax * r * 1.2) + 16
    dmin = np.zeros((bs, bs), np.float32); uu = np.zeros((bs, bs), np.float32); ss = np.zeros((bs, bs), np.float32)
    nb = max(4, int(r * 1.1))
    btone = np.zeros(nb); bgap = np.zeros(nb); bh = np.zeros(nb)
    col = np.zeros(3); pick = np.zeros(3)
    count = 0
    step = max(r * 0.9, 1.5)
    for idx in order:
        cy = idx // nx; cx = idx % nx
        x = (cx + np.random.random()) * grid
        y = (cy + np.random.random()) * grid
        ix = int(x); iy = int(y)
        if ix < 0 or iy < 0 or ix >= W or iy >= H:
            continue
        e = 0.0
        for c in range(3):
            dd = canvas[iy, ix, c] - ref[iy, ix, c]
            e += dd * dd
        e = math.sqrt(e)
        if (not always) and e < thr[iy, ix]:
            continue
        # mix the colour on the palette: never quite the same twice
        lum = 0.0
        g = np.random.normal(0.0, jit)
        for c in range(3):
            col[c] = ref[iy, ix, c] * (1.0 + g) + np.random.normal(0.0, jit * 0.6)
            if col[c] < 0: col[c] = 0.0
            if col[c] > 1: col[c] = 1.0
            pick[c] = canvas[iy, ix, c]
            lum += col[c]
        lum /= 3.0
        # trace along the form
        a0 = ang[iy, ix]
        dx = math.cos(a0); dy = math.sin(a0)
        if np.random.random() < 0.5:
            dx = -dx; dy = -dy
        px[0] = x; py[0] = y
        n = 1
        maxn = int(lmin + np.random.random() * (lmax - lmin))
        if maxn > maxpts: maxn = maxpts
        cxp = x; cyp = y
        for i in range(1, maxn):
            cxp += dx * step; cyp += dy * step
            jx = int(cxp); jy = int(cyp)
            if jx < 0 or jy < 0 or jx >= W or jy >= H:
                break
            if i > lmin * 0.5:
                d1 = 0.0; d2 = 0.0
                for c in range(3):
                    t1 = ref[jy, jx, c] - canvas[jy, jx, c]
                    t2 = ref[jy, jx, c] - col[c]
                    d1 += t1 * t1; d2 += t2 * t2
                if d2 > d1 and math.sqrt(d2) > 0.05:
                    break
            px[i] = cxp; py[i] = cyp
            n += 1
            a1 = ang[jy, jx]
            ndx = math.cos(a1); ndy = math.sin(a1)
            if ndx * dx + ndy * dy < 0:
                ndx = -ndx; ndy = -ndy
            dx = curv * ndx + (1 - curv) * dx
            dy = curv * ndy + (1 - curv) * dy
            nn = math.sqrt(dx * dx + dy * dy) + 1e-9
            dx /= nn; dy /= nn
        if n < 2:
            px[1] = x + dx * step; py[1] = y + dy * step
            n = 2
        prev = 0.0
        for b in range(nb):
            v = np.random.normal(0.0, 1.0)
            btone[b] = 0.55 * v + 0.45 * prev
            prev = v
            bgap[b] = np.random.random()
            bh[b] = np.random.random()
        dry = dry0 * (0.25 + 0.75 * np.random.random())
        th = thick * (0.30 + 1.0 * lum * lum) * (0.7 + 0.6 * np.random.random())
        _stroke(canvas, hmap, weave, px, py, n, r * (0.8 + 0.4 * np.random.random()), col, pick,
                opacity, th, dry, smear, tonevar, dmin, uu, ss, btone, bgap, bh)
        count += 1
    return count


def make_weave(H, W, k, rng):
    """plain-woven linen: warp and weft passing over and under, a little irregular"""
    p = max(5.2 * k, 2.6)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wob = fbm(H, W, 24, 40, 3, rng) - 0.5
    wob2 = fbm(H, W, 40, 24, 3, rng) - 0.5
    X = xx + wob * p * 1.6
    Y = yy + wob2 * p * 1.6
    cxr = np.floor(X / p); cyr = np.floor(Y / p)
    fx = X / p - cxr; fy = Y / p - cyr
    over = ((cxr + cyr) % 2) == 0
    bx = np.sin(np.pi * fx); by = np.sin(np.pi * fy)
    h = np.where(over, bx ** 0.7 * (0.55 + 0.45 * by), by ** 0.7 * (0.55 + 0.45 * bx) * 0.9)
    # slubs: threads of uneven thickness
    tr = np.random.default_rng(1)
    col = tr.random(int(W / p) + 3)[np.clip(cxr.astype(int), 0, None)]
    row = tr.random(int(H / p) + 3)[np.clip(cyr.astype(int), 0, None)]
    h = h * np.where(over, 0.8 + 0.4 * col, 0.8 + 0.4 * row)
    h = cv2.GaussianBlur(h.astype(np.float32), (0, 0), 0.55)
    return np.clip(h, 0, 1)


def orientation(ref, k, sig_d, sig_i, rng, base_noise):
    g = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), sig_d * k)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), sig_i * k)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), sig_i * k)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), sig_i * k)
    # tangent double-angle = gradient double angle + pi
    c2 = -(jxx - jyy)
    s2 = -(2 * jxy)
    mag = np.sqrt(c2 * c2 + s2 * s2)
    w = np.clip(mag / (np.percentile(mag, 80) + 1e-9), 0, 1) ** 0.5
    a0 = (base_noise - 0.5) * 1.5 - 0.12          # the hand's habitual slant
    c0, s0 = np.cos(2 * a0), np.sin(2 * a0)
    cn = c2 / (mag + 1e-9) * w + c0 * (1 - w)
    sn = s2 / (mag + 1e-9) * w + s0 * (1 - w)
    return (0.5 * np.arctan2(sn, cn)).astype(np.float32)


def paint(ref, detail, k, seed=1, log=print):
    H, W, _ = ref.shape
    rng = np.random.default_rng(seed)
    weave = make_weave(H, W, k, rng)
    # warm imprimatura, scrubbed thinly over the priming
    tone = fbm(H, W, 6, 9, 5, rng)
    ground = np.array([0.50, 0.36, 0.25], np.float32)[None, None] * (0.80 + 0.35 * tone[..., None])
    ground = ground * (0.86 + 0.20 * weave[..., None])
    canvas = np.ascontiguousarray(ground.astype(np.float32))
    hmap = np.zeros((H, W), np.float32)
    base_noise = fbm(H, W, 5, 8, 3, rng)
    det = cv2.GaussianBlur(detail, (0, 0), 6 * k)
    det = np.maximum(det, detail)

    # radius, grid, lmin, lmax, opacity, thick, dry, smear, jitter, tonevar, curv, thr, det-power, always
    layers = [
        (64, 44, 5, 12, 0.93, 0.55, 0.55, 0.10, 0.030, 0.050, 0.18, 0.00, 0.0, True),
        (34, 24, 5, 12, 0.92, 0.70, 0.60, 0.14, 0.035, 0.055, 0.22, 0.055, 0.3, False),
        (18, 13, 4, 10, 0.92, 0.85, 0.65, 0.16, 0.035, 0.060, 0.35, 0.050, 0.6, False),
        (9.5, 7, 4, 11, 0.93, 1.00, 0.60, 0.15, 0.030, 0.060, 0.40, 0.050, 1.2, False),
        (5.0, 3.8, 3, 10, 0.94, 1.00, 0.50, 0.12, 0.028, 0.055, 0.45, 0.055, 1.7, False),
        (2.7, 2.1, 3, 9, 0.95, 0.90, 0.35, 0.08, 0.022, 0.045, 0.45, 0.070, 2.2, False),
    ]
    for li, (r, grid, lmin, lmax, op, th, dry, smear, jit, tv, curv, thr0, dp, always) in enumerate(layers):
        rk = r * k
        if rk < 1.2:
            continue
        refb = cv2.GaussianBlur(ref, (0, 0), max(rk * 0.33, 0.5))
        ang = orientation(ref, k, max(r * 0.12, 1.5), max(r * 0.45, 5), rng, base_noise)
        thr = (thr0 / (0.30 + 0.70 * det) ** dp).astype(np.float32)
        n = paint_layer(canvas, hmap, np.ascontiguousarray(refb), ang, thr, weave, rk, grid * k, lmin, lmax,
                        op, th, dry, smear, jit, tv, curv, seed * 100 + li, always)
        log(f'layer {li}: brush {rk:.1f}px, {n} strokes')
    return canvas, hmap, weave


@njit(cache=True)
def flakes(canvas, hmap, xs, ys, rs, als, ang):
    H, W, _ = canvas.shape
    for i in range(len(xs)):
        r = rs[i]
        ca = math.cos(ang[i]); sa = math.sin(ang[i])
        x0 = max(int(xs[i] - 2.5 * r) - 1, 0); x1 = min(int(xs[i] + 2.5 * r) + 2, W)
        y0 = max(int(ys[i] - 2.5 * r) - 1, 0); y1 = min(int(ys[i] + 2.5 * r) + 2, H)
        for y in range(y0, y1):
            for x in range(x0, x1):
                dx = x - xs[i]; dy = y - ys[i]
                u = (dx * ca + dy * sa) / (1.7 * r)
                v = (-dx * sa + dy * ca) / r
                d = u * u + v * v
                if d < 1.0:
                    a = als[i] * min(1.0, (1.0 - d) * 2.5)
                    canvas[y, x, 0] = canvas[y, x, 0] * (1 - a) + 0.93 * a
                    canvas[y, x, 1] = canvas[y, x, 1] * (1 - a) + 0.94 * a
                    canvas[y, x, 2] = canvas[y, x, 2] * (1 - a) + 1.00 * a
                    hmap[y, x] = hmap[y, x] * (1 - a) + (0.5 + 0.6 * (1 - d)) * a


def snowfall(canvas, hmap, k, rng):
    """the last of the storm: flakes flicked on with the tip of the brush, thick to the left"""
    H, W, _ = canvas.shape
    n = int(1500)
    x = rng.random(n * 6) * W
    y = rng.random(n * 6) * H
    keep = rng.random(n * 6) < (0.03 + 0.97 * np.exp(-x / (W * 0.22)))
    x, y = x[keep][:n], y[keep][:n]
    depth = rng.random(len(x)) ** 3.0
    rs = (1.6 + 3.4 * depth) * k
    als = 0.22 + 0.5 * rng.random(len(x)) * (0.5 + 0.5 * depth)
    ang = 1.15 + rng.normal(0, 0.25, len(x))
    flakes(canvas, hmap, x.astype(np.float64), y.astype(np.float64), rs, als, ang)


def finish(canvas, hmap, weave, k, rng):
    H, W, _ = canvas.shape
    hp = cv2.GaussianBlur(hmap.astype(np.float32), (0, 0), 0.8)
    # where the paint is thin the cloth shows through it
    thin = np.exp(-hp * 2.2)
    relief = hp * 1.9 * max(k, 0.6) + weave * (0.34 + 0.8 * thin) * max(k, 0.6)
    gx = cv2.Sobel(relief, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(relief, cv2.CV_32F, 0, 1, ksize=3) / 8
    s = 2.3
    nx, ny, nz = -gx * s, -gy * s, np.ones_like(gx)
    nl = np.sqrt(nx * nx + ny * ny + 1)
    nx, ny, nz = nx / nl, ny / nl, nz / nl
    L = np.array([-0.50, -0.62, 0.60]); L /= np.linalg.norm(L)     # gallery light, upper left
    diff = nx * L[0] + ny * L[1] + nz * L[2]
    shade = 1.0 + 0.80 * (diff - L[2])
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 60
    spec0 = Hh[2] ** 60
    out = canvas * shade[..., None] + (spec - spec0)[..., None] * 0.10
    # the faint ambered depth of varnish
    out = out * np.array([1.0, 0.985, 0.95], np.float32) + np.array([0.012, 0.008, 0.0], np.float32)
    out = np.clip(out, 0, 1)
    out = out ** 1.03
    return np.clip(out, 0, 1)


if __name__ == '__main__':
    k = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    out = sys.argv[2] if len(sys.argv) > 2 else '.'
    sc = Scene(k)
    ref, det = sc.build()
    cv2.imwrite(f'{out}/ref.png', (ref[:, :, ::-1] * 255).astype(np.uint8))
    canvas, hmap, weave = paint(np.ascontiguousarray(ref), det, k)
    rng = np.random.default_rng(99)
    snowfall(canvas, hmap, k, rng)
    final = finish(canvas, hmap, weave, k, rng)
    img8 = (final[:, :, ::-1] * 255 + 0.5).astype(np.uint8)
    cv2.imwrite(f'{out}/painting.png', img8)
    cv2.imwrite(f'{out}/painting.jpg', img8, [cv2.IMWRITE_JPEG_QUALITY, 96])
    print('done', img8.shape)
