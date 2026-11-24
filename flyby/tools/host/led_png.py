#!/usr/bin/env python3
"""Turns 128x64 PPM frames into PNGs that look like a lit LED matrix.

Usage: led_png.py DIR   (converts every DIR/*.ppm, and writes DIR/contact_sheet.png)
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

PITCH = 8   # output pixels per LED
DOT = 6     # LED diameter


def led_image(frame: Image.Image) -> Image.Image:
    w, h = frame.size
    out = Image.new("RGB", (w * PITCH, h * PITCH), (12, 12, 14))
    draw = ImageDraw.Draw(out)
    px = frame.load()
    off = (PITCH - DOT) // 2
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            lit = r + g + b > 24
            color = (r, g, b) if lit else (26, 26, 30)
            x0, y0 = x * PITCH + off, y * PITCH + off
            draw.ellipse([x0, y0, x0 + DOT - 1, y0 + DOT - 1], fill=color)
    # Soft glow from the lit pixels.
    glow = out.filter(ImageFilter.GaussianBlur(PITCH * 0.9))
    out = Image.blend(out, glow, 0.25)
    # Seam between the two 64x64 panels.
    seam_x = (w // 2) * PITCH
    ImageDraw.Draw(out).line([(seam_x, 0), (seam_x, h * PITCH)], fill=(5, 5, 6), width=1)
    return out


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    frames = sorted(glob.glob(os.path.join(folder, "*.ppm")))
    pngs = []
    for path in frames:
        img = led_image(Image.open(path).convert("RGB"))
        png = os.path.splitext(path)[0] + ".png"
        img.save(png)
        pngs.append(img)
        os.remove(path)
        print("wrote", png)
    if not pngs:
        return
    # Contact sheet: two columns, scaled down.
    scale = 0.5
    tw, th = int(pngs[0].width * scale), int(pngs[0].height * scale)
    gap = 24
    cols = 2
    rows = (len(pngs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (32, 32, 36))
    for i, img in enumerate(pngs):
        r, c = divmod(i, cols)
        sheet.paste(img.resize((tw, th), Image.LANCZOS), (gap + c * (tw + gap), gap + r * (th + gap)))
    sheet.save(os.path.join(folder, "contact_sheet.png"))
    print("wrote", os.path.join(folder, "contact_sheet.png"))


if __name__ == "__main__":
    main()
