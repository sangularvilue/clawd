# Though Your Sins Be as Scarlet

- `though-your-sins-be-as-scarlet_3840x2160.jpg` — the painting, 3840×2160 (16:9, Samsung Frame native)
- `timelapse.mp4` — the canvas filmed while it was painted, blank ground to last accent, one take
- `process.jpg` — maquette, colour study and the saved stages side by side

## How it was made

Painted in **MyPaint** (its own brush engine and stock `tanda` / `deevad` brush
packs, driven headless), following an easel workflow:

1. **Maquette** (`studio/maquette.py`) — the figure group modelled in 3D and lit
   by a low sun from behind, as a reference for anatomy and light.
2. **Colour study** (`studio/land.py`, `studio/study.py`) — landscape masses and
   atmosphere, with the maquette set into it; contour drawing and value study
   derived from it.
3. **Painting session** (`studio/paintit.py`, via `studio/mp.py`):
   toned ground → contour drawing → big blots of tone → colour blots →
   block-in with progressively smaller bristle brushes → modelling →
   mountains, cloud, forests, village, blasted tree, evergreens, tracks and
   thorns painted by hand → figures finished with small brushes → accents.
   Each pass looks at the canvas and only paints where it still disagrees
   with the study.
4. **Finish** (`studio/finish.py`) — linen weave, slight brush relief and
   varnish for the "photographed canvas" surface; export.

`scene.py` and `paint.py` in this folder are the first, fully procedural
attempt; the studio pipeline reuses their sky and canvas-weave code.

## Rebuild

```
apt-get install mypaint mypaint-brushes mypaint-data-extras python3-numpy ffmpeg
pip install numpy scipy opencv-python-headless numba pycairo
cd studio
python3 maquette.py <work> 2
python3 study.py <work>
/usr/bin/python3.12 paintit.py <work> 0 7      # ~13 min, writes stages + tl_0.mp4
python3 finish.py <work> ..
```
