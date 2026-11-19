"""A cheap fit check for the bracket's mounting face, and a go/no-go that
measures the boss at the same time.

The bracket is 148 cm3 and the first one did not fit. This is 4 cm3 of the
same interface: the two stock M5s at 72 apart, and the register bore on the
screw centreline. If this drops over the boss and the bolts line up, the
bracket will too.

The register is cut as a STAIRCASE of diameters rather than one bore. The
boss enters the widest step first and jams at the one that matches it, so how
far it sinks reads off the boss OD - the last dimension with no measurement
behind it.

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
from fcutil import box, check, xcyl

# Same datum as the bracket: Z = 0 on the screw axis, X = 0 at the plate face.
STEPS = (42.0, 40.0, 38.0, 36.0)   # outward from the plate face
STEP_T = 1.5
T = len(STEPS) * STEP_T
HALF_W = P.PLATE_W / 2.0
TOP = P.PLATE_TOP_ABOVE            # 22.5, the plate's top edge
BOTTOM = -P.PLATE_BOT_BELOW        # -22.5


def make_gauge():
    g = box(0, T, -HALF_W, HALF_W, BOTTOM, TOP)

    # the two stock M5s
    for side in (+1, -1):
        g = g.cut(xcyl(P.BOLT_CLEAR_D, -1, T + 1, side * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))

    # staircase register, widest against the plate
    for i, dia in enumerate(STEPS):
        g = g.cut(xcyl(dia, i * STEP_T, T + 1))

    # notch the top edge so it cannot be fitted upside down - the bolt line is
    # only 1.5 off centre and the part is otherwise nearly symmetric
    g = g.cut(box(-1, T + 1, -4.0, 4.0, TOP - 3.0, TOP + 1))
    return check(g, "FitGauge", 1)


def main() -> None:
    doc = App.newDocument("WEN_X_FitGauge")
    obj = doc.addObject("Part::Feature", "FitGauge")
    obj.Shape = make_gauge()
    obj.Label = "X drive fit gauge"
    doc.recompute()
    doc.saveAs(os.path.join(_HERE, "wen_x_gauge.FCStd"))

    print()
    vol = obj.Shape.Volume / 1000
    print(f"gauge {P.PLATE_W:.0f} x {TOP - BOTTOM:.0f} x {T:.1f}, ~{vol:.0f} cm3")
    print(f"bolts {P.BOLT_PITCH:.0f} apart, {P.BOLT_ABOVE:.1f} above the screw axis")
    print()
    print("how far it sits off the plate tells you the boss OD:")
    for i, dia in enumerate(STEPS):
        gap = T - (i + 1) * STEP_T
        verdict = "flush" if gap == 0 else f"{gap:.1f} mm proud"
        print(f"  boss just over {dia - 2:.0f} and up to {dia:.0f}  ->  sits {verdict}")
    print()
    print(f"params.py currently assumes BOSS_D = {P.BOSS_D:.0f}")


main()
