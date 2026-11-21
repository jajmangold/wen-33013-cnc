"""Build the X belt drive that bolts to the STOCK bearing-seat plate.

Run headless:  FreeCADCmd build.py

Two printed GT2 pulleys and one bracket. The stock plate, its 8200 thrust
bearing and the M8 nut all stay; the pulley takes the handwheel's place on
the keyed stub and the nut clamps it, exactly as the handwheel was retained.
"""
import itertools
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import gt2
import params as P
import Part
from fcutil import box, check, xcyl
from FreeCAD import Placement, Rotation, Vector

OUT = os.path.join(_HERE, "wen_x_belt.FCStd")

# ---------------------------------------------------------------- layout
C = (P.BELT_TEETH * P.PITCH - math.pi * (P.PITCH * P.TEETH / math.pi)) / 2.0
BELT_X0 = P.PULLEY_X0 + P.FLANGE_T
BELT_X1 = BELT_X0 + P.SEAT_W
# The plate clears the END OF THE THREAD, not just the nut. The thread runs
# 3.9 mm past the nut and it is at Y 0, Z 0 - straight through the plate.
PLATE_X0 = max(P.NUT_END_X, P.THREAD_X1) + 1.0
PLATE_X1 = PLATE_X0 + P.PLATE_T_AL
MOTOR_FACE_X = PLATE_X1
SHAFT_TIP_X = MOTOR_FACE_X - P.NEMA_SHAFT_L
# motor pulley: teeth at its INBOARD face, hub outboard, so it reaches back
MPUL_X0 = SHAFT_TIP_X
MPUL_X1 = MPUL_X0 + P.SEAT_W + P.FLANGE_T + P.MOTOR_HUB_L
TEETH_OVERLAP = min(BELT_X1, MPUL_X0 + P.SEAT_W) - max(BELT_X0, MPUL_X0)

PLATE_TOP_Z = C + P.PLATE_PILOT_FROM_TOP
SLOT_Z_HI = PLATE_TOP_Z - P.PLATE_SLOT_FROM_TOP[0]
SLOT_Z_LO = PLATE_TOP_Z - P.PLATE_SLOT_FROM_TOP[1]
BOLT_Z_HI, BOLT_Z_LO = 21.0, 5.0
BOLT_Y = 20.0
TENSION_TRAVEL = (P.PLATE_SLOT_FROM_TOP[1] - P.PLATE_SLOT_FROM_TOP[0]
                  - (BOLT_Z_HI - BOLT_Z_LO))

FLANGE_OD = P.PITCH * P.TEETH / math.pi - 2 * P.PLD + 2 * P.FLANGE_PROUD
BOSS_Y_IN = BOLT_Y - P.M5_TAP_D / 2.0 - P.BOSS_WALL
BOSS_Y_OUT = 26.0
BACK_W, BACK_TOP, BACK_BOT = 88.0, 26.7, -24.0
BORE_D = P.BOSS_D + 2 * P.BORE_CLEARANCE


def make_pulley(teeth, bore_d, keyed, length_hub=0.0):
    wire, pd, ro = gt2.tooth_profile_wire(teeth, P.PITCH, P.PLD,
                                          P.GROOVE_R, P.TIP_R, P.GROOVE_H)
    seat = Part.Face(wire).extrude(Vector(0, 0, P.SEAT_W))
    seat.Placement = Placement(Vector(P.FLANGE_T, 0, 0), Rotation(Vector(0, 1, 0), 90))
    fl = 2 * ro + 2 * P.FLANGE_PROUD
    b = seat.fuse(xcyl(fl, 0.0, P.FLANGE_T))
    b = b.fuse(xcyl(fl, P.FLANGE_T + P.SEAT_W, 2 * P.FLANGE_T + P.SEAT_W))
    if length_hub:
        b = b.fuse(xcyl(P.SHAFT_D + 8.0, 2 * P.FLANGE_T + P.SEAT_W,
                        2 * P.FLANGE_T + P.SEAT_W + length_hub))
    b = b.removeSplitter()
    total = 2 * P.FLANGE_T + P.SEAT_W + length_hub
    b = b.cut(xcyl(bore_d, -1.0, total + 1.0))
    if keyed:
        kw = P.KEY_W + P.KEY_FIT
        b = b.cut(Part.makeBox(total + 2.0, kw, P.KEY_HUB_DEPTH + 1.0,
                               Vector(-1.0, -kw / 2.0, bore_d / 2.0 - 1.0)))
    else:
        gx = 2 * P.FLANGE_T + P.SEAT_W + length_hub / 2.0
        for rot in (0, 90):
            a = math.radians(rot)
            b = b.cut(Part.makeCylinder(P.SETSCREW_TAP_D / 2.0, 20.0,
                                        Vector(gx, 0, 0),
                                        Vector(0, math.cos(a), math.sin(a))))
    return b.removeSplitter(), pd, ro


