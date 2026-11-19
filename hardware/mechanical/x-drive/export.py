"""Export the parts we make as STL, with a mesh audit.

The 20T pulley is a bought part and is modelled for the assembly only, so it
is deliberately not exported.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import MeshPart

OURS = ("Pulley_40T", "Bracket")
GAUGE = ("FitGauge",)
OUTDIR = os.path.join(_HERE, "stl")


def main() -> None:
    os.makedirs(OUTDIR, exist_ok=True)
    jobs = [("wen_x_drive.FCStd", OURS), ("wen_x_gauge.FCStd", GAUGE)]
    failures = []
    for fname, names in jobs:
        path = os.path.join(_HERE, fname)
        if not os.path.exists(path):
            continue
        failures += _export(App.openDocument(path), names)
    if failures:
        raise SystemExit(f"unprintable mesh: {failures}")


def _export(doc, names):
    failures = []
    for name in names:
        mesh = MeshPart.meshFromShape(
            Shape=doc.getObject(name).Shape,
            LinearDeflection=0.02,
            AngularDeflection=0.1,
            Relative=False,
        )
        # A slicer will silently patch an open or non-manifold mesh and print
        # something subtly wrong, so the audit happens here instead.
        bad = []
        if not mesh.isSolid():
            bad.append("not solid")
        if mesh.hasNonManifolds():
            bad.append("non-manifold")
        if mesh.hasSelfIntersections():
            bad.append("self-intersecting")
        path = os.path.join(OUTDIR, name + ".stl")
        mesh.write(path)
        print(f"{name:<12} {mesh.CountFacets:6d} facets  {' / '.join(bad) if bad else 'OK'}")
        if bad:
            failures.append((name, bad))
    App.closeDocument(doc.Name)
    return failures


main()
