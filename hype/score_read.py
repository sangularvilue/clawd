"""Read noteheads off clean engraved piano-score page images (a small, purpose-built OMR).

    python3 score_read.py <out.json> page1.png page2.png ... [--flats-from-bar N --flats B,E,A]

For each grand-staff system it finds the staff lines and barlines, removes the
staff lines, finds filled and hollow noteheads, and reads each one's pitch from
its vertical staff position (treble/bass clef). Output: a list of bars, each with
its notes as {staff, midi, x (0..1 position across the bar), head}.

Assumptions that hold for the score this was written for: treble over bass,
no accidentals except an optional key signature from a given bar on.
"""
import argparse
import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

DIATONIC = [0, 2, 4, 5, 7, 9, 11]  # C D E F G A B
LETTERS = 'CDEFGAB'


def staff_lines(dark):
    rows = np.where(dark.mean(1) > 0.7)[0]  # full-width staff lines, not ledger-line rows
    lines = []
    for r in rows:
        if lines and r - lines[-1][-1] <= 2:
            lines[-1].append(r)
        else:
            lines.append([r])
    ys = [float(np.mean(l)) for l in lines]
    staves, i = [], 0
    while i + 4 < len(ys):
        g = ys[i:i + 5]
        d = np.diff(g)
        if d.max() < 16 and d.max() - d.min() < 3:
            staves.append(g)
            i += 5
        else:
            i += 1
    return staves


def systems(staves, dark=None):
    """Pair staves into (treble, bass) by the gap between them. A treble staff with no
    partner (its bass lines buried under beams) gets one found by line spacing."""
    out, i = [], 0
    while i < len(staves):
        a = staves[i]
        sp = np.mean(np.diff(a))
        b = staves[i + 1] if i + 1 < len(staves) else None
        if b is not None and b[0] - a[-1] < 12 * sp:
            out.append((a, b))
            i += 2
            continue
        if dark is not None:
            prof = dark.mean(1)
            best, by = -1, None
            for y0 in range(int(a[-1] + 4 * sp), int(a[-1] + 11 * sp)):
                ys = [y0 + k * sp for k in range(5)]
                v = sum(prof[int(round(y))] for y in ys if int(round(y)) < len(prof))
                if v > best:
                    best, by = v, ys
            out.append((a, by))
        i += 1
    return out


def barlines(dark, top, bottom):
    col = dark[int(top):int(bottom) + 1].mean(0)
    xs = np.where(col > 0.97)[0]
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= 3:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [int(np.mean(g)) for g in groups]


def remove_lines(dark, lines):
    out = dark.copy()
    for y in lines:
        for yy in range(int(round(y)) - 1, int(round(y)) + 2):
            if 0 < yy < out.shape[0] - 1:
                above = dark[yy - 2] if yy - 2 >= 0 else np.zeros_like(dark[yy])
                below = dark[yy + 2] if yy + 2 < dark.shape[0] else np.zeros_like(dark[yy])
                keep = above & below  # ink crossing the line (a notehead or stem) survives
                out[yy] = dark[yy] & keep
    return out


