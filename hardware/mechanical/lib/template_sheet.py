"""Render a polygon outline to a 1:1 printable sheet.

Paper is the cheapest fit check there is. This draws the outline at exact
scale with a 100 mm bar to prove the print was not fitted to the page, cut
lines for the holes, and a crosshair on the datum so it can be lined up on
the work.

    python template_sheet.py outline.json sheet.png
"""

from __future__ import annotations

import json
import sys

import cv2
import numpy as np

DPI = 600
MARGIN_MM = 10.0
BAR_MM = 100.0


def mm(v: float) -> int:
    return int(round(v / 25.4 * DPI))


def render(data: dict, path: str) -> str:
    polys = data["polygons"]
    ys = [p[0] for poly in polys for p in poly]
    zs = [p[1] for poly in polys for p in poly]
    y0, y1, z0, z1 = min(ys), max(ys), min(zs), max(zs)
    w = mm(y1 - y0 + 2 * MARGIN_MM)
    h = mm(z1 - z0 + 2 * MARGIN_MM + 18)       # room for the bar and caption
    img = np.full((h, w), 255, np.uint8)

    def pt(y, z):
        # +z is up on the part, +y is down in image space
        return mm(y - y0 + MARGIN_MM), mm(z1 - z + MARGIN_MM)

    thick = max(2, DPI // 300)
    for i, poly in enumerate(polys):
        a = np.array([pt(*p) for p in poly], np.int32)
        cv2.polylines(img, [a], True, 0, thick if i == 0 else max(1, thick - 1))

    # datum crosshair on the screw axis, and the bolt line
    cy, cz = data["screw_axis"]
    x, y = pt(cy, cz)
    r = mm(6)
    cv2.line(img, (x - r, y), (x + r, y), 0, thick)
    cv2.line(img, (x, y - r), (x, y + r), 0, thick)
    bz = data["bolt_above"]
    bx0, by0 = pt(-data["bolt_pitch"] / 2, bz)
    bx1, _ = pt(data["bolt_pitch"] / 2, bz)
    for xx in (bx0, bx1):
        cv2.line(img, (xx, by0 - mm(3)), (xx, by0 + mm(3)), 0, max(1, thick - 1))

    # scale bar
    yb = mm(z1 - z0 + 2 * MARGIN_MM + 6)
    xb = mm(MARGIN_MM)
    cv2.line(img, (xb, yb), (xb + mm(BAR_MM), yb), 0, thick)
    for xx in (xb, xb + mm(BAR_MM)):
        cv2.line(img, (xx, yb - mm(2)), (xx, yb + mm(2)), 0, thick)
    cv2.putText(img, f"{BAR_MM:.0f} mm - PRINT AT 100%, NO FIT-TO-PAGE",
                (xb, yb + mm(5)),
                cv2.FONT_HERSHEY_SIMPLEX, DPI / 700.0, 0, max(1, DPI // 600))
    cv2.putText(img, f"{data['part']} 1:1  register {data['register_dia']:.2f}"
                     f"  bolts {data['bolt_pitch']:.0f} at {data['bolt_above']:.1f} up",
                (xb, yb + mm(10)), cv2.FONT_HERSHEY_SIMPLEX,
                DPI / 750.0, 0, max(1, DPI // 600))
    cv2.imwrite(path, img)
    return path


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    path = render(data, sys.argv[2])
    polys = data["polygons"]
    ys = [p[0] for poly in polys for p in poly]
    zs = [p[1] for poly in polys for p in poly]
    print(f"outline {max(ys) - min(ys):.1f} x {max(zs) - min(zs):.1f} mm at {DPI} dpi")
    print("wrote", path)


main()
