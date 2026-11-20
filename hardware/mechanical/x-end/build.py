"""Build the X end housing (ADR-0010).

Run headless:  FreeCADCmd build.py

Replaces the stock bearing seat. Supports the screw on a preloaded pair of
6000-2RS in a single Ø26 bore, bolted to the table's own two M6 holes.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import mount
import params as P
from fcutil import box, check, clearance, xcyl

OUT = os.path.join(_HERE, "wen_x_end.FCStd")

BODY_L = P.BODY_L                # solved in params, with the circlip and web
BODY_W = 92.0                    # reaches both M6s with 10 mm to spare
BODY_TOP = P.BOLT_ABOVE + 11.0
BODY_BOT = -(P.BEAR_OD / 2.0 + 7.0)
CB_D, CB_DEPTH = 11.0, 12.0      # M6 counterbore, so an M6 x 25 reaches
CLIP_D, CLIP_W = 27.2, P.CLIP_W  # DIN 472 internal circlip for a 26 bore


def make_housing():
    b = box(0, BODY_L, -BODY_W / 2, BODY_W / 2, BODY_BOT, BODY_TOP)
    # one bore, one diameter - the 6000 and the stock 8200 share a 26 OD
    b = b.cut(xcyl(P.BORE_D + P.BORE_FIT, P.LIP_L, P.BORE_L + 1.0))
    b = b.cut(xcyl(P.LIP_D, -1.0, P.LIP_L))          # seat for the first race
    b = b.cut(xcyl(CLIP_D, P.BORE_L, P.BORE_L + CLIP_W))
    # The web outboard of the circlip still has to let the shaft through.
    # Without this it is solid across the bore - which the clash audit caught.
    b = b.cut(xcyl(P.SHAFT_D + 2.0, -1.0, BODY_L + 1.0))
    for s in (+1, -1):
        y = s * P.BOLT_PITCH / 2.0
        b = b.cut(xcyl(P.BOLT_CLEAR_D, -1.0, BODY_L + 1.0, y, P.BOLT_ABOVE))
        b = b.cut(xcyl(CB_D, BODY_L - CB_DEPTH, BODY_L + 1.0, y, P.BOLT_ABOVE))
    b = mount.add_tower(b.removeSplitter(), BODY_TOP)
    return b


def ref_screw():
    s = xcyl(16.0, P.SHOULDER_X - 12.0, P.SHOULDER_X)
    s = s.fuse(xcyl(P.SHAFT_D, P.SHOULDER_X, P.LAND_OUTBOARD))
    s = s.fuse(xcyl(P.THREAD_D, P.LAND_OUTBOARD, P.LAND_OUTBOARD + P.THREAD_L))
    return s.removeSplitter()


def tube(od, id_, x0, x1):
    return xcyl(od, x0, x1).cut(xcyl(id_, x0 - 1, x1 + 1))


def main():
    doc = App.newDocument("WEN_X_End")
    print("building...\n")
    housing = check(make_housing(), "Housing", 1)
    inner = check(tube(16.0, P.SHAFT_D + 0.1, P.SHOULDER_X, P.LIP_L), "InnerSpacer", 1)
    outer = check(tube(24.0, 19.0, P.BRG1_X1, P.BRG2_X0), "OuterSpacer", 1)
    b1 = check(tube(P.BEAR_OD, P.BEAR_ID, P.BRG1_X0, P.BRG1_X1), "Bearing1_REF", 1)
    b2 = check(tube(P.BEAR_OD, P.BEAR_ID, P.BRG2_X0, P.BRG2_X1), "Bearing2_REF", 1)
    screw = check(ref_screw(), "ScrewEnd_REF", 1)
    pulley = check(tube(30.0, P.SHAFT_D + 0.1, P.PULLEY_X0, P.PULLEY_X1), "Pulley_REF", 1)

    for shp, name in ((housing, "Housing"), (inner, "InnerSpacer"),
                      (outer, "OuterSpacer"), (b1, "Bearing1_REF"),
                      (b2, "Bearing2_REF"), (screw, "ScrewEnd_REF"),
                      (pulley, "Pulley_REF")):
        o = doc.addObject("Part::Feature", name)
        o.Shape = shp

    print("")
    for an, a, bn, bb in (("Housing", housing, "Pulley", pulley),
                          ("Housing", housing, "InnerSpacer", inner),
                          ("Housing", housing, "ScrewEnd", screw),
                          ("Bearing1", b1, "Bearing2", b2)):
        if clearance(a, an, bb, bn) > 1e-6:
            raise AssertionError(f"{an} interferes with {bn}")

    # --- the axial budget. An M8 washer's 8.4 bore cannot pass over the O10
    # land, so the pulley's outboard face MUST reach the thread, and the nut
    # must still have thread under it. Both, or the nut spins without
    # clamping and nothing in the geometry shows it.
    nut_end = P.PULLEY_X1 + P.WASHER_T + P.NUT_T
    thread_end = P.LAND_OUTBOARD + P.THREAD_L
    if P.PULLEY_X1 < P.LAND_OUTBOARD:
        raise AssertionError(
            f"pulley face at {P.PULLEY_X1:.1f} is still on the O{P.SHAFT_D:.0f} "
            f"land (ends {P.LAND_OUTBOARD:.1f}); an M8 washer will not pass")
    if nut_end > thread_end:
        raise AssertionError(
            f"washer and nut reach {nut_end:.1f}, thread ends {thread_end:.1f}")
    if P.SPACER_L < P.SPACER_MIN:
        raise AssertionError(f"spacer {P.SPACER_L:.1f} too short to preload on")

    # --- every fastener must be fittable. Both families go into BLIND holes
    # - the motor's into the NEMA 23, the M6s into the table casting - so each
    # can only enter from one side and needs an open corridor from it. This is
    # the check that caught two unassemblable versions of the x-drive bracket.
    h = P.NEMA_BOLT_PITCH / 2.0
    t = P.TENSION_SLOT / 2.0
    jobs = []
    for s in (+1, -1):                       # M6, driven from OUTBOARD down
        jobs.append(("M6 mount", P.M6_HEAD_D + 1.0, BODY_L - CB_DEPTH, 70.0,
                     s * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))
    for dy in (-h, h):                       # motor screws, from INBOARD
        for dz in (-h, h):
            for sl in (-t, 0.0, t):
                jobs.append(("M5 motor", P.TOOL_ACCESS_D, -1.0, mount.MPLATE_X0,
                             mount.MOTOR_Y + dy, mount.MOTOR_Z + dz + sl))
    blocked = []
    for what, dia, x0, x1, y, z in jobs:
        v = housing.common(xcyl(dia, x0, x1, y, z)).Volume
        if v > 1e-6:
            blocked.append(f"{what} Y{y:+.1f} Z{z:.1f} ({v:.0f} mm3)")
    if blocked:
        raise AssertionError("screws cannot be fitted: " + ", ".join(blocked))

    gap = mount.MPLATE_X0 - mount.BELT_X1
    if gap < 3.0:
        raise AssertionError(
            f"motor plate clears the belt by only {gap:.1f} mm and it bridges "
            f"{2*P.WALL_Y_IN:.0f}")

    span = (P.BRG2_X0 + P.BRG2_X1) / 2 - (P.BRG1_X0 + P.BRG1_X1) / 2
    over = (P.PULLEY_X0 + P.PULLEY_X1) / 2 - (P.BRG2_X0 + P.BRG2_X1) / 2
    for line in (
        "",
        f"land outboard of the table face  {P.LAND_OUTBOARD:.1f}"
        f"   (12 plate + 16 boss + 10 free, all measured)",
        f"shoulder                         {P.SHOULDER_X:.1f}  inside the casting",
        f"bore                             O{P.BORE_D:.0f} x {P.BORE_L:.1f},"
        f" one diameter, 6000-2RS or the stock 8200",
        f"bearing centres                  {span:.1f} apart",
        f"pulley overhang                  {over:.1f}  (ratio {over/span:.2f})",
        f"washer+nut end                   {nut_end:.1f} of {thread_end:.1f}"
        f"  -> {thread_end-nut_end:.1f} spare",
        f"pulley width                     {P.PULLEY_W:.1f} MEASURED;"
        f" this housing takes up to {P.PULLEY_W_MAX:.1f}",
        f"spacer                           {P.SPACER_L:.1f}, solved - it is"
        f" what the budget leaves, not a choice",
        f"M6 length                        {BODY_L - CB_DEPTH:.0f} through"
        f" + ~10 thread -> M6 x 25",
        "",
        f"centre distance                  {mount.C:.2f} on a {P.BELT_TEETH}T"
        f" belt, motor straight above",
        f"belt plane                       X {mount.BELT_X0:.1f}"
        f"..{mount.BELT_X1:.1f}, {gap:.1f} clear under the motor plate",
        f"walls start                      Z {mount.WALL_BOT:.1f}, above the"
        f" M6 heads at {P.BOLT_ABOVE:.1f}",
        f"motor face                       X {mount.MOTOR_FACE_X:.1f}",
        f"bearing block                    {BODY_L:.1f} x {BODY_W:.0f} x"
        f" {BODY_TOP-BODY_BOT:.1f}",
        f"whole part                       {housing.BoundBox.XLength:.1f} x"
        f" {housing.BoundBox.YLength:.0f} x {housing.BoundBox.ZLength:.1f},"
        f" {housing.Volume/1000:.1f} cm3",
    ):
        print(line)

    doc.recompute()
    doc.saveAs(OUT)
    print("\nsaved", OUT)


main()
