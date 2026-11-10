# Though Your Sins Be as Scarlet

`though-your-sins-be-as-scarlet_3840x2160.jpg` — 3840×2160 (16:9, Samsung Frame native).

Generated procedurally, no image model:

- `scene.py` composes the colour study (sky, land, figures, light).
- `paint.py` repaints it stroke by stroke on a toned linen ground: bristle
  brushes from broad to fine, paint running dry, impasto relief lit by a raking
  light, canvas weave showing through thin passages.

Rebuild: `pip install numpy scipy opencv-python-headless numba pycairo`, then
`python3 paint.py 1.0 <outdir>` (about a minute; `0.5` for a quick half-size proof).