def make_bracket():
    b = box(0, P.MOUNT_T, -BACK_W / 2, BACK_W / 2, BACK_BOT, BACK_TOP)
    for sy in (+1, -1):
        b = b.fuse(box(P.MOUNT_T, PLATE_X0, sy * BOSS_Y_IN, sy * BOSS_Y_OUT,
                       BOLT_Z_LO - 4.0, BOLT_Z_HI + 4.0))
    b = b.removeSplitter()
    # Clearance over the stock Ø35 boss, which stands 16 proud. The 45°
    # cone on its outboard end is not decoration: closing the hole abruptly
    # would leave a ledge hanging in the air where the bosses resume.
    b = b.cut(xcyl(BORE_D, -1.0, P.BOSS_PROUD))
    cone = Part.makeCone(BORE_D / 2.0, BOSS_Y_IN - P.BOSS_CLEAR,
                         BORE_D / 2.0 - (BOSS_Y_IN - P.BOSS_CLEAR),
                         Vector(P.BOSS_PROUD, 0, 0), Vector(1, 0, 0))
    b = b.cut(cone)
    for sy in (+1, -1):
        b = b.cut(xcyl(P.BOLT_CLEAR_D, -1.0, P.MOUNT_T + 1.0,
                       sy * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))
        for z in (BOLT_Z_LO, BOLT_Z_HI):
            b = b.cut(xcyl(P.M5_TAP_D, PLATE_X0 - P.TAP_DEPTH, PLATE_X0 + 1.0,
                           sy * BOLT_Y, z))
    return b.removeSplitter()


def tube(od, id_, x0, x1):
    return xcyl(od, x0, x1).cut(xcyl(id_, x0 - 1, x1 + 1))


def ref_screw():
    s = xcyl(P.BOSS_D, 0.0, P.BOSS_PROUD)
    s = s.fuse(xcyl(P.SHAFT_D, P.BOSS_PROUD, P.LAND_X1))
    s = s.fuse(xcyl(P.THREAD_D, P.LAND_X1, P.THREAD_X1))
    t1 = P.KEY_H - P.KEY_PROUD
    s = s.fuse(Part.makeBox(P.FREE_LAND, P.KEY_W, P.KEY_H,
                            Vector(P.BOSS_PROUD, -P.KEY_W / 2, P.SHAFT_D / 2 - t1)))
    return s.removeSplitter()


def ref_stock_plate():
    p = box(-P.PLATE_T, 0, -58.5, 58.5, -8.2, 37.2)
    p = p.cut(xcyl(26.0, -P.PLATE_T - 1, 1))
    for sy in (+1, -1):
        p = p.cut(xcyl(10.0, -P.PLATE_T - 1, 1, sy * P.BOLT_PITCH / 2, P.BOLT_ABOVE))
    return p.removeSplitter()


def stadium(r, x0, x1):
    s = xcyl(2 * r, x0, x1, 0, 0).fuse(xcyl(2 * r, x0, x1, 0, C))
    return s.fuse(box(x0, x1, -r, r, 0, C)).removeSplitter()


def ref_belt(grow=0.0):
    R = P.PITCH * P.TEETH / math.pi / 2.0
    x0, x1 = BELT_X0 - grow, BELT_X0 + P.BELT_W + grow
    return stadium(R + 0.9 + grow, x0, x1).cut(
        stadium(R - 0.5 - grow, x0, x1)).removeSplitter()


