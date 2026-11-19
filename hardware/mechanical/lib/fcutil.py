"""Shared FreeCAD helpers for the mechanical parts.

Everything here works in the axis convention used by the drive models: +X
along the screw, +Z up, origin on the screw centreline at the face the part
registers against.
"""

from __future__ import annotations

import Part
from FreeCAD import Vector


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
    """A box from two corners, in any order.

    Sorting the pairs is not tidiness: mirroring a feature by negating a
    coordinate silently produces a negative extent, and `Part.makeBox` then
    fails with "width of box too small" far from the line that caused it.
    """
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, Vector(x0, y0, z0))


def xcyl(d: float, x0: float, x1: float, y: float = 0.0, z: float = 0.0):
    """A cylinder of diameter `d` lying along +X from x0 to x1."""
    return Part.makeCylinder(d / 2.0, x1 - x0, Vector(x0, y, z), Vector(1, 0, 0))


def xtube(d_out: float, x0: float, x1: float, d_in: float = 0.0):
    """A cylinder along +X, optionally bored through."""
    s = xcyl(d_out, x0, x1)
    if d_in:
        s = s.cut(xcyl(d_in, x0 - 1.0, x1 + 1.0))
    return s


def xslot(d: float, x0: float, x1: float, y: float, z: float, travel: float):
    """A round-ended slot bored through X, free to move along Z."""
    s = xcyl(d, x0, x1, y, z - travel / 2.0)
    s = s.fuse(xcyl(d, x0, x1, y, z + travel / 2.0))
    s = s.fuse(box(x0, x1, y - d / 2.0, y + d / 2.0,
                   z - travel / 2.0, z + travel / 2.0))
    return s.removeSplitter()


def check(shape, name: str, expect_solids: int = 1):
    """Assert a shape is one closed valid solid, and say so.

    A boolean that severs a part does NOT raise - it returns a perfectly valid
    shape with more than one solid. Checking the count is the only thing that
    catches it, and it has to happen at every step, not at the end.
    """
    problems = []
    if len(shape.Solids) != expect_solids:
        problems.append(f"solids={len(shape.Solids)} (expected {expect_solids})")
    if not shape.isValid():
        problems.append("not valid")
    if not shape.isClosed():
        problems.append("not closed")
    if problems:
        raise AssertionError(f"{name}: {'; '.join(problems)}")
    bb = shape.BoundBox
    print(f"  OK  {name:<18} solids={expect_solids} vol={shape.Volume:9.1f} mm3  "
          f"bb={bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f}")
    return shape


def clearance(a, a_name: str, b, b_name: str, limit: float = 1e-6) -> float:
    """Report the interference volume between two shapes. Zero is the point.

    Assert CONTACT and FIT, not merely the absence of overlap - a part that is
    mirrored or rotated wrongly also fails to overlap. See AGENTS.md section 4.
    """
    v = a.common(b).Volume
    verdict = f"CLASH {v:.1f} mm3" if v > limit else "clear"
    print(f"  {a_name:<12} vs {b_name:<12}  {verdict}")
    return v
