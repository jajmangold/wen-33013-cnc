"""Dump the fit plate's outline as polygons, for a 1:1 paper template.

Paper costs nothing and takes a minute. Hold the printed outline on the plate
and the bolt slots and register bore either line up or they do not - before
anything is printed in plastic at all.

The outline is SLICED from the FitPlate solid rather than drawn again, so it
cannot drift from the part. Writes outline.json next to this file; render and
print it with lib/template_sheet.py.

    FreeCADCmd template.py
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import params as P
from FreeCAD import Vector

OUT = os.path.join(_HERE, "outline.json")


def main() -> None:
    doc = App.openDocument(os.path.join(_HERE, "wen_x_drive.FCStd"))
    shape = doc.getObject("FitPlate").Shape
    # Slice at mid-thickness: through the slots and the bore, clear of any
    # chamfer or first-layer artefact at the faces.
    wires = shape.slice(Vector(1, 0, 0), P.FIT_PLATE_T / 2.0)
    polys = []
    for w in wires:
        pts = [(round(v.y, 3), round(v.z, 3)) for v in w.discretize(Deflection=0.05)]
        polys.append(pts)
    polys.sort(key=lambda p: -_area(p))          # outer boundary first
    data = {
        "part": "FitPlate",
        "units": "mm",
        "axes": "y horizontal, z vertical, origin on the SCREW AXIS",
        "screw_axis": [0.0, 0.0],
        "bolt_pitch": P.BOLT_PITCH,
        "bolt_above": P.BOLT_ABOVE,
        "register_dia": P.BOSS_D + 2 * P.BORE_CLEARANCE,
        "polygons": polys,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"{len(polys)} polygons, outer is {len(polys[0])} points")
    ys = [p[0] for poly in polys for p in poly]
    zs = [p[1] for poly in polys for p in poly]
    print(f"extent  y {min(ys):.1f}..{max(ys):.1f}   z {min(zs):.1f}..{max(zs):.1f} mm")
    print("wrote", OUT)
    App.closeDocument(doc.Name)


def _area(pts) -> float:
    a = 0.0
    for i in range(len(pts)):
        y0, z0 = pts[i]
        y1, z1 = pts[(i + 1) % len(pts)]
        a += y0 * z1 - y1 * z0
    return abs(a) / 2.0


main()
