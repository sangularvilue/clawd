"""Underpainting / reference study for "Though Your Sins Be as Scarlet".

Builds the full composition (sky, land, figures, light) as a smooth colour
study.  paint.py then re-paints it stroke by stroke in simulated oil.
All coordinates are in 3840x2160 space; `k` scales the working resolution.
"""
import math
import numpy as np
import cv2
import cairo

W0, H0 = 3840, 2160
SX, SY = 2110.0, 1052.0          # the rising sun
YH = 1092.0                      # horizon
GX0, GY0, GS = 2077.0, 1598.0, 1.2   # figure-group origin / scale


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fbm(h, w, cy, cx, octv, rng, gain=0.5):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for _ in range(octv):
        g = rng.random((int(cy) + 2, int(cx) + 2)).astype(np.float32)
        out += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= gain
        cy *= 2
        cx *= 2
    out /= tot
    lo, hi = np.percentile(out[::8, ::8], [1, 99])
    return np.clip((out - lo) / (hi - lo), 0, 1)


def ramp(t, stops):
    pos = np.array([s[0] for s in stops], np.float32)
    cols = np.array([s[1] for s in stops], np.float32)
    return np.stack([np.interp(t, pos, cols[:, i]) for i in range(3)], -1).astype(np.float32)


def smooth(ctx, pts, closed=True):
    P = np.array(pts, float)
    n = len(P)
    ctx.move_to(*P[0])
    rng_ = range(n) if closed else range(n - 1)
    for i in rng_:
        if closed:
            p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        else:
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        ctx.close_path()


