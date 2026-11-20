"""Export the parts we make as STL, with a mesh audit.

The bearings, pulley and screw end are modelled for the assembly only and are
deliberately not exported.

The two SPACERS are exported, but read the README before printing them: they
carry the M8 nut's clamping preload, which printed plastic will creep under.
The STLs are there as a dimensional reference and for a dry fit.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import MeshPart

OURS = ("Housing", "InnerSpacer", "OuterSpacer")
OUTDIR = os.path.join(_HERE, "stl")


def main() -> None:
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(_HERE, "wen_x_end.FCStd")
    if not os.path.exists(path):
        raise SystemExit("build it first: FreeCADCmd build.py")
    doc = App.openDocument(path)
    failures = []
    for name in OURS:
        mesh = MeshPart.meshFromShape(
            Shape=doc.getObject(name).Shape,
            LinearDeflection=0.02,
            AngularDeflection=0.1,
            Relative=False,
        )
        # A slicer silently patches an open or non-manifold mesh and prints
        # something subtly wrong, so the audit happens here instead.
        bad = []
        if not mesh.isSolid():
            bad.append("not solid")
        if mesh.hasNonManifolds():
            bad.append("non-manifold")
        if mesh.hasSelfIntersections():
            bad.append("self-intersecting")
        out = os.path.join(OUTDIR, name + ".stl")
        mesh.write(out)
        print(f"{name:<14} {mesh.CountFacets:6d} facets  "
              f"{' / '.join(bad) if bad else 'OK'}  -> {out}")
        if bad:
            failures.append((name, bad))
    App.closeDocument(doc.Name)
    if failures:
        raise SystemExit(f"unprintable mesh: {failures}")


main()