def heads(dark, sp, orig=None, lines_rel=None):
    """Filled noteheads via an opening that removes stems, beams and slurs. Hollow ones
    (half/whole notes) from small enclosed holes in the image *with* staff lines, where a
    line through a head splits its hole in two; those halves are merged back."""
    se = np.ones((max(3, int(sp * 0.62)), max(3, int(sp * 0.75))), bool)
    filled = ndimage.binary_opening(dark, structure=se)
    found = []
    lab, n = ndimage.label(filled)
    for sl in ndimage.find_objects(lab):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if not (0.7 * sp <= w <= 2.0 * sp and 0.55 * sp <= h):
            continue
        cx = (sl[1].start + sl[1].stop) / 2
        k = max(1, int(round(h / (sp * 0.95))))  # stacked seconds/chords
        for j in range(k):
            found.append((cx, sl[0].start + (j + 0.5) * h / k, 'filled'))
    src = orig if orig is not None else dark
    holes = ndimage.binary_fill_holes(src) & ~src
    lab, n = ndimage.label(holes)
    cand = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if not (0.3 * sp <= w <= 1.0 * sp and 0.12 * sp <= h <= 0.7 * sp):
            continue
        cand.append([sl[1].start, sl[1].stop, sl[0].start, sl[0].stop])
    merged = []
    for c in sorted(cand, key=lambda c: (c[0], c[2])):
        for m in merged:
            if abs((c[0] + c[1]) / 2 - (m[0] + m[1]) / 2) < 0.4 * sp and c[2] - m[3] <= 0.35 * sp:
                m[0], m[1], m[2], m[3] = min(m[0], c[0]), max(m[1], c[1]), min(m[2], c[2]), max(m[3], c[3])
                break
        else:
            merged.append(list(c))
    for x0, x1, y0, y1 in merged:
        if (y1 - y0) > 0.95 * sp:
            continue
        pad = max(2, int(0.25 * sp))
        ring = src[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
        if ring.mean() < 0.3:  # a real notehead rings its hole with ink
            continue
        cy = (y0 + y1) / 2
        if lines_rel is not None:  # snap to the staff: on a (ledger) line if one crosses the hole, else a space
            top, bot = lines_rel[0], lines_rel[-1]
            grid = [top + k * sp for k in range(-6, 11)]
            on = [g for g in grid if y0 + 0.5 <= g <= y1 - 0.5]  # a line through the hole, not just touching it
            if on:
                cy = min(on, key=lambda g: abs(g - cy))
            else:
                spaces = [g + sp / 2 for g in grid]
                cy = min(spaces, key=lambda g: abs(g - cy))
        found.append(((x0 + x1) / 2, cy, 'hollow'))
    return found


def pitch(y, lines, clef, flats=()):
    sp = np.mean(np.diff(lines))
    steps = int(round((lines[-1] - y) / (sp / 2)))  # 0 = bottom line
    base = (2, 4) if clef == 'treble' else (4, 2)  # bottom line: E4 (treble) / G2 (bass) as (letter idx, octave)
    idx = base[0] + steps
    octave = base[1] + idx // 7
    letter = idx % 7
    midi = 12 * (octave + 1) + DIATONIC[letter]
    if LETTERS[letter] in flats:
        midi -= 1
    return midi, LETTERS[letter] + str(octave)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('pages', nargs='+')
    ap.add_argument('--flats-from-bar', type=int, default=0)
    ap.add_argument('--flats', default='')
    ap.add_argument('--time-sig-bars', default='1', help='bars that open with a time signature, e.g. 1,11,13')
    a = ap.parse_args()
    flat_letters = set(a.flats.split(',')) if a.flats else set()
    a.time_sig_bars = {int(v) for v in a.time_sig_bars.split(',') if v}
    bars = []
    for pi, path in enumerate(a.pages):
        im = np.asarray(Image.open(path).convert('L'))
        dark = im < 140
        for si, (tre, bas) in enumerate(systems(staff_lines(dark), dark)):
            sp = float(np.mean(np.diff(tre)))
            bl = [x for x in barlines(dark, tre[0], bas[-1])]
            clean = remove_lines(dark, tre + bas)
            # skip clef/key/time area: noteheads only count right of the first barline + 3 sp
            first = True
            for x0, x1 in zip(bl[:-1], bl[1:]):
                if x1 - x0 < 3 * sp:
                    continue
                bar_no = len(bars) + 1
                # glyph zones that aren't notes: clef (+ key signature) at a system start,
                # time-signature digits, the courtesy key signature before a key change
                skip_lo = x0 + (4.2 * sp if first else 0)
                if first and a.flats_from_bar and bar_no >= a.flats_from_bar:
                    skip_lo += len(flat_letters) * 0.95 * sp
                if bar_no in a.time_sig_bars:
                    skip_lo += 2.3 * sp
                skip_hi = x1 - (3.4 * sp if a.flats_from_bar and bar_no == a.flats_from_bar - 1 else 0)
                first = False
                notes = []
                for staff, lines, clef in (('rh', tre, 'treble'), ('lh', bas, 'bass')):
                    y0 = int(lines[0] - 6 * sp)
                    y1 = int(lines[-1] + 6 * sp)
                    if clef == 'treble':
                        y1 = int(min(y1, (tre[-1] + bas[0]) / 2))
                    else:
                        y0 = int(max(y0, (tre[-1] + bas[0]) / 2))
                    sub = clean[max(0, y0):y1, x0 + 2:x1 - 1]
                    rel = [ly - max(0, y0) for ly in lines]
                    for cx, cy, kind in heads(sub, sp, dark[max(0, y0):y1, x0 + 2:x1 - 1], rel):
                        gx, gy = cx + x0 + 2, cy + max(0, y0)
                        if not (skip_lo <= gx <= skip_hi):
                            continue
                        fl = flat_letters if a.flats_from_bar and bar_no >= a.flats_from_bar else ()
                        m, name = pitch(gy, lines, clef, fl)
                        notes.append(dict(staff=staff, midi=m, name=name, x=(gx - x0) / (x1 - x0),
                                          px=float(gx), py=float(gy), head=kind))
                bars.append(dict(bar=len(bars) + 1, page=pi + 1, x0=int(x0), x1=int(x1), sp=sp, notes=notes))
    json.dump(bars, open(a.out, 'w'), indent=0)
    print('%d bars, %d noteheads' % (len(bars), sum(len(b['notes']) for b in bars)))


if __name__ == '__main__':
    main()