def poly(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def ribbon(pts, widths, n=60):
    """polygon around a smooth centre line with varying width"""
    P = np.array(pts, float)
    t = np.linspace(0, len(P) - 1, n)
    xs = np.interp(t, np.arange(len(P)), P[:, 0])
    ys = np.interp(t, np.arange(len(P)), P[:, 1])
    ker = np.ones(5) / 5
    xs2 = np.convolve(np.pad(xs, 2, mode='edge'), ker, 'valid')
    ys2 = np.convolve(np.pad(ys, 2, mode='edge'), ker, 'valid')
    ws = np.interp(t, np.arange(len(P)), np.array(widths, float))
    dx = np.gradient(xs2)
    dy = np.gradient(ys2)
    L = np.hypot(dx, dy) + 1e-6
    nx, ny = -dy / L, dx / L
    left = list(zip(xs2 + nx * ws / 2, ys2 + ny * ws / 2))
    right = list(zip(xs2 - nx * ws / 2, ys2 - ny * ws / 2))
    return left + right[::-1]


class Scene:
    def __init__(self, k=1.0, seed=7):
        self.k = k
        self.W, self.H = int(W0 * k), int(H0 * k)
        self.img = np.zeros((self.H, self.W, 3), np.float32)
        self.detail = np.zeros((self.H, self.W), np.float32)
        self.rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.xx, self.yy = xx / k, yy / k

    # ---------- cairo helpers ----------
    def _ctx(self, fmt, group):
        surf = cairo.ImageSurface(fmt, self.W, self.H)
        ctx = cairo.Context(surf)
        ctx.scale(self.k, self.k)
        if group:
            ctx.translate(GX0, GY0)
            ctx.scale(GS, GS)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        return surf, ctx

    def mask(self, fn, group=False):
        surf, ctx = self._ctx(cairo.FORMAT_A8, group)
        ctx.set_source_rgba(1, 1, 1, 1)
        fn(ctx)
        surf.flush()
        a = np.frombuffer(surf.get_data(), np.uint8).reshape(self.H, surf.get_stride())[:, :self.W]
        return a.astype(np.float32) / 255.0

    def overlay(self, fn, group=False, blur=0.0, alpha=1.0, detail=None, clip=None):
        surf, ctx = self._ctx(cairo.FORMAT_ARGB32, group)
        fn(ctx)
        surf.flush()
        a = np.frombuffer(surf.get_data(), np.uint8).reshape(self.H, self.W, 4).astype(np.float32) / 255.0
        rgb = a[:, :, 2::-1]
        al = a[:, :, 3:4]
        if blur > 0:
            s = blur * self.k
            rgb = cv2.GaussianBlur(rgb, (0, 0), s)
            al = cv2.GaussianBlur(al, (0, 0), s)[..., None]
        al = al * alpha
        if clip is not None:
            al = al * clip[..., None]
            rgb = rgb * clip[..., None]
        self.img = self.img * (1 - al) + rgb * alpha
        if detail is not None:
            self.detail = np.maximum(self.detail, al[..., 0] * detail)
        return al[..., 0]

    def relief(self, fn, base, group=True, sig=(4, 14), rim=1.0, amb=0.55, depth=2.4,
               suncol=(1.0, 0.86, 0.60), detail=1.0, lz=-0.22, alpha=1.0, m=None, tint=None, form=0.5):
        """Fill a shape with pseudo-3D backlit shading: warm rim toward the sun,
        cool sky light from above, soft snow-bounce from below."""
        k = self.k
        if m is None:
            m = self.mask(fn, group)
        ys, xs = np.where(m > 0.004)
        if len(ys) == 0:
            return m
        pad = int(3 * max(max(sig), 30) * k) + 3
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, self.H)
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, self.W)
        mc = m[y0:y1, x0:x1]
        gx = np.zeros_like(mc)
        gy = np.zeros_like(mc)
        for s in sig:
            b = cv2.GaussianBlur(mc, (0, 0), max(s * k, 0.6))
            gx += cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3) / 8 * (s * k) * depth / len(sig)
            gy += cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3) / 8 * (s * k) * depth / len(sig)
        nx, ny, nz = -gx, -gy, np.ones_like(gx)
        nl = np.sqrt(nx * nx + ny * ny + 1)
        nx, ny, nz = nx / nl, ny / nl, nz / nl
        lx = SX - self.xx[y0:y1, x0:x1]
        ly = SY - self.yy[y0:y1, x0:x1]
        ll = np.sqrt(lx * lx + ly * ly) + 1e-3
        lx, ly = lx / ll, ly / ll
        ln = math.sqrt(1 + lz * lz)
        rimv = np.clip((nx * lx + ny * ly + nz * lz) / ln, 0, 1) ** 1.3 * rim
        # nearer the sun = stronger
        rimv *= (0.55 + 0.75 * np.exp(-ll / 900.0))
        sky = np.clip(-ny * 0.75 + nz * 0.45, 0, 1)
        bounce = np.clip(ny * 0.8 + nz * 0.25, 0, 1)
        base = np.array(base, np.float32)
        if tint is not None:
            base = base[None, None, :] * tint[y0:y1, x0:x1, None]
        else:
            base = np.broadcast_to(base, mc.shape + (3,))
        col = base * (amb * (0.42 * np.array([0.80, 0.86, 1.08], np.float32)
                             + sky[..., None] * np.array([0.42, 0.48, 0.66], np.float32)
                             + bounce[..., None] * np.array([0.60, 0.50, 0.46], np.float32)))
        sc = np.array(suncol, np.float32)
        col = col + rimv[..., None] * sc * (base * 0.75 + 0.30)
        if form > 0:
            b3 = cv2.GaussianBlur(mc, (0, 0), 30 * k)
            fx = -cv2.Sobel(b3, cv2.CV_32F, 1, 0, ksize=3) / 8 * (30 * k) * 3.0
            fy = -cv2.Sobel(b3, cv2.CV_32F, 0, 1, ksize=3) / 8 * (30 * k) * 3.0
            fd = (fx * lx + fy * ly) / np.sqrt(fx * fx + fy * fy + 1)
            col = col * (1 - 0.45 * form * np.clip(-fd, 0, 1))[..., None] \
                + (form * np.clip(fd, 0, 1) ** 1.2)[..., None] * sc * base * 0.85
        a = (mc * alpha)[..., None]
        self.img[y0:y1, x0:x1] = self.img[y0:y1, x0:x1] * (1 - a) + col * a
        self.detail = np.maximum(self.detail, m * detail)
        return m

    # =====================================================================
    def sky(self):
        k, W, H, rng = self.k, self.W, self.H, self.rng
        xx, yy = self.xx, self.yy
        dx, dy = xx - SX, yy - SY
        dn = np.sqrt((dx / 1.75) ** 2 + (dy * 1.05) ** 2) / 3840.0
        self.dn = dn
        stops = [(0.00, (1.00, 0.98, 0.88)), (0.025, (1.00, 0.94, 0.72)), (0.07, (0.99, 0.81, 0.52)),
                 (0.13, (0.95, 0.66, 0.48)), (0.20, (0.78, 0.55, 0.55)), (0.28, (0.53, 0.47, 0.60)),
                 (0.38, (0.36, 0.39, 0.56)), (0.55, (0.23, 0.27, 0.43)), (0.80, (0.13, 0.16, 0.28))]
        sky = ramp(dn, stops)
        # cloud deck: heavy to the upper left (the departing storm), open toward the dawn
        n = fbm(H, W, 3, 4, 7, rng)
        n2 = fbm(H, W, 6, 5, 5, rng)
        cov = (1 - yy / 1000.0) * 0.95 + (1 - xx / 3840.0) * 0.55 - 0.38
        cov -= 0.75 * np.exp(-(dn / 0.115) ** 2)
        cov -= 0.55 * np.exp(-(((xx - 3180) / 300) ** 2 + ((yy - 330) / 190) ** 2))  # window for the morning star
        cov += 0.35 * np.exp(-((xx - 300) / 900) ** 2) * (yy < 1100)
        c = smoothstep(0.0, 0.26, n - (0.63 - 0.47 * np.clip(cov, -0.4, 1.2)))
        # lit undersides: density falls off toward the sun
        ll = np.sqrt(dx * dx + dy * dy) + 1e-3
        sh = 46 * k
        mapx = (xx * k + dx / ll * sh).astype(np.float32)
        mapy = (yy * k + dy / ll * sh).astype(np.float32)
        cs = cv2.remap(c, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        rimc = np.clip((c - cs) * 2.6, 0, 1)
        dark = (np.array([0.20, 0.21, 0.32], np.float32)[None, None] * (1 - n2[..., None] * 0.5)
                + np.array([0.40, 0.36, 0.47], np.float32)[None, None] * (n2[..., None] * 0.5))
        dark = dark * (0.62 + 0.38 * np.clip(xx / 2600.0, 0, 1))[..., None]
        litcol = ramp(dn * 0.55, stops) * np.array([1.0, 0.9, 0.86], np.float32)
        lit = (rimc * np.exp(-dn / 0.20) * 1.15)[..., None]
        glowthru = (np.exp(-dn / 0.16) * 0.38)[..., None]
        cloud = dark * (1 - glowthru) + litcol * glowthru
        cloud = cloud * (1 - lit) + litcol * lit
        sky = sky * (1 - c[..., None] * 0.94) + cloud * (c[..., None] * 0.94)
        # long bars of stratus burning near the horizon
        n3 = fbm(H, W, 34, 3, 4, rng)
        bar = smoothstep(0.60, 0.74, n3) * smoothstep(560, 760, yy) * smoothstep(1090, 1010, yy)
        barcol = ramp(np.clip(dn * 0.9 + 0.10, 0, 1), stops) * np.array([0.92, 0.78, 0.86], np.float32)
        edge = np.clip(bar - np.roll(bar, int(-7 * k), axis=0), 0, 1)[..., None]
        sky = sky * (1 - bar[..., None] * 0.7) + barcol * bar[..., None] * 0.7
        sky = sky + edge * np.array([0.5, 0.36, 0.2], np.float32) * np.exp(-dn / 0.2)[..., None]
        # faint rays
        angle = np.arctan2(dy, dx)
        rn = np.interp((angle + math.pi) / (2 * math.pi) * 720, np.arange(721),
                       np.convolve(rng.random(725), np.ones(5) / 5, 'valid'))
        rays = smoothstep(0.52, 0.75, rn) * np.exp(-dn / 0.14) * (dy < 0) * 0.12
        sky = sky + rays[..., None] * np.array([1.0, 0.85, 0.6], np.float32)
        self.img = sky.astype(np.float32)
        self.detail[:] = 0.12 + 0.25 * np.exp(-dn / 0.12)
        # the sun itself
        d = np.sqrt(dx * dx + dy * dy)
        disc = smoothstep(36, 30, d)[..., None]
        halo = (np.exp(-d / 95.0) * 0.75 + np.exp(-d / 330.0) * 0.30)[..., None]
        self.img = self.img + halo * np.array([1.0, 0.88, 0.62], np.float32)
        self.img = self.img * (1 - disc) + np.array([1.0, 1.0, 0.95], np.float32) * disc
        # morning star
        ds = np.sqrt((xx - 3185) ** 2 + (yy - 318) ** 2)
        star = (np.exp(-(ds / 3.2) ** 2) * 1.0 + np.exp(-ds / 16.0) * 0.28)[..., None]
        self.img = self.img + star * np.array([1.0, 0.97, 0.9], np.float32)
        self.detail = np.maximum(self.detail, np.exp(-(ds / 14.0) ** 2))

    # ---------------------------------------------------------------
    def mountains(self):
        rng, xx, yy = self.rng, self.xx, self.yy
        x = np.arange(self.W) / self.k

        def n1(cells, octv=5):
            out = np.zeros(self.W)
            amp, tot = 1.0, 0
            for _ in range(octv):
                g = rng.random(cells + 2)
                out += amp * np.interp(np.linspace(0, cells, self.W), np.arange(cells + 2), g)
                tot += amp
                amp *= 0.5
                cells *= 2
            return out / tot

        ax = np.abs(x - SX)
        side = np.where(x < SX, 1.3, 0.85)
        r1 = YH + 4 - (8 + 300 * smoothstep(60, 1900, ax) ** 1.05 * (0.45 + 1.1 * n1(7)) * side)
        r2 = YH + 6 - (4 + 120 * smoothstep(150, 1500, ax) * (0.4 + 1.2 * n1(11)) * side)
        self.r1, self.r2 = r1, r2
        glow = np.exp(-self.dn / 0.10)[..., None]
        tex = fbm(self.H, self.W, 30, 40, 4, rng)
        facet = smoothstep(0.45, 0.7, tex + 0.25 * np.sign(SX - xx) * (np.roll(tex, int(12 * self.k), 1) - tex) * 8)
        m1 = smoothstep(-1.5, 1.5, yy - r1[None, :])[..., None]
        shadow = np.array([0.50, 0.50, 0.69], np.float32)
        light = np.array([0.98, 0.80, 0.70], np.float32)
        col = shadow * (1 - facet[..., None] * 0.55) + light * facet[..., None] * 0.55
        col = col * (1 - glow * 0.75) + np.array([1.0, 0.86, 0.62], np.float32) * glow * 0.75
        self.img = self.img * (1 - m1) + col * m1
        m2 = smoothstep(-1.5, 1.5, yy - r2[None, :])[..., None]
        tex2 = fbm(self.H, self.W, 60, 90, 3, rng)[..., None]
        col2 = np.array([0.30, 0.33, 0.50], np.float32) * (0.8 + 0.5 * tex2)
        col2 = col2 * (1 - glow * 0.6) + np.array([0.98, 0.74, 0.52], np.float32) * glow * 0.6
        self.img = self.img * (1 - m2) + col2 * m2
        self.detail = np.maximum(self.detail, (m1[..., 0] * 0.35) * (yy < YH + 10))

    # ---------------------------------------------------------------
    def crest(self):
        pts = np.array([(0, 1760), (700, 1730), (1200, 1680), (1650, 1622), (2077, 1602), (2500, 1598),
                        (2800, 1626), (3150, 1700), (3500, 1790), (3840, 1830)], float)
        x = np.arange(self.W) / self.k
        y = np.interp(x, pts[:, 0], pts[:, 1])
        ksz = int(240 * self.k) | 1
        y = np.convolve(np.pad(y, ksz // 2, mode='edge'), np.ones(ksz) / ksz, 'valid')
        return y

    def ground(self):
        k, rng, xx, yy = self.k, self.rng, self.xx, self.yy
        T = fbm(1024, 1024, 7, 7, 6, rng)
        d = np.clip(yy - YH, 1.0, None)
        mu = ((xx - SX) / (d + 26) * 150 + 512).astype(np.float32)
        mv = (150 * 2600 / (d + 26) * 0.35).astype(np.float32)
        pat = cv2.remap(T, mu % 1024, mv % 1024, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        pat = cv2.GaussianBlur(pat, (0, 0), 1.2)
        big = fbm(self.H, self.W, 5, 7, 3, rng)
        p = np.clip((yy - YH) / (2160 - YH), 0, 1)
        # the path of light under the sun
        wp = np.exp(-((xx - SX) / (230 + 1.05 * d)) ** 2)
        far = np.exp(-p / 0.16)
        lit = smoothstep(0.40, 0.72, pat * 0.75 + big * 0.35)
        L = np.clip(lit * (0.16 + 0.85 * wp) + far * (0.42 + 0.5 * wp) + 0.22 * wp * (1 - p), 0, 1)
        yc = self.crest()[None, :]
        near = smoothstep(-8, 90, yy - yc)
        L = L * (1 - 0.42 * near * (1 - 0.6 * wp))
        crestline = np.exp(-((yy - yc + 5) / 7.0) ** 2) * (1 - 0.3 * wp)
        L = np.clip(L + crestline * 0.16, 0, 1)
        self.groundL = L
        shadow = ramp(p, [(0, (0.60, 0.58, 0.72)), (0.25, (0.44, 0.46, 0.65)), (0.6, (0.31, 0.35, 0.55)),
                          (1.0, (0.19, 0.22, 0.40))])
        light = ramp(p, [(0, (1.0, 0.90, 0.70)), (0.3, (1.0, 0.92, 0.78)), (1.0, (0.99, 0.86, 0.74))])
        # blush at the edge of light: rose half-tones
        half = np.exp(-((L - 0.45) / 0.22) ** 2)[..., None] * np.array([0.10, 0.0, -0.03], np.float32)
        g = shadow * (1 - L[..., None]) + light * L[..., None] + half
        g = g * (0.94 + 0.12 * pat[..., None])
        m = smoothstep(-1, 1, yy - YH)[..., None]
        self.img = self.img * (1 - m) + g * m
        self.detail = np.maximum(self.detail, m[..., 0] * (0.22 + 0.2 * wp))

    # ---------------------------------------------------------------
    def stream_and_village(self):
        k = self.k
        cl = [(3060, 1102), (2860, 1118), (3200, 1146), (2780, 1196), (3300, 1280), (2900, 1420), (3330, 1660), (3180, 1900), (3560, 2230)]
        ws = [4, 7, 12, 22, 40, 78, 150, 300, 620]
        pg = ribbon(cl, ws, 140)
        m = self.mask(lambda c: (poly(c, pg), c.fill()))
        en = fbm(self.H, self.W, 50, 70, 4, self.rng)
        pp = np.clip((self.yy - YH) / (2160 - YH), 0, 1)
        m = smoothstep(0.38, 0.62, cv2.GaussianBlur(m, (0, 0), 3 * k) + (en - 0.5) * 0.55 * smoothstep(0.02, 0.4, pp) * (m > 0.02))
        p = np.clip((self.yy - YH) / (2160 - YH), 0, 1)
        water = ramp(p, [(0, (1.0, 0.86, 0.60)), (0.15, (0.98, 0.74, 0.50)), (0.33, (0.74, 0.55, 0.52)),
                         (0.55, (0.30, 0.31, 0.47)), (1.0, (0.075, 0.10, 0.20))])
        rip = fbm(self.H, self.W, 120, 10, 3, self.rng)
        glint = smoothstep(0.62, 0.8, rip)[..., None] * np.array([0.55, 0.36, 0.18], np.float32) * (1 - p[..., None] * 0.5)
        water = water * (0.95 + 0.1 * rip[..., None]) + glint * 0.6
        self.img = self.img * (1 - m[..., None]) + water * m[..., None]
        # ice shelves along the banks, snow lip
        edge = np.clip(cv2.GaussianBlur(m, (0, 0), 9 * k) - 0.0, 0, 1)
        ice = np.clip(1 - np.abs(edge - 0.55) / 0.18, 0, 1) * m * smoothstep(0.1, 0.5, p)
        self.img = self.img * (1 - ice[..., None] * 0.55) + np.array([0.62, 0.70, 0.86], np.float32) * ice[..., None] * 0.55
        bank = np.clip(cv2.GaussianBlur(m, (0, 0), 5 * k) * (1 - m) * 3, 0, 1) * smoothstep(0.05, 0.4, p)
        self.img = self.img * (1 - bank[..., None] * 0.5) + np.array([0.20, 0.22, 0.40], np.float32) * bank[..., None] * 0.5
        self.detail = np.maximum(self.detail, m * 0.45)
        self.stream_mask = m
        rr = np.random.default_rng(61)
        ys, xs = np.where((m > 0.95) & (pp > 0.30))
        sel = rr.choice(len(ys), 16, replace=False)
        stones = sorted([(ys[i] / k, xs[i] / k) for i in sel])

        def rocks(c):
            for (y, x) in stones:
                s_ = 16 + 70 * ((y - YH) / (2160 - YH)) ** 1.5 * rr.uniform(0.6, 1.3)
                c.set_source_rgba(0.05, 0.06, 0.12, 0.9)
                c.save(); c.translate(x, y + s_ * 0.25); c.scale(1.5, 0.45); c.arc(0, 0, s_, 0, 7); c.fill(); c.restore()
                c.set_source_rgba(0.50, 0.55, 0.78, 1)
                c.save(); c.translate(x, y); c.scale(1.4, 0.5); c.arc(0, 0, s_, 0, 7); c.fill(); c.restore()
                c.set_source_rgba(1.0, 0.86, 0.72, 0.95)
                c.save(); c.translate(x - s_ * 0.25, y - s_ * 0.16); c.scale(1.2, 0.3); c.arc(0, 0, s_ * 0.8, 0, 7); c.fill(); c.restore()

        # the distant church: where the road leads
        def church(c):
            c.set_source_rgb(0.20, 0.20, 0.33)
            c.rectangle(3050, 1062, 86, 36); c.fill()
            poly(c, [(3044, 1064), (3093, 1036), (3142, 1064)]); c.fill()
            c.rectangle(3030, 1022, 24, 76); c.fill()
            poly(c, [(3027, 1024), (3042, 958), (3057, 1024)]); c.fill()
            c.set_source_rgb(0.20, 0.20, 0.33)
            c.set_line_width(2.2); c.move_to(3042, 962); c.line_to(3042, 942); c.stroke()
            c.move_to(3035, 950); c.line_to(3049, 950); c.stroke()
            # snow on roofs catching light on the sunward (left) pitch
            c.set_source_rgb(0.97, 0.80, 0.66)
            poly(c, [(3044, 1064), (3093, 1036), (3096, 1041), (3050, 1067)]); c.fill()
            poly(c, [(3027, 1024), (3042, 958), (3044, 966), (3031, 1026)]); c.fill()
            c.set_source_rgb(0.55, 0.56, 0.74)
            poly(c, [(3093, 1036), (3142, 1064), (3136, 1066), (3094, 1042)]); c.fill()
            # lit windows - the lamp is burning
            c.set_source_rgb(1.0, 0.72, 0.25)
            for wx in (3064, 3084, 3104, 3122):
                c.rectangle(wx, 1074, 6, 13); c.fill()
            c.rectangle(3039, 1040, 5, 10); c.fill()
            # cottages
            for (hx, hy, hw) in [(2960, 1082, 40), (3170, 1080, 46), (3235, 1086, 34), (2900, 1090, 30), (3300, 1090, 38)]:
                c.set_source_rgb(0.22, 0.21, 0.33)
                c.rectangle(hx, hy, hw, 18); c.fill()
                c.set_source_rgb(0.62, 0.60, 0.76)
                poly(c, [(hx - 4, hy + 1), (hx + hw / 2, hy - 15), (hx + hw + 4, hy + 1)]); c.fill()
                c.set_source_rgb(0.98, 0.78, 0.62)
                poly(c, [(hx - 4, hy + 1), (hx + hw / 2, hy - 15), (hx + hw / 2 + 3, hy - 11), (hx + 2, hy + 3)]); c.fill()
                c.set_source_rgb(1.0, 0.70, 0.25)
                c.rectangle(hx + hw * 0.55, hy + 6, 5, 6); c.fill()
            # dark clumps of trees round the village
            rr = np.random.default_rng(5)
            for i in range(60):
                tx = rr.uniform(2700, 3840); ty = rr.uniform(1082, 1106)
                s = rr.uniform(8, 26)
                c.set_source_rgba(0.17, 0.18, 0.30, 0.9)
                c.save(); c.translate(tx, ty); c.scale(1.0, 0.8); c.arc(0, -s * 0.5, s * 0.6, 0, 7); c.fill(); c.restore()
        self.overlay(church, detail=1.0)

        def smoke(c):
            c.set_source_rgba(0.93, 0.74, 0.70, 0.55)
            smooth(c, ribbon([(3186, 1064), (3192, 1020), (3215, 975), (3262, 935), (3330, 905)], [4, 10, 20, 34, 50], 40))
            c.fill()
        self.overlay(smoke, blur=7)
        # village glow
        g = np.exp(-(((self.xx - 3095) / 150) ** 2 + ((self.yy - 1080) / 40) ** 2))[..., None]
        self.img += g * np.array([0.10, 0.05, 0.0], np.float32)

    # ---------------------------------------------------------------
    @staticmethod
    def spruce(c, x, yb, h, rr, dark, snow, rimc, sunside=1, wf=0.40, snowy=1.0):
        w = h * wf
        tiers = int(9 + h / 48)
        c.set_source_rgb(*[v * 0.8 for v in dark])
        c.set_line_width(max(h * 0.022, 1.0))
        c.move_to(x, yb); c.line_to(x, yb - h * 0.5); c.stroke()
        for i in range(tiers):
            t = i / tiers
            y = yb - h * 0.07 - t * h * 0.90
            hw = (w * 0.5 * (1 - t) ** 0.8 + h * 0.012) * rr.uniform(0.78, 1.18)
            th = h / tiers * 2.1
            lean = rr.uniform(-0.1, 0.1) * hw
            pts = [(x + lean * 0.3, y - th)]
            nj = 7
            xs = np.linspace(-hw, hw, nj)
            right = [(x + xs[j] + rr.uniform(-0.08, 0.08) * hw,
                      y + (abs(xs[j]) / hw) ** 1.5 * th * 0.28 - rr.uniform(0, 0.3) * th * (j % 2)) for j in range(nj)]
            pts += right[::-1]
            c.set_source_rgb(*[v * rr.uniform(0.85, 1.15) for v in dark])
            poly(c, pts); c.fill()
            # snow load on the bough
            if snowy > 0:
                for sd in (-1, 1):
                    f = rr.uniform(0.35, 0.95)
                    if rr.random() < 0.3:
                        continue
                    col = snow if sd != sunside else [snow[j] * 0.55 + rimc[j] * 0.45 for j in range(3)]
                    c.set_source_rgba(col[0], col[1], col[2], 0.9 * snowy)
                    smooth(c, [(x + sd * hw * 0.06, y - th * 0.86), (x + sd * hw * 0.5 * f, y - th * 0.48),
                               (x + sd * hw * f, y - th * 0.02 + (f ** 1.5) * th * 0.2),
                               (x + sd * hw * 0.62 * f, y - th * 0.16), (x + sd * hw * 0.22, y - th * 0.50)])
                    c.fill()
            # warm rim where the dawn finds the edge
            if rr.random() < 0.22:
                c.set_source_rgba(rimc[0], rimc[1], rimc[2], 0.45)
                f = rr.uniform(0.45, 1.0)
                c.save(); c.translate(x + sunside * hw * f, y - th * 0.02 + (f ** 1.5) * th * 0.2 - th * 0.08)
                c.rotate(sunside * 0.5); c.scale(1.0, 0.35)
                c.arc(0, 0, max(hw * 0.16, 1.2), 0, 7); c.fill(); c.restore()

    def forest(self):
        rr = np.random.default_rng(11)

        def top(x):
            return 640 + 462 * np.clip(x / 1680.0, 0, 1) ** 0.8

        def low(x):
            return 1296 - 196 * np.clip(x / 1680.0, 0, 1)

        def base(c):
            xs = np.linspace(0, 1700, 80)
            pts = [(x, top(x) + 40 + 14 * math.sin(x * 0.02)) for x in xs] + [(x, low(x) - 8) for x in xs[::-1]]
            c.set_source_rgb(0.085, 0.105, 0.15)
            poly(c, pts); c.fill()
        self.overlay(base, blur=3, detail=0.5)
        trees = []
        for i in range(520):
            x = rr.uniform(-40, 1720)
            t = rr.random() ** 0.8
            y = top(x) + 40 + t * (low(x) - top(x) - 30)
            size = (34 + 250 * (1 - min(max(x, 0), 1700) / 1700.0) ** 1.5) * rr.uniform(0.7, 1.25) * (0.55 + 0.5 * t)
            trees.append((y, x, size))
        trees.sort()

        def draw(c):
            for (y, x, s) in trees:
                depth = np.clip((y - 700) / 600.0, 0, 1)
                dark = (0.07 + 0.06 * (1 - depth), 0.09 + 0.07 * (1 - depth), 0.13 + 0.10 * (1 - depth))
                self.spruce(c, x, y, s, rr, dark, (0.36, 0.41, 0.58), (0.66, 0.56, 0.62), sunside=1, snowy=0.85)
        self.overlay(draw, detail=0.55)
        # mist at the foot of the wood
        xx, yy = self.xx, self.yy
        mist = np.exp(-((yy - low(xx)) / 46.0) ** 2) * smoothstep(1800, 500, xx) * 0.35
        self.img = self.img * (1 - mist[..., None]) + np.array([0.46, 0.49, 0.68], np.float32) * mist[..., None]

    def mid_trees(self):
        rr = np.random.default_rng(23)

        def draw(c):
            for (x, yb, h) in [(2590, 1160, 150), (2650, 1172, 110), (3330, 1190, 190), (3420, 1178, 130),
                               (1830, 1150, 120), (1760, 1140, 90), (3700, 1230, 260)]:
                self.spruce(c, x, yb, h, rr, (0.13, 0.15, 0.25), (0.50, 0.52, 0.72), (0.98, 0.74, 0.55),
                            sunside=-1 if x > SX else 1, snowy=0.8)
            # fence posts wandering down to the village
            for i in range(14):
                t = i / 13.0
                x = 2560 + 420 * t + 40 * math.sin(t * 5)
                y = 1420 - 300 * t ** 0.75
                hh = 46 * (1 - t) + 8
                c.set_source_rgb(0.16, 0.14, 0.2)
                c.set_line_width(max(6 * (1 - t), 1.4))
                c.move_to(x, y); c.line_to(x + rr.uniform(-3, 3), y - hh); c.stroke()
                c.set_source_rgb(1.0, 0.85, 0.66)
                c.set_line_width(max(2 * (1 - t), 0.8))
                c.move_to(x - 2.5 * (1 - t), y); c.line_to(x - 2.5 * (1 - t), y - hh); c.stroke()
        self.overlay(draw, detail=0.7)

    # ---------------------------------------------------------------
    def shadows(self):
        """long blue shadows thrown toward us, fanning from the point under the sun"""
        k = self.k
        yb = GY0

        def wedge(c, xa, xb, y0, soft=0):
            f = (2260 - YH) / (y0 - YH)
            poly(c, [(xa, y0), (xb, y0), (SX + (xb - SX) * f, 2260), (SX + (xa - SX) * f, 2260)])
            c.fill()

        def draw(c):
            wedge(c, GX0 - 372 * GS, GX0 - 52 * GS, yb - 4)      # penitent (and cloak)
            wedge(c, GX0 + 78 * GS, GX0 + 430 * GS, yb - 4)      # priest and log
            wedge(c, 3575, 3640, 1580)                           # right-hand tree
        m = self.mask(draw)
        m = cv2.GaussianBlur(m, (0, 0), 7 * k)
        m2 = cv2.GaussianBlur(m, (0, 0), 30 * k)
        p = np.clip((self.yy - GY0) / (2160 - GY0), 0, 1)
        m = m * (1 - p) + m2 * p
        m *= 0.74 * (0.80 + 0.4 * fbm(self.H, self.W, 9, 14, 4, self.rng))
        m = np.clip(m, 0, 1)
        sh = ramp(np.clip((self.yy - YH) / (2160 - YH), 0, 1),
                  [(0, (0.46, 0.50, 0.72)), (0.5, (0.33, 0.38, 0.62)), (1, (0.20, 0.24, 0.45))])
        tex = fbm(self.H, self.W, 40, 30, 3, self.rng)[..., None]
        sh = sh * (0.9 + 0.2 * tex)
        self.img = self.img * (1 - m[..., None]) + sh * m[..., None]
        # shadows of the left-hand spruces striping the snow
        def tsh(c):
            for (x, y, w_) in [(120, 1800, 190), (520, 1610, 150), (860, 1505, 70)]:
                f = (2260 - YH) / (y - YH)
                poly(c, [(x - w_ / 2, y), (x + w_ / 2, y), (SX + (x + w_ / 2 - SX) * f, 2260), (SX + (x - w_ / 2 - SX) * f, 2260)])
                c.fill()
        m = cv2.GaussianBlur(self.mask(tsh), (0, 0), 22 * k) * 0.6
        self.img = self.img * (1 - m[..., None]) + sh * m[..., None]

    def footprints(self):
        path = np.array([(300, 2200), (520, 2050), (680, 1960), (880, 1880), (1030, 1790), (1140, 1705), (1222, 1640)], float)
        t = np.linspace(0, len(path) - 1, 400)
        xs = np.interp(t, np.arange(len(path)), path[:, 0])
        ys = np.interp(t, np.arange(len(path)), path[:, 1])
        ker = np.ones(31) / 31
        xs = np.convolve(np.pad(xs, 15, mode='edge'), ker, 'valid')
        ys = np.convolve(np.pad(ys, 15, mode='edge'), ker, 'valid')
        seg = np.hypot(np.diff(xs), np.diff(ys))
        cum = np.concatenate([[0], np.cumsum(seg)])
        rr = np.random.default_rng(3)
        prints = []
        s, side = 30.0, 1
        while s < cum[-1] - 10:
            i = min(np.searchsorted(cum, s), len(xs) - 2)
            x, y = xs[i], ys[i]
            dx, dy = xs[i + 1] - xs[i], ys[i + 1] - ys[i]
            L = math.hypot(dx, dy); dx, dy = dx / L, dy / L
            sc = 0.16 + 0.95 * (y - YH) / (2160 - YH)
            ln = 92 * sc
            ox, oy = -dy * side * ln * 0.42, dx * side * ln * 0.25
            prints.append((x + ox + rr.uniform(-4, 4) * sc, y + oy, math.atan2(dy * 0.55, dx) + rr.uniform(-0.2, 0.2), ln))
            s += ln * rr.uniform(0.95, 1.25)   # short, stumbling steps
            side = -side

        def holes(c):
            for (x, y, a, ln) in prints:
                c.save(); c.translate(x, y); c.rotate(a); c.scale(ln * 0.5, ln * 0.24)
                c.set_source_rgba(0.13, 0.16, 0.33, 0.95)
                c.arc(0, 0, 1, 0, 7); c.fill()
                c.restore()
        self.overlay(holes, blur=1.6, detail=0.75)

        def lips(c):
            for (x, y, a, ln) in prints:
                c.save(); c.translate(x, y + ln * 0.05); c.rotate(a); c.scale(ln * 0.5, ln * 0.24)
                c.set_source_rgba(1.0, 0.88, 0.74, 0.9)
                c.set_line_width(0.2)
                c.arc(0, 0, 1.08, 0.25, 2.6); c.stroke()
                c.set_source_rgba(0.07, 0.09, 0.22, 0.85)
                c.arc(0, -0.25, 0.72, 3.4, 6.0); c.fill()
                c.restore()
        self.overlay(lips, blur=1.0)

    # ---------------------------------------------------------------
    def bare_tree(self):
        def tree(c, off, col, wmul, seed=41):
            rr = np.random.default_rng(seed)
            c.set_source_rgba(*col)

            def branch(x, y, ang, ln, w, depth):
                if depth == 0 or w < 0.7:
                    return
                segs = 3
                for i in range(segs):
                    a2 = ang + rr.normal(0, 0.10)
                    x2, y2 = x + math.cos(a2) * ln / segs, y + math.sin(a2) * ln / segs
                    c.set_line_width(max(w * (1 - 0.1 * i) * wmul, 0.7))
                    c.move_to(x + off[0] * w * 0.05, y + off[1] * w * 0.05)
                    c.line_to(x2 + off[0] * w * 0.05, y2 + off[1] * w * 0.05)
                    c.stroke()
                    x, y, ang = x2, y2, a2
                n = 2 if rr.random() < 0.55 else 3
                for i in range(n):
                    spread = rr.normal(0, 0.30) + (0.36 if i == 0 else (-0.36 if i == 1 else 0.0))
                    na = ang + spread
                    na = na * 0.72 + (-math.pi / 2 - 0.1) * 0.28
                    branch(x, y, na, ln * rr.uniform(0.62, 0.84), w * rr.uniform(0.52, 0.66), depth - 1)
            branch(3610, 1600, -math.pi / 2 - 0.02, 300, 62, 10)
        self.overlay(lambda c: tree(c, (0, 0), (0.09, 0.075, 0.10, 1), 1.0), detail=0.75)
        self.overlay(lambda c: tree(c, (-7, -2), (1.0, 0.76, 0.50, 0.55), 0.13), detail=0.75)

    def big_spruces(self):
        rr = np.random.default_rng(77)

        def draw(c):
            for (x, yb, h) in [(-90, 1930, 1700), (860, 1500, 430), (520, 1600, 1090), (120, 1800, 1640)]:
                self.spruce(c, x, yb, h, rr, (0.050, 0.065, 0.085), (0.30, 0.36, 0.54), (0.50, 0.46, 0.60),
                            sunside=1, wf=0.44, snowy=0.95)
        self.overlay(draw, detail=0.6)

    # ---------------------------------------------------------------
    def cross(self):
        wood = (0.21, 0.15, 0.12)
        R = self.relief
        R(lambda c: (c.rectangle(190, -1198, 50, 1185), c.fill()), wood, sig=(3, 9), rim=1.25)
        R(lambda c: (c.rectangle(-82, -986, 594, 46), c.fill()), wood, sig=(3, 9), rim=1.1)
        # corpus
        flesh = (0.74, 0.64, 0.55)
        R(lambda c: (smooth(c, ribbon([(-58, -966), (40, -935), (120, -905), (178, -890)], [15, 19, 24, 30], 30)), c.fill()), flesh, sig=(2.5, 7))
        R(lambda c: (smooth(c, ribbon([(488, -966), (390, -935), (310, -905), (252, -890)], [15, 19, 24, 30], 30)), c.fill()), flesh, sig=(2.5, 7))
        R(lambda c: (smooth(c, [(190, -692), (252, -692), (244, -640), (226, -598), (236, -540), (238, -500), (224, -474),
                               (204, -480), (203, -532), (182, -592), (178, -642)]), c.fill()), flesh, sig=(3, 8))
        R(lambda c: (smooth(c, [(168, -902), (215, -894), (262, -902), (268, -856), (254, -800), (258, -738), (192, -738),
                               (190, -798), (166, -852)]), c.fill()), flesh, sig=(3, 10))
        R(lambda c: (smooth(c, [(182, -748), (254, -748), (268, -712), (284, -650), (266, -664), (252, -668), (216, -676), (184, -682)]),
                     c.fill()), (0.86, 0.84, 0.82), sig=(2.5, 7))
        # bowed head, inclined toward the penitent
        R(lambda c: (smooth(c, [(176, -938), (198, -944), (214, -930), (216, -908), (206, -888), (190, -880), (176, -890), (168, -912)]),
                     c.fill()), flesh, sig=(2.5, 7))
        # hair falling forward, beard
        R(lambda c: (smooth(c, [(170, -936), (190, -952), (214, -944), (226, -922), (228, -892), (220, -868), (212, -880), (214, -912),
                               (204, -930), (184, -930), (172, -916), (164, -888), (158, -866), (154, -892), (160, -920)]),
                     c.fill()), (0.20, 0.13, 0.10), sig=(2, 6))
        # the face lost in its own shadow
        self.overlay(lambda c: (c.set_source_rgba(0.24, 0.16, 0.15, 0.55),
                                smooth(c, [(172, -906), (192, -900), (212, -906), (206, -884), (190, -876), (176, -886)]), c.fill()),
                     group=True, blur=3, detail=1.0)

        def thorns(c):
            c.set_source_rgb(0.12, 0.08, 0.06); c.set_line_width(2)
            rr = np.random.default_rng(2)
            for i in range(22):
                a = rr.uniform(0, 6.28)
                c.move_to(194 + 24 * math.cos(a), -932 + 8 * math.sin(a))
                c.line_to(194 + 32 * math.cos(a + 0.3), -934 + 13 * math.sin(a + 0.3))
                c.stroke()
            # ribs, shadow under the chest
            c.set_source_rgba(0.25, 0.18, 0.2, 0.45); c.set_line_width(2.2)
            for i in range(4):
                y = -845 + i * 14
                c.move_to(184, y); c.curve_to(200, y + 6, 232, y + 6, 250, y); c.stroke()
            c.move_to(216, -888); c.line_to(217, -760); c.stroke()
            c.set_source_rgba(0.35, 0.05, 0.05, 0.8); c.set_line_width(2)
            c.move_to(240, -838); c.line_to(243, -812); c.stroke()
        self.overlay(thorns, group=True, detail=1.0)
        R(lambda c: (c.rectangle(196, -480, 38, 16), c.fill()), wood, sig=(2, 5))
        # titulus
        R(lambda c: (c.rectangle(180, -1060, 70, 34), c.fill()), (0.62, 0.55, 0.46), sig=(2, 5))
        # little gabled roof, as on an alpine wayside cross
        R(lambda c: (poly(c, [(215, -1244), (-128, -1040), (-116, -1020), (215, -1216)]), c.fill()), wood, sig=(3, 8), rim=1.2)
        R(lambda c: (poly(c, [(215, -1244), (558, -1040), (546, -1020), (215, -1216)]), c.fill()), wood, sig=(3, 8), rim=0.5)
        # snow lying on the roof and the arms
        snow = (0.74, 0.78, 0.93)
        R(lambda c: (smooth(c, [(215, -1262), (150, -1232), (40, -1166), (-60, -1104), (-134, -1052), (-126, -1038), (-40, -1088), (60, -1150), (215, -1244)]),
                     c.fill()), snow, sig=(3, 8), rim=1.3, amb=0.8)
        R(lambda c: (smooth(c, [(215, -1262), (290, -1230), (390, -1168), (480, -1110), (564, -1052), (556, -1038), (470, -1088), (370, -1150), (215, -1244)]),
                     c.fill()), snow, sig=(3, 8), rim=0.7, amb=0.8)
        R(lambda c: (smooth(c, [(-84, -986), (-70, -998), (-30, -996), (-10, -986)]), c.fill()), snow, sig=(2, 5), amb=0.8)
        R(lambda c: (smooth(c, [(440, -986), (470, -998), (505, -996), (514, -986)]), c.fill()), snow, sig=(2, 5), amb=0.8)

    # ---------------------------------------------------------------
    def head(self, cx, cy, rot, mirror, sc, old):
        R = self.relief

        def T(fn):
            def g(c):
                c.save(); c.translate(cx, cy); c.rotate(rot); c.scale(mirror * sc, sc)
                fn(c)
                c.restore()
            return g
        prof = [(0, -50), (22, -46), (35, -34), (40, -18), (36, -10), (44, 0), (53, 9), (41, 14), (43, 20), (40, 25), (42, 30),
                (37, 36), (39, 46), (27, 53), (8, 48), (-8, 40), (-28, 32), (-45, 10), (-47, -12), (-38, -34), (-20, -47)]
        skin = (0.86, 0.66, 0.54) if not old else (0.84, 0.68, 0.60)
        R(T(lambda c: (smooth(c, prof), c.fill())), skin, sig=(2.2, 8), rim=1.25, amb=0.62)

        def feat(c):
            # eye socket, closed lid, brow, ear, mouth
            c.set_source_rgba(0.22, 0.12, 0.12, 0.55)
            c.arc(27, -8, 7, 0, 7); c.fill()
            c.set_source_rgba(0.12, 0.07, 0.07, 0.9); c.set_line_width(2.2)
            c.move_to(21, -6); c.curve_to(25, -2, 31, -3, 34, -7); c.stroke()
            c.set_line_width(2.6 if not old else 3.4)
            if old:
                c.set_source_rgba(0.80, 0.80, 0.84, 0.95)
            c.move_to(19, -17); c.curve_to(26, -21, 33, -19, 38, -15); c.stroke()
            c.set_source_rgba(0.30, 0.14, 0.12, 0.7); c.set_line_width(1.8)
            c.move_to(33, 25); c.line_to(41, 25); c.stroke()
            c.move_to(38, 13); c.curve_to(34, 14, 33, 10, 35, 8); c.stroke()
            c.set_source_rgba(0.42, 0.22, 0.18, 0.75); c.set_line_width(2.2)
            c.save(); c.translate(-6, 4); c.scale(0.62, 1); c.arc(0, 0, 10, 0.6, 5.8); c.stroke(); c.restore()
            c.set_source_rgba(0.25, 0.13, 0.12, 0.35)
            smooth(c, [(8, 48), (27, 52), (36, 40), (22, 34), (2, 30), (-8, 40)]); c.fill()  # jaw shadow
        self.overlay(T(feat), group=True, detail=1.0)
        if not old:
            hair = [(34, -40), (24, -52), (4, -58), (-22, -55), (-44, -36), (-54, -6), (-50, 22), (-40, 40), (-26, 44), (-22, 26),
                    (-14, 8), (-4, -8), (10, -18), (24, -24), (33, -20), (42, -6), (46, -20), (42, -32)]
            R(T(lambda c: (smooth(c, hair), c.fill())), (0.17, 0.11, 0.085), sig=(2.2, 7), rim=1.3)
            # a tear takes the light
            self.overlay(T(lambda c: (c.set_source_rgba(1, 0.95, 0.8, 0.95), c.arc(31, 4, 2.2, 0, 7), c.fill(),
                                      c.set_source_rgba(1, 0.9, 0.7, 0.6), c.set_line_width(1.4),
                                      c.move_to(30, -2), c.line_to(31, 4), c.stroke())), group=True, detail=1.0)
        else:
            hair = [(2, -30), (-12, -44), (-32, -40), (-46, -20), (-51, 6), (-42, 30), (-26, 38), (-14, 30), (-12, 12), (-6, -6)]
            R(T(lambda c: (smooth(c, hair), c.fill())), (0.84, 0.84, 0.88), sig=(2.2, 6), rim=1.2, amb=0.8)
            beard = [(-6, 20), (6, 22), (22, 22), (36, 22), (45, 30), (44, 46), (36, 58), (20, 60), (4, 52), (-6, 40)]
            R(T(lambda c: (smooth(c, beard), c.fill())), (0.84, 0.84, 0.87), sig=(2.2, 6), rim=1.3, amb=0.8)

    def figures(self):
        R = self.relief
        ov = self.overlay
        # ---------------- the log the priest sits on ----------------
        R(lambda c: (smooth(c, [(250, -186), (415, -182), (436, -150), (440, -70), (424, -24), (250, -18)]), c.fill()),
          (0.25, 0.18, 0.14), sig=(4, 12), rim=0.5)
        ov(lambda c: (c.set_source_rgba(0.50, 0.38, 0.28, 0.9), c.save(), c.translate(426, -104), c.scale(0.28, 1),
                      c.arc(0, 0, 78, 0, 7), c.restore(), c.fill(),
                      c.set_source_rgba(0.26, 0.17, 0.12, 0.8), c.set_line_width(2.5),
                      c.save(), c.translate(426, -104), c.scale(0.28, 1), c.arc(0, 0, 50, 0, 7), c.restore(), c.stroke(),
                      c.save(), c.translate(426, -104), c.scale(0.28, 1), c.arc(0, 0, 24, 0, 7), c.restore(), c.stroke()),
           group=True, detail=0.8)
        R(lambda c: (smooth(c, [(300, -188), (330, -214), (380, -220), (424, -206), (444, -182), (420, -176), (360, -180)]), c.fill()),
          (0.78, 0.82, 0.95), sig=(3, 9), amb=0.8, rim=0.6)

        # ---------------- PENITENT ----------------
        # legs
        R(lambda c: (smooth(c, [(-212, -178), (-150, -172), (-90, -120), (-38, -62), (-16, -30), (-22, -4), (-60, 2), (-150, 2),
                               (-235, 2), (-262, -14), (-250, -40), (-200, -50), (-160, -58), (-185, -90), (-228, -110), (-240, -150)]),
                     c.fill()), (0.27, 0.20, 0.17), sig=(4, 12), rim=1.2)
        # neck
        R(lambda c: (smooth(c, [(-130, -372), (-102, -402), (-70, -378), (-68, -338), (-98, -336)]), c.fill()),
          (0.80, 0.60, 0.50), sig=(3, 8))
        # torso in a poor linen shirt - the white garment under the scarlet
        shirt = (0.90, 0.87, 0.80)
        R(lambda c: (smooth(c, [(-128, -380), (-176, -364), (-218, -316), (-240, -246), (-246, -170), (-242, -116), (-192, -106),
                               (-140, -126), (-98, -138), (-86, -190), (-76, -250), (-68, -300), (-74, -346), (-100, -370)]),
                     c.fill()), shirt, sig=(4, 16), rim=1.25, amb=0.50, lz=-0.1, form=1.0)

        def shirtfolds(c):
            c.set_source_rgba(0.30, 0.32, 0.46, 0.5)
            for (a, b, w) in [((-120, -350), (-100, -200), 5), ((-150, -340), (-135, -180), 6), ((-190, -300), (-175, -150), 6),
                              ((-110, -250), (-92, -150), 4)]:
                c.set_line_width(w); c.move_to(*a); c.curve_to(a[0] + 12, (a[1] + b[1]) / 2, b[0] - 8, (a[1] + b[1]) / 2, *b); c.stroke()
            # ragged hem
            c.set_source_rgba(0.24, 0.22, 0.3, 0.7); c.set_line_width(3)
            for x in range(-236, -100, 17):
                c.move_to(x, -118 - (x + 236) * 0.1); c.line_to(x + 5, -100 - (x + 236) * 0.12); c.stroke()
        ov(shirtfolds, group=True, blur=1.2)

        # the scarlet cloak, slipping from his back and trailing into the tracks
        cloak = [(-138, -384), (-190, -372), (-236, -322), (-260, -250), (-272, -170), (-294, -100), (-344, -50), (-430, -26),
                 (-540, -10), (-650, 4), (-716, 30), (-650, 50), (-520, 42), (-400, 32), (-300, 16), (-248, 2), (-224, -60),
                 (-220, -120), (-212, -200), (-204, -280), (-180, -336), (-150, -358)]
        cm = self.mask(lambda c: (smooth(c, cloak), c.fill()), True)
        R(None, (0.80, 0.085, 0.07), sig=(5, 16), rim=1.15, amb=0.66, m=cm, suncol=(1.0, 0.55, 0.25), form=0.8)

        def cloakfolds(c):
            rr = np.random.default_rng(8)
            folds = [[(-160, -366), (-222, -300), (-246, -200), (-262, -110), (-330, -40), (-460, -8), (-600, 16)],
                     [(-150, -350), (-208, -270), (-232, -150), (-250, -60), (-320, -8), (-450, 18), (-560, 30)],
                     [(-190, -340), (-238, -230), (-262, -140), (-300, -70), (-400, -22), (-520, 0), (-680, 26)],
                     [(-232, -100), (-270, -30), (-340, 4), (-430, 22)]]
            for f in folds:
                c.set_source_rgba(0.30, 0.01, 0.04, 0.6); c.set_line_width(9)
                smooth(c, f, closed=False); c.stroke()
                c.set_source_rgba(1.0, 0.36, 0.16, 0.55); c.set_line_width(4)
                smooth(c, [(x + 7, y - 7) for (x, y) in f], closed=False); c.stroke()
        ov(cloakfolds, group=True, blur=1.6, clip=cm)

        def cloaksnow(c):  # fresh snow already whitening the scarlet where it lies
            rr = np.random.default_rng(9)
            for i in range(420):
                t = rr.random() ** 0.6
                x = -330 - t * 390 + rr.normal(0, 12)
                y = -40 + t * 70 + rr.normal(0, 14) - 6
                a = 0.25 + 0.75 * t
                r = rr.uniform(2, 7) * (0.6 + t)
                c.set_source_rgba(0.90, 0.90, 0.99, a)
                c.save(); c.translate(x, y); c.scale(1.6, 0.7); c.arc(0, 0, r, 0, 7); c.fill(); c.restore()
        ov(cloaksnow, group=True, clip=np.clip(cv2.GaussianBlur(cm, (0, 0), 4 * self.k) * 1.3, 0, 1), blur=0.8)

        # bare foot, sole up
        R(lambda c: (smooth(c, [(-262, -30), (-286, -44), (-320, -36), (-370, -12), (-368, 2), (-318, 0), (-270, -4)]), c.fill()),
          (0.78, 0.58, 0.48), sig=(2.5, 7), rim=0.9)
        ov(lambda c: (c.set_source_rgba(0.25, 0.14, 0.14, 0.5), c.set_line_width(3), c.move_to(-290, -22), c.line_to(-350, -6), c.stroke()),
           group=True, blur=1.5)
        # head
        self.head(-52, -400, math.radians(35), 1, 0.95, False)
        # near arm
        R(lambda c: (smooth(c, [(-162, -322), (-142, -360), (-110, -356), (-84, -310), (-62, -270), (-36, -310), (-22, -322), (-6, -293),
                               (-30, -240), (-55, -205), (-78, -208), (-120, -270)]), c.fill()),
          shirt, sig=(3.5, 11), rim=1.3, amb=0.56, lz=-0.1, form=0.9)
        ov(lambda c: (c.set_source_rgba(0.28, 0.30, 0.44, 0.5), c.set_line_width(4),
                      c.move_to(-130, -330), c.curve_to(-110, -290, -90, -250, -66, -222), c.stroke(),
                      c.move_to(-58, -236), c.line_to(-26, -290), c.stroke()), group=True, blur=1.2)
        # clasped hands
        R(lambda c: (smooth(c, [(-40, -314), (-38, -340), (-22, -352), (-4, -348), (4, -328), (0, -308), (-16, -298), (-32, -302)]), c.fill()),
          (0.86, 0.65, 0.53), sig=(2.2, 6), rim=1.3, amb=0.65)
        ov(lambda c: (c.set_source_rgba(0.30, 0.15, 0.13, 0.6), c.set_line_width(1.8),
                      [(c.move_to(-34 + i * 7, -340 + i * 2), c.line_to(-26 + i * 7, -312 + i * 2), c.stroke()) for i in range(4)]),
           group=True)

        # ---------------- PRIEST ----------------
        black = (0.115, 0.10, 0.115)
        # far arm lifted in absolution
        R(lambda c: (smooth(c, [(155, -404), (176, -452), (130, -476), (86, -493), (40, -530), (11, -546), (-13, -517), (8, -490),
                               (58, -446), (110, -424)]), c.fill()), black, sig=(3.5, 11), rim=1.3)
        # white cuff
        R(lambda c: (smooth(c, [(13, -548), (2, -558), (-20, -528), (-12, -514)]), c.fill()), (0.9, 0.9, 0.92), sig=(2, 5), amb=0.8)

        def hand(c):
            c.save(); c.translate(-2, -532); c.rotate(math.radians(-24)); c.scale(0.86, -0.86)
            smooth(c, [(-13, 0), (-17, 28), (-22, 40), (-29, 52), (-23, 60), (-14, 50), (-13, 60), (-11, 92), (-5, 98), (3, 99), (9, 92),
                       (10, 56), (17, 52), (21, 38), (16, 20), (12, 0)])
            c.restore(); c.fill()
        R(hand, (0.86, 0.68, 0.58), sig=(2.2, 6), rim=1.4, amb=0.66)
        # body: cassock and winter cape
        body = [(128, -438), (150, -464), (200, -454), (252, -426), (292, -370), (312, -300), (320, -220), (324, -120), (320, -40),
                (302, 2), (200, 4), (95, 4), (46, 2), (44, -12), (68, -30), (72, -110), (62, -190), (68, -224), (100, -240),
                (140, -242), (130, -300), (120, -380)]
        bm = R(lambda c: (smooth(c, body), c.fill()), black, sig=(5, 18), rim=1.25, depth=2.2)

        def cassockfolds(c):
            for (pts, w) in [([(110, -236), (100, -150), (112, -60), (104, 0)], 9), ([(150, -238), (160, -150), (150, -60), (170, 0)], 10),
                             ([(200, -230), (215, -140), (225, -50), (240, 0)], 10), ([(250, -400), (275, -300), (285, -200), (290, -80)], 10),
                             ([(210, -430), (232, -340), (245, -250)], 8), ([(80, -200), (84, -110), (78, -30)], 6)]:
                c.set_source_rgba(0.02, 0.02, 0.03, 0.45); c.set_line_width(w * 1.6)
                smooth(c, pts, closed=False); c.stroke()
                c.set_source_rgba(0.26, 0.27, 0.38, 0.32); c.set_line_width(w * 1.1)
                smooth(c, [(x - w * 0.9, y) for (x, y) in pts], closed=False); c.stroke()
            # buttons of the cassock
            c.set_source_rgba(0.38, 0.36, 0.46, 0.8)
            for i in range(5):
                c.arc(119 + i * 1.5, -400 + i * 15, 2.2, 0, 7); c.fill()
        ov(cassockfolds, group=True, blur=4.5, clip=bm)
        # roman collar
        R(lambda c: (poly(c, [(125, -441), (141, -452), (146, -444), (129, -432)]), c.fill()), (0.95, 0.95, 0.97), sig=(1.5, 3), amb=0.9)

        # the violet stole of the confessor
        violet = (0.50, 0.20, 0.66)
        far = ribbon([(124, -428), (112, -340), (104, -262), (70, -236), (50, -180), (46, -112)], [20, 22, 24, 24, 26, 27], 50)
        R(lambda c: (smooth(c, far), c.fill()), (0.36, 0.14, 0.50), sig=(2.5, 7), rim=1.2, amb=0.6)
        near = ribbon([(152, -458), (138, -420), (130, -330), (128, -262), (96, -244), (70, -206), (64, -140), (62, -84)],
                      [22, 28, 30, 30, 30, 31, 32, 34], 60)
        sm = R(lambda c: (smooth(c, near), c.fill()), violet, sig=(2.5, 8), rim=1.3, amb=0.72)

        def stoletrim(c):
            gold = (0.95, 0.74, 0.30)
            c.set_source_rgba(*gold, 0.95); c.set_line_width(3)
            c.move_to(64, -150); c.line_to(64, -116); c.stroke()
            c.move_to(52, -138); c.line_to(76, -138); c.stroke()
            c.set_line_width(2.4)
            for i in range(9):
                x = 47 + i * 3.8
                c.move_to(x, -86); c.line_to(x - 1, -66); c.stroke()
            c.set_line_width(2.5); c.move_to(46, -92); c.line_to(80, -90); c.stroke()
            c.set_source_rgba(0.24, 0.07, 0.34, 0.6); c.set_line_width(3)
            smooth(c, [(140, -420), (134, -330), (131, -262)], closed=False); c.stroke()
        ov(stoletrim, group=True, detail=1.0)

        # near arm: his hand closes over the penitent's folded hands
        R(lambda c: (smooth(c, [(212, -402), (201, -438), (165, -438), (122, -374), (98, -347), (60, -344), (25, -342), (22, -305), (46, -287),
                               (100, -290), (136, -296), (172, -340)]), c.fill()), black, sig=(4, 12), rim=1.3)
        ov(lambda c: (c.set_source_rgba(0.30, 0.31, 0.43, 0.5), c.set_line_width(5),
                      c.move_to(190, -410), c.curve_to(160, -360, 130, -330, 108, -322), c.stroke(),
                      c.move_to(112, -330), c.line_to(40, -326), c.stroke()), group=True, blur=1.5)
        R(lambda c: (smooth(c, [(28, -344), (20, -302), (36, -296), (42, -340)]), c.fill()), (0.9, 0.9, 0.92), sig=(2, 5), amb=0.8)
        R(lambda c: (smooth(c, [(26, -340), (6, -348), (-12, -342), (-22, -326), (-14, -308), (4, -300), (24, -304)]), c.fill()),
          (0.86, 0.68, 0.58), sig=(2.2, 6), rim=1.35, amb=0.66)
        ov(lambda c: (c.set_source_rgba(0.32, 0.17, 0.15, 0.55), c.set_line_width(1.8),
                      [(c.move_to(18 - i * 8, -342 + i), c.line_to(12 - i * 8, -318 + i * 2), c.stroke()) for i in range(4)]),
           group=True)
        # head
        self.head(120, -494, math.radians(-28), -1, 0.98, True)
        # cape collar over the nape
        R(lambda c: (smooth(c, [(150, -470), (190, -462), (214, -440), (200, -428), (160, -440), (140, -452)]), c.fill()),
          black, sig=(3, 8), rim=0.8)

        # snow settling on shoulders and hair
        def dust(c):
            rr = np.random.default_rng(31)
            for (x0, y0, x1, y1, n) in [(160, -462, 290, -372, 60), (-176, -368, -238, -300, 40), (-60, -452, -100, -430, 14)]:
                for i in range(n):
                    t = rr.random()
                    c.set_source_rgba(0.80, 0.84, 0.98, rr.uniform(0.5, 0.95))
                    c.arc(x0 + (x1 - x0) * t + rr.normal(0, 4), y0 + (y1 - y0) * t + rr.normal(0, 4) - 4, rr.uniform(1.5, 4), 0, 7)
                    c.fill()
        ov(dust, group=True)

        # snow heaped against knees, hem and the foot of the cross
        snowc = (0.70, 0.74, 0.92)
        for pts in ([(-270, 6), (-230, -14), (-170, -10), (-110, -16), (-50, -12), (-10, -18), (20, -4), (10, 14), (-150, 18)],
                    [(36, 6), (60, -12), (120, -8), (190, -14), (260, -8), (330, -18), (400, -30), (450, -16), (460, 10), (250, 18)],
                    [(160, -36), (200, -58), (240, -50), (262, -30), (240, -22), (190, -24)]):
            R(lambda c, pts=pts: (smooth(c, pts), c.fill()), snowc, sig=(4, 12), amb=0.78, rim=0.9, detail=0.6)

    # ---------------------------------------------------------------
    def chain(self):
        """a broken fetter left behind in the tracks"""
        def draw(c):
            rr = np.random.default_rng(4)
            x, y = 1010, 1905
            for i in range(9):
                a = rr.uniform(-0.5, 0.5) + (0.2 if i % 2 else -0.2)
                c.save(); c.translate(x, y); c.rotate(a); c.scale(1, 0.5)
                c.set_source_rgb(0.10, 0.09, 0.12); c.set_line_width(5)
                c.arc(0, 0, 12, 0, 7 if i < 8 else 4.4); c.stroke()
                c.restore()
                x -= 19 + rr.uniform(-2, 2); y += 7 + rr.uniform(-3, 3)
            c.save(); c.translate(1036, 1895); c.scale(1, 0.55)
            c.set_line_width(7); c.arc(0, 0, 22, 0.9, 5.6); c.stroke(); c.restore()

        def hl(c):
            c.translate(-2, -2.5)
            rr = np.random.default_rng(4)
            x, y = 1010, 1905
            for i in range(9):
                a = rr.uniform(-0.5, 0.5) + (0.2 if i % 2 else -0.2)
                c.save(); c.translate(x, y); c.rotate(a); c.scale(1, 0.5)
                c.set_source_rgba(1.0, 0.78, 0.5, 0.9); c.set_line_width(1.6)
                c.arc(0, 0, 12, 3.6, 5.6); c.stroke()
                c.restore()
                x -= 19 + rr.uniform(-2, 2); y += 7 + rr.uniform(-3, 3)
        self.overlay(draw, detail=0.9)
        self.overlay(hl)

    def bramble(self):
        rr = np.random.default_rng(19)
        canes = []
        for i in range(26):
            x0 = rr.uniform(-60, 620)
            y0 = 2190
            hgt = rr.uniform(180, 560) * (1 - x0 / 1300)
            lean = rr.uniform(-160, 330)
            p1 = (x0 + lean * 0.2, y0 - hgt * 0.7)
            p2 = (x0 + lean * 0.7, y0 - hgt * 1.05)
            p3 = (x0 + lean * 1.25, y0 - hgt * rr.uniform(0.45, 0.9))
            canes.append(((x0, y0), p1, p2, p3, rr.uniform(4, 9)))

        def bez(p0, p1, p2, p3, t):
            u = 1 - t
            return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])

        def draw(c, off=(0, 0), col=(0.085, 0.06, 0.085, 1), wm=1.0, thorns=True):
            r2 = np.random.default_rng(20)
            for (p0, p1, p2, p3, w) in canes:
                c.set_source_rgba(*col); c.set_line_width(w * wm)
                c.move_to(p0[0] + off[0], p0[1] + off[1])
                c.curve_to(p1[0] + off[0], p1[1] + off[1], p2[0] + off[0], p2[1] + off[1], p3[0] + off[0], p3[1] + off[1])
                c.stroke()
                if thorns:
                    for j in range(12):
                        t = r2.uniform(0.1, 0.98)
                        x, y = bez(p0, p1, p2, p3, t)
                        a = r2.uniform(0, 6.28)
                        c.set_line_width(2.2)
                        c.move_to(x, y); c.line_to(x + 13 * math.cos(a), y + 13 * math.sin(a)); c.stroke()
        self.overlay(lambda c: draw(c), detail=0.7)
        self.overlay(lambda c: draw(c, (2.5, -2.5), (0.95, 0.62, 0.42, 0.8), 0.25, False))

        def extras(c):
            r2 = np.random.default_rng(21)
            for (p0, p1, p2, p3, w) in canes:
                for j in range(3):   # snow clinging
                    t = r2.uniform(0.3, 0.95)
                    x, y = bez(p0, p1, p2, p3, t)
                    c.set_source_rgba(0.62, 0.68, 0.90, 0.95)
                    c.save(); c.translate(x, y - w * 0.8); c.scale(2.2, 0.8); c.arc(0, 0, w * 1.1, 0, 7); c.fill(); c.restore()
                if r2.random() < 0.6:  # hips: drops of red among the thorns
                    t = r2.uniform(0.6, 1.0)
                    x, y = bez(p0, p1, p2, p3, t)
                    c.set_source_rgba(0.70, 0.06, 0.05, 1); c.arc(x + 5, y + 8, 6.5, 0, 7); c.fill()
                    c.set_source_rgba(1.0, 0.5, 0.3, 0.9); c.arc(x + 7, y + 6, 2, 0, 7); c.fill()
        self.overlay(extras, detail=0.7)

    def reeds(self):
        rr = np.random.default_rng(53)

        def draw(c):
            for (cx, cy, n, hh) in [(2760, 2090, 70, 230), (2900, 1830, 40, 150), (2620, 2150, 50, 200), (3020, 1640, 22, 90),
                                    (3760, 1900, 50, 200)]:
                for i in range(n):
                    x = cx + rr.normal(0, hh * 0.35)
                    y = cy + rr.normal(0, hh * 0.08)
                    ln = hh * rr.uniform(0.4, 1.0)
                    a = -math.pi / 2 + rr.normal(0.12, 0.28)
                    x2, y2 = x + ln * math.cos(a), y + ln * math.sin(a)
                    lit = rr.random() < 0.5
                    c.set_source_rgba(*((0.98, 0.72, 0.36, 0.95) if lit else (0.30, 0.20, 0.16, 0.95)))
                    c.set_line_width(rr.uniform(1.6, 3.6))
                    c.move_to(x, y); c.curve_to(x, y - ln * 0.5, x2 - 6, y2 + ln * 0.2, x2, y2); c.stroke()
        self.overlay(draw, detail=0.6)

    def finish(self):
        k = self.k
        xx, yy = self.xx, self.yy
        d = np.sqrt((xx - SX) ** 2 + (yy - SY) ** 2)
        # light floods round the forms that stand against it
        bloom = (np.exp(-d / 70.0) * 0.55 + np.exp(-d / 260.0) * 0.22)[..., None]
        self.img = self.img + bloom * np.array([1.0, 0.86, 0.58], np.float32)
        hi = np.clip(self.img - 0.92, 0, 1)
        self.img += cv2.GaussianBlur(hi, (0, 0), 14 * k) * 0.8
        # gather the eye: let the corners sink
        v = ((xx - 2110) / 2700.0) ** 2 + ((yy - 1150) / 1500.0) ** 2
        vig = 1 - 0.46 * smoothstep(0.30, 1.25, v)
        self.img *= vig[..., None]
        lum = self.img.mean(-1, keepdims=True)
        self.img = lum + (self.img - lum) * 0.90
        self.img = np.clip(self.img, 0, 1)

    def build(self):
        self.sky()
        self.mountains()
        self.ground()
        self.stream_and_village()
        self.mid_trees()
        self.forest()
        self.shadows()
        self.footprints()
        self.chain()
        self.bare_tree()
        self.big_spruces()
        self.cross()
        self.figures()
        self.reeds()
        self.bramble()
        self.finish()
        return np.ascontiguousarray(self.img.astype(np.float32)), np.clip(self.detail, 0, 1).astype(np.float32)


if __name__ == '__main__':
    import sys
    k = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    out = sys.argv[2] if len(sys.argv) > 2 else '.'
    sc = Scene(k)
    img, det = sc.build()
    np.save(f'{out}/ref.npy', img)
    np.save(f'{out}/detail.npy', det)
    cv2.imwrite(f'{out}/ref.png', (img[:, :, ::-1] * 255).astype(np.uint8))
    cv2.imwrite(f'{out}/detail.png', (det * 255).astype(np.uint8))