def ref_plate():
    top = PLATE_TOP_Z
    p = box(PLATE_X0, PLATE_X1, -P.PLATE_W_AL / 2, P.PLATE_W_AL / 2,
            top - P.PLATE_L_AL, top)
    p = p.cut(xcyl(38.20, PLATE_X0 - 1, PLATE_X1 + 1, 0, C))
    h = P.NEMA_BOLT_PITCH / 2.0
    for dy in (-h, h):
        for dz in (-h, h):
            p = p.cut(xcyl(5.10, PLATE_X0 - 1, PLATE_X1 + 1, dy, C + dz))
    for y in P.PLATE_SLOT_Y:
        s = xcyl(P.PLATE_SLOT_W, PLATE_X0 - 1, PLATE_X1 + 1, y, SLOT_Z_LO)
        s = s.fuse(xcyl(P.PLATE_SLOT_W, PLATE_X0 - 1, PLATE_X1 + 1, y, SLOT_Z_HI))
        s = s.fuse(box(PLATE_X0 - 1, PLATE_X1 + 1, y - P.PLATE_SLOT_W / 2,
                       y + P.PLATE_SLOT_W / 2, SLOT_Z_LO, SLOT_Z_HI))
        p = p.cut(s.removeSplitter())
    return p.removeSplitter()


def ref_nema():
    f = P.NEMA_FRAME / 2.0
    m = box(MOTOR_FACE_X, MOTOR_FACE_X + 76.0, -f, f, C - f, C + f)
    m = m.fuse(xcyl(P.NEMA_PILOT_D, MOTOR_FACE_X - 1.6, MOTOR_FACE_X, 0, C))
    m = m.fuse(xcyl(P.MOTOR_SHAFT_D, SHAFT_TIP_X, MOTOR_FACE_X, 0, C))
    return m.removeSplitter()


