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
from FreeCAD import Vector

OUT = os.path.join(_HERE, "wen_x_end.FCStd")

BODY_L = P.BODY_L                # solved in params, with the circlip and web
BODY_W = 92.0                    # reaches both M6s with 10 mm to spare
BODY_TOP = P.BOLT_ABOVE + 11.0
BODY_BOT = -(P.BEAR_OD / 2.0 + 7.0)
# Ø14 so a standard M6 washer (12.5 OD) fits UNDER the head. A Ø10 cap head
# straight on plastic is ~45 mm2 of bearing area; this joint wants about
# 500 N a bolt to hold against belt pull and cutting load, which is 11 MPa
# of sustained compression. PETG creeps under that and the clamp goes slack
# over weeks. With the washer it is 5.6 MPa. The washer is not optional.
CB_D, CB_DEPTH = P.CB_D, 12.0
CLIP_D, CLIP_W = 27.2, P.CLIP_W  # DIN 472 internal circlip for a 26 bore
WEB_CLEAR_D = 22.0               # see make_housing: an overhang number,
                                 # not a clearance one


def make_housing():
    b = box(0, BODY_L, -BODY_W / 2, BODY_W / 2, BODY_BOT, BODY_TOP)
    # one bore, one diameter - the 6000 and the stock 8200 share a 26 OD
    b = b.cut(xcyl(P.BORE_D + P.BORE_FIT, P.LIP_L, P.BORE_L + 1.0))
    b = b.cut(xcyl(P.LIP_D, -1.0, P.LIP_L))          # seat for the first race
    b = b.cut(xcyl(CLIP_D, P.BORE_L, P.BORE_L + CLIP_W))
    # The web outboard of the circlip still has to let the shaft through.
    # Without this it is solid across the bore - which the clash audit caught.
    #
    # Ø22, not Ø12. Only the shaft passes here, so Ø12 would do - but the
    # layer below this is the Ø27.2 circlip groove, so a Ø12 hole leaves a
    # 7.6 mm annulus overhanging inward all the way round, which is what the
    # slicer complains about. A DIN 472 ring for a 26 bore seats at Ø27.2 and
    # still stands proud to about Ø24, so Ø22 backs it completely and cuts
    # the overhang to 2.6 mm.
    b = b.cut(xcyl(WEB_CLEAR_D, P.BORE_L + CLIP_W, BODY_L + 1.0))
    for s in (+1, -1):
        y = s * P.BOLT_PITCH / 2.0
        b = b.cut(xcyl(P.BOLT_CLEAR_D, -1.0, BODY_L + 1.0, y, P.BOLT_ABOVE))
        b = b.cut(xcyl(CB_D, BODY_L - CB_DEPTH, BODY_L + 1.0, y, P.BOLT_ABOVE))
    b = b.removeSplitter()
    return (mount.add_tower(b, BODY_TOP) if P.PRINTED_TOWER
            else mount.add_plate_mount(b))


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

    # The bearing fit in a PRINTED Ø26 bore is a tuning exercise, and this
    # part is 167 cm3. The coupon is the housing's own first 14 mm - an
    # intersection, so it cannot drift from the part it is checking - with
    # the lip, the start of the bore and both bolt holes.
    slab = box(0.0, 14.0, -30.0, 30.0, -20.0, 20.0)
    gauge = check(housing.common(slab), "BoreGauge", 1)

    for shp, name in ((housing, "Housing"), (gauge, "BoreGauge"), (inner, "InnerSpacer"),
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
        jobs.append(("M6 mount", CB_D, BODY_L - CB_DEPTH, 70.0,
                     s * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))
    if P.PRINTED_TOWER:
        for dy in (-h, h):                   # motor screws, from INBOARD
            for dz in (-h, h):
                for sl in (-t, 0.0, t):
                    jobs.append(("M5 motor", P.TOOL_ACCESS_D, -1.0,
                                 mount.MPLATE_X0, mount.MOTOR_Y + dy,
                                 mount.MOTOR_Z + dz + sl))
    blocked = []
    for what, dia, x0, x1, y, z in jobs:
        v = housing.common(xcyl(dia, x0, x1, y, z)).Volume
        if v > 1e-6:
            blocked.append(f"{what} Y{y:+.1f} Z{z:.1f} ({v:.0f} mm3)")
    if blocked:
        raise AssertionError("screws cannot be fitted: " + ", ".join(blocked))

    # --- OVERHANG AUDIT. Printed inboard-face-down, the only thing that is
    # allowed to be in the air is the motor plate's underside, which bridges
    # between the two side walls and is not a functional face. Everything
    # else must be a lip, not a ledge. A Ø12 hole under the Ø27.2 circlip
    # groove once left a 7.6 mm annulus overhanging inward all the way round
    # - printable, but the slicer is right to object, and nothing in the
    # clash or access checks sees it.
    LAYER, BUDGET = 0.4, 300.0
    ov = housing.cut(housing.translated(Vector(LAYER, 0, 0)))
    x0 = housing.BoundBox.XMin
    islands = [i for i in ov.Solids if i.BoundBox.XMin > x0 + LAYER / 2.0]
    stray = 0.0
    print("")
    for i in sorted(islands, key=lambda i: -i.Volume):
        c = i.BoundBox
        area = i.Volume / LAYER
        plate = P.PRINTED_TOWER and abs(c.XMin - mount.MPLATE_X0) < 0.01
        if not plate:
            stray += area
        print(f"  overhang {area:8.1f} mm2 at X={c.XMin:6.2f}"
              f"  {'the motor plate bridge, expected' if plate else 'stray'}")
    if stray > BUDGET:
        raise AssertionError(
            f"{stray:.0f} mm2 of overhang that is not the motor plate bridge, "
            f"budget {BUDGET:.0f}. Printed inboard-face-down, anything in the air "
            f"that is not that bridge should be a lip, not a ledge")

    gap = mount.MPLATE_X0 - mount.BELT_X1 if P.PRINTED_TOWER else float("inf")
    if gap < 3.0:
        raise AssertionError(
            f"motor plate clears the belt by only {gap:.1f} mm and it bridges "
            f"{2*P.WALL_Y_IN:.0f}")

    # --- the bosses must clear the pulley, and the tapped holes must have
    # wall. Both are governed by the pulley's largest diameter, which is a
    # parameter precisely because it has not been measured.
    _bolts, _both = mount.bolt_positions()
    if not P.PRINTED_TOWER:
        import Part as _Pt
        # A keep-out TUBE around the pulley, over the pulley's own length.
        # Not distToShape against the pulley itself: that measures the axial
        # gap to the housing face, which is a different number and is meant
        # to be small.
        keep = _Pt.makeCylinder(P.PULLEY_MAX_OD / 2.0 + P.BOSS_CLEAR - 0.02,
                                P.PULLEY_X1 - P.PULLEY_X0,
                                Vector(P.PULLEY_X0, 0, 0), Vector(1, 0, 0))
        v = housing.common(keep).Volume
        if v > 1e-6:
            raise AssertionError(
                f"{v:.0f} mm3 of the mount intrudes within {P.BOSS_CLEAR:.1f} mm "
                f"of a Ø{P.PULLEY_MAX_OD:.0f} pulley")
        print(f"  mount clears a Ø{P.PULLEY_MAX_OD:.0f} pulley by "
              f"{P.BOSS_CLEAR:.1f}+, {len(_bolts)} bolts usable"
              f"{'' if _both else ' (upper slots only)'}")
        if mount.PLATE_X0 - P.PULLEY_X1 < 1.0:
            raise AssertionError("the plate would foul the screw pulley")

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
        f"motor mount                      "
        f"{'printed tower' if P.PRINTED_TOWER else 'bought T3 x 60 x 96.5 plate'}",
        f"belt plane                       X {mount.BELT_X0:.1f}"
        f"..{mount.BELT_X1:.1f}",
        f"centre distance                  {mount.C:.2f} on a {P.BELT_TEETH}T"
        f" belt at {P.TEETH}/{P.MOTOR_TEETH} = 1:1",
        f"plate                            X {mount.PLATE_X0:.1f}"
        f"..{mount.PLATE_X1:.1f}, top edge Z {mount.PLATE_TOP_Z:.2f},"
        f" motor face X {mount.AL_MOTOR_FACE_X:.1f}",
        f"tension travel                   Z {mount.SLOT_Z_LO:.2f}"
        f"..{mount.SLOT_Z_HI:.2f}, the plate's own slots",
        f"bolts                            {len(_bolts)} x M5 into the bosses"
        f"{'' if _both else '  (upper slots only - the pulley blocks the lower pair)'}",
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
