"""A flat gauge to print fast, hold against the plate, and photograph.

Reading a dimension off a photo normally fails on scale and perspective. This
puts a known ruler in the same plane as the thing being measured, so neither
matters:

* Two Ø5.5 holes at the bolt pitch. Held against the plate they should sit
  concentric inside its Ø10 holes, leaving an even 2.25 mm ring all round.
  Off-centre rings mean the bolt pattern in params.py is wrong, and which way
  it is wrong is visible.
* A scribed line where the plate's TOP EDGE should fall.
* A fan of fingers reaching into the window at known radii, 16 to 23. The boss
  hides the ones that land on it and the rest overhang onto the plate behind.
  Wherever that changes along the fan is the boss radius.
* A tick scale along the bottom edge, as a backup ruler for anything else in
  the frame.

Prints flat, no supports, ~2 mm thick.

    FreeCADCmd gauge.py      -> stl/FitGauge.stl
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import params as P
import Part
from fcutil import box, check, xcyl
from FreeCAD import Vector

T = 2.0                       # thin: this is a photo target, not a structure
TOP = P.PLATE_TOP_ABOVE + 9.5     # stand above the plate so the window closes
BOTTOM = -40.0
HALF_W = P.PLATE_W / 2.0
WINDOW_D = 50.0

FINGER_R = (16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0)
FINGER_A0, FINGER_A1 = 160.0, 20.0     # fanned across the top of the window
FINGER_W = 3.0

SCRIBE_W, SCRIBE_DEPTH = 1.0, 0.8
TICK_EVERY, TICK_SHORT, TICK_LONG = 5.0, 2.0, 4.0


def _finger(tip_r: float, deg: float):
    """A spoke from the window rim inward, stopping at tip_r."""
    half = FINGER_W / 2.0
    bar = box(0, T, -half, half, tip_r, WINDOW_D / 2.0 + 2.0)
    bar.rotate(Vector(0, 0, 0), Vector(1, 0, 0), deg - 90.0)
    return bar


def make_gauge():
    g = box(0, T, -HALF_W, HALF_W, BOTTOM, TOP)

    # the bolt pattern - the whole point of the part
    for side in (+1, -1):
        g = g.cut(xcyl(P.BOLT_CLEAR_D, -1, T + 1, side * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))

    # window, then put the fingers back
    g = g.cut(xcyl(WINDOW_D, -1, T + 1))
    step = (FINGER_A1 - FINGER_A0) / (len(FINGER_R) - 1)
    fan = []
    for i, r in enumerate(FINGER_R):
        deg = FINGER_A0 + i * step
        g = g.fuse(_finger(r, deg))
        fan.append((r, deg))

    # where the plate's top edge should land
    g = g.cut(box(T - SCRIBE_DEPTH, T + 1, -HALF_W - 1, HALF_W + 1,
                  P.PLATE_TOP_ABOVE - SCRIBE_W / 2, P.PLATE_TOP_ABOVE + SCRIBE_W / 2))

    # backup ruler along the bottom edge
    n = int(P.PLATE_W / TICK_EVERY)
    for i in range(n + 1):
        y = -HALF_W + i * TICK_EVERY
        if abs(y) > HALF_W:
            continue
        depth = TICK_LONG if i % 2 == 0 else TICK_SHORT
        g = g.cut(box(-1, T + 1, y - 0.5, y + 0.5, BOTTOM - 1, BOTTOM + depth))

    # orientation: the top-left corner is clipped, so "which way up" and
    # "which way round" are never a question when reading the photo
    c = 14.0
    tri = Part.Face(Part.makePolygon([
        Vector(-1, -HALF_W, TOP - c),
        Vector(-1, -HALF_W, TOP),
        Vector(-1, -HALF_W + c, TOP),
        Vector(-1, -HALF_W, TOP - c),
    ]))
    g = g.cut(tri.extrude(Vector(T + 2, 0, 0)))

    return check(g, "FitGauge", 1), fan


def main() -> None:
    doc = App.newDocument("WEN_X_FitGauge")
    gauge, fan = make_gauge()
    obj = doc.addObject("Part::Feature", "FitGauge")
    obj.Shape = gauge
    obj.Label = "X drive photo gauge"
    doc.recompute()
    doc.saveAs(os.path.join(_HERE, "wen_x_gauge.FCStd"))

    vol = gauge.Volume / 1000
    print()
    print(f"gauge {P.PLATE_W:.0f} x {TOP - BOTTOM:.0f} x {T:.1f} mm, {vol:.1f} cm3")
    print(f"bolt holes Ø{P.BOLT_CLEAR_D} at {P.BOLT_PITCH:.0f} pitch,"
          f" {P.BOLT_ABOVE:.1f} above the screw axis")
    print(f"scribed line at {P.PLATE_TOP_ABOVE:.1f} above the screw = the plate's top edge")
    print()
    print("finger fan, clipped corner on the LEFT, reading left to right:")
    for r, deg in fan:
        print(f"  {deg:6.1f} deg   tip at r={r:.0f}  (boss Ø{2 * r:.0f})")


main()