def main():
    doc = App.newDocument("WEN_X_Belt")
    print("building...")
    pulley, pd, ro = make_pulley(P.TEETH, P.SHAFT_D + P.BORE_FIT, True)
    pulley = pulley.copy()
    pulley.Placement = Placement(Vector(P.PULLEY_X0, 0, 0), Rotation())
    mpul, _, _ = make_pulley(P.MOTOR_TEETH, P.MOTOR_SHAFT_D + 0.08, False,
                             P.MOTOR_HUB_L)
    mpul = mpul.copy()
    mpul.Placement = Placement(Vector(MPUL_X0, 0, C), Rotation())
    bracket = make_bracket()
    named = [("Bracket", check(bracket, "Bracket", 1)),
             ("Pulley_40T", check(pulley, "Pulley_40T", 1)),
             ("MotorPulley_40T", check(mpul, "MotorPulley_40T", 1)),
             ("ScrewEnd_REF", check(ref_screw(), "ScrewEnd_REF", 1)),
             ("StockPlate_REF", check(ref_stock_plate(), "StockPlate_REF", 1)),
             ("Belt_REF", check(ref_belt(), "Belt_REF", 1)),
             ("AlPlate_REF", check(ref_plate(), "AlPlate_REF", 1)),
             ("NEMA23_REF", check(ref_nema(), "NEMA23_REF", 1))]
    for name, shp in named:
        o = doc.addObject("Part::Feature", name)
        o.Shape = shp

    # ---- every pair, not a list I thought of
    ALLOWED = {frozenset(("Pulley_40T", "Belt_REF")),
               frozenset(("MotorPulley_40T", "Belt_REF")),
               frozenset(("Pulley_40T", "ScrewEnd_REF")),      # key in keyway
               frozenset(("MotorPulley_40T", "NEMA23_REF")),   # pulley on shaft
               frozenset(("Bracket", "StockPlate_REF"))}       # bolted face to face
    bad = [f"{a} vs {b} ({shp_a.common(shp_b).Volume:.0f} mm3)"
           for (a, shp_a), (b, shp_b) in itertools.combinations(named, 2)
           if frozenset((a, b)) not in ALLOWED
           and shp_a.common(shp_b).Volume > 1e-6]
    print(f"\n  clash audit     {len(named)} parts, "
          f"{len(named)*(len(named)-1)//2} pairs, {len(ALLOWED)} allowed")
    if bad:
        raise AssertionError("parts interfere: " + ", ".join(bad))

    # ---- can every screw be fitted?
    jobs = [("M6 mount", P.M6_HEAD_D + 1.0, P.MOUNT_T, 80.0,
             sy * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE) for sy in (+1, -1)]
    jobs += [("M5 plate", P.M5_TAP_D + 6.0, PLATE_X1, 80.0, sy * BOLT_Y, z)
             for sy in (+1, -1) for z in (BOLT_Z_LO, BOLT_Z_HI)]
    blocked = [f"{w} Y{y:+.0f} Z{z:.0f}"
               for w, d, x0, x1, y, z in jobs
               if bracket.common(xcyl(d, x0, x1, y, z)).Volume > 1e-6]
    if blocked:
        raise AssertionError("screws cannot be fitted: " + ", ".join(blocked))
    print(f"  screw access    all {len(jobs)} reachable")

    # ---- belt keep-out, and the pulleys sharing enough teeth
    v = bracket.common(ref_belt(2.0)).Volume
    if v > 1e-6:
        raise AssertionError(f"{v:.0f} mm3 of bracket within 2 mm of the belt")
    if TEETH_OVERLAP < P.BELT_W:
        raise AssertionError(
            f"pulleys share {TEETH_OVERLAP:.1f} mm of teeth, belt is {P.BELT_W:.0f}")
    print(f"  belt            2 mm clear all round, "
          f"{TEETH_OVERLAP:.1f} mm of shared teeth for {P.BELT_W:.0f}")

    # ---- overhangs, 45 degrees allowed
    T, BUDGET = 0.4, 300.0
    below = bracket.translated(Vector(T, 0, 0))
    for dy, dz in ((T, 0), (-T, 0), (0, T), (0, -T)):
        below = below.fuse(bracket.translated(Vector(T, dy, dz)))
    ov = bracket.cut(below.removeSplitter())
    x0 = bracket.BoundBox.XMin
    isl = [i for i in ov.Solids if i.BoundBox.XMin > x0 + T / 2]
    area = sum(i.Volume for i in isl) / T
    for i in sorted(isl, key=lambda i: -i.Volume)[:4]:
        print(f"  overhang        {i.Volume/T:7.1f} mm2 at X={i.BoundBox.XMin:6.2f}")
    if area > BUDGET:
        raise AssertionError(f"{area:.0f} mm2 of overhang, budget {BUDGET:.0f}")

    for line in (
        "",
        f"pulleys          {P.TEETH}T/{P.MOTOR_TEETH}T = 1:1, "
        f"{P.PULLEY_W:.0f} mm wide for a {P.BELT_W:.0f} mm belt",
        f"screw pulley     X {P.PULLEY_X0:.0f}..{P.PULLEY_X1:.0f} on the land, "
        f"keyed; washer+nut to {P.NUT_END_X:.1f} of {P.THREAD_X1:.0f}",
        f"motor pulley     X {MPUL_X0:.1f}..{MPUL_X1:.1f}, 8 mm bore, grub screws",
        f"centre distance  {C:.2f} on a {P.BELT_TEETH}T belt",
        f"plate            X {PLATE_X0:.1f}..{PLATE_X1:.1f}, motor face {MOTOR_FACE_X:.1f}",
        f"tension travel   {TENSION_TRAVEL:.1f} mm",
        f"M6 length        {P.MOUNT_T:.0f} bracket + {P.PLATE_T:.0f} plate "
        f"+ ~10 thread -> M6 x 30",
        f"bracket          {bracket.BoundBox.XLength:.1f} x "
        f"{bracket.BoundBox.YLength:.0f} x {bracket.BoundBox.ZLength:.1f}, "
        f"{bracket.Volume/1000:.1f} cm3",
        f"pulleys          {pulley.Volume/1000:.1f} + {mpul.Volume/1000:.1f} cm3",
    ):
        print(line)
    doc.recompute()
    doc.saveAs(OUT)
    print("\nsaved", OUT)


main()
