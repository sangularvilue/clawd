"""Photographing the finished canvas: the MyPaint painting is given the surface
of a real picture - linen weave, the slight relief of the brushwork under a
raking gallery light, a thin amber varnish - and exported for the Frame.
Also assembles the process sheet from the saved stages.
"""
import sys, os
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import paint as pt

S, OUT = sys.argv[1], sys.argv[2]
src = sys.argv[3] if len(sys.argv) > 3 else '7_final'
im = cv2.imread(S + '/stage_%s.png' % src)[:, :, ::-1].astype(np.float32) / 255
H, W, _ = im.shape
rng = np.random.default_rng(3)
weave = pt.make_weave(H, W, 1.0, rng)
L = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
# brush relief: the fine streaks of the bristles, and lights laid on thicker than darks
hp = (L - cv2.GaussianBlur(L, (0, 0), 2.5)) * 3.0 + (cv2.GaussianBlur(L, (0, 0), 1.0) - cv2.GaussianBlur(L, (0, 0), 9)) * 1.2
body = 0.25 + 0.75 * cv2.GaussianBlur(L, (0, 0), 3) ** 1.5
relief = hp * body * 1.6 + weave * (0.42 - 0.22 * body)
gx = cv2.Sobel(relief, cv2.CV_32F, 1, 0, ksize=3) / 8
gy = cv2.Sobel(relief, cv2.CV_32F, 0, 1, ksize=3) / 8
s = 2.2
nx, ny, nz = -gx * s, -gy * s, np.ones_like(gx)
nl = np.sqrt(nx * nx + ny * ny + 1)
nx, ny, nz = nx / nl, ny / nl, nz / nl
Ld = np.array([-0.50, -0.62, 0.60]); Ld /= np.linalg.norm(Ld)
shade = 1.0 + 0.75 * (nx * Ld[0] + ny * Ld[1] + nz * Ld[2] - Ld[2])
Hh = Ld + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
spec = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 60 - Hh[2] ** 60
out = im * shade[..., None] + spec[..., None] * 0.08
out = out * np.array([1.0, 0.985, 0.955], np.float32) + np.array([0.010, 0.007, 0.0], np.float32)
out = np.clip(out, 0, 1)
o8 = (out[:, :, ::-1] * 255 + 0.5).astype(np.uint8)
cv2.imwrite(OUT + '/though-your-sins-be-as-scarlet_3840x2160.jpg', o8, [cv2.IMWRITE_JPEG_QUALITY, 96])
cv2.imwrite(S + '/final.png', o8)

# process sheet
names = [('1_drawing', 'drawing'), ('2_underpainting', 'umber underpainting'), ('3_blockin', 'colour block-in'),
         ('4_modelling', 'modelling'), ('5_landscape', 'landscape'), ('7_final', 'finished')]
tiles = []
mq = cv2.imread(S + '/maquette.png')
if mq is not None:
    t = cv2.resize(mq, (960, 540), interpolation=cv2.INTER_AREA)
    cv2.putText(t, 'maquette study', (20, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 40, 40), 2, cv2.LINE_AA)
    tiles.append(t)
st = cv2.imread(S + '/study.png')
if st is not None:
    t = cv2.resize(st, (960, 540), interpolation=cv2.INTER_AREA)
    cv2.putText(t, 'colour study', (20, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    tiles.append(t)
for n, lab in names:
    p = S + '/stage_%s.png' % n
    if os.path.exists(p):
        t = cv2.resize(cv2.imread(p), (960, 540), interpolation=cv2.INTER_AREA)
        cv2.putText(t, lab, (20, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(t)
while len(tiles) % 4:
    tiles.append(np.zeros((540, 960, 3), np.uint8))
rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
cv2.imwrite(OUT + '/process.jpg', np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
print('exported')
