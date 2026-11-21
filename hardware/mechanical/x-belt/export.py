"""Export the printed parts as STL, with a mesh audit."""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import MeshPart

OURS = ("Bracket", "Pulley_40T", "MotorPulley_40T")
OUTDIR = os.path.join(_HERE, "stl")


def main() -> None:
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(_HERE, "wen_x_belt.FCStd")
    if not os.path.exists(path):
        raise SystemExit("build it first: FreeCADCmd build.py")
    doc = App.openDocument(path)
    failures = []
    for name in OURS:
        mesh = MeshPart.meshFromShape(Shape=doc.getObject(name).Shape,
                                      LinearDeflection=0.02,
                                      AngularDeflection=0.1, Relative=False)
        bad = []
        if not mesh.isSolid():
            bad.append("not solid")
        if mesh.hasNonManifolds():
            bad.append("non-manifold")
        if mesh.hasSelfIntersections():
            bad.append("self-intersecting")
        out = os.path.join(OUTDIR, name + ".stl")
        mesh.write(out)
        print(f"{name:<18} {mesh.CountFacets:6d} facets  "
              f"{' / '.join(bad) if bad else 'OK'}")
        if bad:
            failures.append((name, bad))
    App.closeDocument(doc.Name)
    if failures:
        raise SystemExit(f"unprintable mesh: {failures}")


main()
