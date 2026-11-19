"""Numeric audit of the built 40T pulley.

Screenshots prove nothing. Every feature that carries load is probed here:
all 40 grooves and lands against their computed radii, the wall left under
the keyway, and the fit over the measured screw end.
"""

from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import params as P
from FreeCAD import Vector

doc = App.openDocument(os.path.join(_HERE, "wen_x_drive.FCStd"))
pulley = doc.getObject("Pulley_40T").Shape
screw = doc.getObject("ScrewEnd_REF").Shape

pitch_dia = P.PITCH * P.TEETH / math.pi
tip_r = pitch_dia / 2 - P.PLD
root_r = tip_r - P.GROOVE_H
step = 360.0 / P.TEETH
bore_r = (P.SHAFT_D + P.BORE_FIT) / 2

# The assembled frame: build.py places the pulley at LAND_START_X, so a probe
# plane written against the part's own origin misses it entirely and every
# groove reads as empty.
PLANE_X = P.LAND_START_X + P.FLANGE_T + P.SEAT_W / 2.0


def solid_at(r: float, deg: float) -> bool:
    a = math.radians(deg)
    return pulley.isInside(Vector(PLANE_X, r * math.cos(a), r * math.sin(a)), 1e-6, True)


def first_material(deg: float) -> float:
    r = tip_r + 0.8
    while r > 4.0 and not solid_at(r, deg):
        r -= 0.002
    return r


print(f"tooth OD {2 * tip_r:.3f}  root {2 * root_r:.3f}  (depth {P.GROOVE_H:.3f})")

bad = []
for i in range(P.TEETH):
    groove, land = i * step, i * step + step / 2.0
    if solid_at(root_r + 0.05, groove):
        bad.append(f"groove {i}: material inside the root")
    if not solid_at(tip_r - 0.05, land):
        bad.append(f"land {i}: no material at the OD")
    if solid_at(tip_r + 0.05, land):
        bad.append(f"land {i}: material outside the OD")
if bad:
    raise SystemExit("tooth profile is wrong: " + "; ".join(bad[:4]))
print(f"{P.TEETH} grooves / {P.TEETH} lands probed: ALL OK")

for label, deg, expect in (("groove", 0.0, root_r), ("land", step / 2.0, tip_r)):
    got = first_material(deg)
    print(f"  {label:<6} first material at r={got:.3f} (expect {expect:.3f})")
    if abs(got - expect) > 0.01:
        raise SystemExit(f"{label} radius is {got:.3f}, expected {expect:.3f}")

print(f"flange OD {P.FLANGE_OD:.1f}, proud of the teeth by {(P.FLANGE_OD - 2 * tip_r) / 2:.2f} mm")
print(f"belt seat {P.SEAT_W:.1f} for a {P.BELT_W:.1f} belt -> {P.SEAT_W - P.BELT_W:.1f} slack")
print(f"root to bore, thinnest wall:  {root_r - bore_r:.3f} mm")
print(f"root to the keyway roof:      {root_r - bore_r - P.KEY_HUB_DEPTH:.3f} mm")

clash = pulley.common(screw).Volume
if clash > 1e-6:
    raise SystemExit(f"the pulley bore fouls the screw end: {clash:.4f} mm3")
print("pulley bore vs the measured screw end: clear")

App.closeDocument(doc.Name)
