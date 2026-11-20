"""Build the WEN 33013 X-axis belt-drive parts.

Run headless:  FreeCADCmd build.py
Writes wen_x_drive.FCStd next to this file.

Axis convention: the lead screw points along +X, X=0 at the face of the
X-axis bearing seat (where the d10 land emerges).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))

import FreeCAD as App
import gt2
import params as P
import Part
from fcutil import check, clearance
from fcutil import xtube as _tube
from FreeCAD import Placement, Rotation, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wen_x_drive.FCStd")

# ---------------------------------------------------------------- derived
BORE_D   = P.SHAFT_D + P.BORE_FIT
BORE_L   = P.SHAFT_LAND_L + P.BORE_OVERRUN
X_FLANGE_IN  = (0.0, P.FLANGE_T)
X_SEAT       = (P.FLANGE_T, P.FLANGE_T + P.SEAT_W)
X_FLANGE_OUT = (X_SEAT[1], X_SEAT[1] + P.FLANGE_T)
# No hub: the pulley is only as wide as the flanges and seat need, because
# anything wider pushes the nut past the end of the thread.
PULLEY_W     = X_FLANGE_OUT[1]






# ------------------------------------------------------------------ pulley
def make_pulley():
    wire, pd, ro = gt2.tooth_profile_wire(P.TEETH, P.PITCH, P.PLD,
                                          P.GROOVE_R, P.TIP_R, P.GROOVE_H)
    face = Part.Face(wire)
    toothed = face.extrude(Vector(0, 0, X_SEAT[1] - X_SEAT[0]))
    # profile is built in XY, swing it onto the +X axis
    toothed.Placement = Placement(Vector(X_SEAT[0], 0, 0),
                                  Rotation(Vector(0, 1, 0), 90))

    body = toothed
    body = body.fuse(_tube(P.FLANGE_OD, *X_FLANGE_IN))
    body = body.fuse(_tube(P.FLANGE_OD, *X_FLANGE_OUT))
    body = body.removeSplitter()

    # bore, nut recess
    body = body.cut(_tube(BORE_D, -1.0, BORE_L))
    body = body.cut(_tube(P.CBORE_D, BORE_L, PULLEY_W + 1.0))

    # keyway: full length of the bore, opening at the inner face
    kw = P.KEY_W + P.KEY_FIT
    key = Part.makeBox(BORE_L + 1.0, kw, P.KEY_HUB_DEPTH + 1.0,
                       Vector(-1.0, -kw / 2.0, BORE_D / 2.0 - 1.0))
    body = body.cut(key)

    body = body.removeSplitter()
    # The M8 washer's ~8.4 bore cannot pass over the Ø10 land, so the
    # counterbore floor HAS to sit on the thread - and far enough in that the
    # nut still has thread under it. That pair of constraints, not the belt,
    # is what fixes this pulley's width.
    WASHER_T, NUT_T = 1.6, 6.5
    thread0, thread1 = P.SHAFT_LAND_L, P.SHAFT_LAND_L + P.THREAD_L
    if thread0 > BORE_L:
        raise AssertionError(
            f"counterbore floor at {BORE_L:.1f} is still on the Ø{P.SHAFT_D:.0f} "
            f"land (ends {thread0:.1f}); an M8 washer will not pass over it")
    if thread1 < BORE_L + WASHER_T + NUT_T:
        raise AssertionError(
            f"washer and nut reach {BORE_L + WASHER_T + NUT_T:.1f} but the "
            f"thread ends at {thread1:.1f} - only "
            f"{thread1 - BORE_L:.1f} mm of thread under the nut")

    return check(body, "Pulley_40T", 1), pd, ro


# -------------------------------------------- reference: the screw end itself
def make_screw_end():
    s = Part.makeCylinder(P.SHAFT_D / 2.0, P.SHAFT_LAND_L,
                          Vector(0, 0, 0), Vector(1, 0, 0))
    s = s.fuse(Part.makeCylinder(P.THREAD_D / 2.0, P.THREAD_L,
                                 Vector(P.SHAFT_LAND_L, 0, 0), Vector(1, 0, 0)))
    t1 = P.KEY_H - P.KEY_PROUD                      # 2.5 sunk
    slot = Part.makeBox(P.KEY_L, P.KEY_W, t1 + 1.0,
                        Vector(1.0, -P.KEY_W / 2.0, P.SHAFT_D / 2.0 - t1))
    s = s.cut(slot)
    s = s.fuse(Part.makeBox(P.KEY_L, P.KEY_W, P.KEY_H,
                            Vector(1.0, -P.KEY_W / 2.0, P.SHAFT_D / 2.0 - t1)))
    s = s.removeSplitter()
    return check(s, "ScrewEnd_REF", 1)


def _box_mm(x0, x1, z_top, z_bot, half=120.0):
    """A slab spanning the whole part in Y and Z, thin in X."""
    return Part.makeBox(x1 - x0, 2 * half, z_top - z_bot,
                        Vector(x0, -half, z_bot))


def main():
    import mount
    doc = App.newDocument("WEN_X_Drive")
    print("building...")
    pulley, pd, ro = make_pulley()
    screw = make_screw_end()

    # the pulley and the screw live on the land, which starts at LAND_START_X
    shift = Placement(Vector(P.LAND_START_X, 0, 0), Rotation())
    pulley = pulley.copy()
    pulley.Placement = shift
    screw = screw.copy()
    screw.Placement = shift

    mpulley, mpd, mro = mount.make_motor_pulley()
    mpulley.Placement = Placement(Vector(mount.MPUL_X0, mount.MOTOR_Y, mount.MOTOR_Z),
                                  Rotation())
    bracket = check(mount.make_bracket(), "Bracket", 1)

    # A fit coupon, so nobody has to print 140 cm3 to find out. It is the
    # bracket's own first few millimetres - an intersection with a thin slab -
    # so it cannot drift from the part it is checking. Same outline, same
    # Ø35.15 register, same bolt slots.
    slab = _box_mm(0.0, P.FIT_PLATE_T, P.PLATE_TOP_ABOVE + 3.0, mount.BRACKET_BOT)
    fitplate = check(bracket.common(slab), "FitPlate", 1)
    nema    = check(mount.make_nema23(), "NEMA23_REF", 1)
    plate   = check(mount.make_end_plate(), "EndPlate_REF", 1)
    check(mpulley, "Pulley_20T", 1)

    for shp, name, label, _col in (
            (pulley,  "Pulley_40T",   "Pulley 40T GT2 15mm",   (0.95, 0.45, 0.15)),
            (mpulley, "Pulley_20T",   "Pulley 20T GT2 15mm",   (0.95, 0.45, 0.15)),
            (bracket, "Bracket",      "NEMA 23 bracket",       (0.30, 0.55, 0.85)),
            (fitplate, "FitPlate",    "Fit coupon",            (0.45, 0.70, 0.35)),
            (screw,   "ScrewEnd_REF", "REF lead screw end",    (0.75, 0.75, 0.78)),
            (nema,    "NEMA23_REF",   "REF NEMA 23",           (0.35, 0.35, 0.38)),
            (plate,   "EndPlate_REF", "REF mill X end plate",  (0.90, 0.30, 0.10))):
        o = doc.addObject("Part::Feature", name)
        o.Shape = shp
        o.Label = label

    # ---- clash audit between the real parts
    print("")
    pairs = [("Bracket", bracket, "Pulley_40T", pulley),
             ("Bracket", bracket, "Pulley_20T", mpulley),
             ("Bracket", bracket, "ScrewEnd",   screw),
             ("Bracket", bracket, "EndPlate",   plate),
             ("Pulley_40T", pulley, "EndPlate", plate),
             ("NEMA23", nema, "Pulley_40T", pulley)]
    clashes = [(an, bn) for an, a, bn, b in pairs if clearance(a, an, b, bn) > 1e-6]
    if clashes:
        raise AssertionError(f"parts interfere: {clashes}")

    # The bore must CLEAR the boss with room to spare, which is the opposite
    # of the old assertion that it fit closely. What has to be true now is
    # that positional error cannot jam it: a boss mis-placed by the full
    # clearance must still pass through.
    import Part as _P
    for off, want_clash in ((0.0, False), (P.BORE_CLEARANCE - 0.5, False),
                            (P.BORE_CLEARANCE + 1.5, True)):
        probe = _P.makeCylinder(P.BOSS_D / 2.0, P.BOSS_PROUD,
                                Vector(0, off, 0), Vector(1, 0, 0))
        hits = bracket.common(probe).Volume > 1e-6
        if hits != want_clash:
            raise AssertionError(
                f"bore wrong: a Ø{P.BOSS_D:.0f} boss offset {off:.1f} "
                f"{'clashes' if hits else 'passes'}, expected "
                f"{'clash' if want_clash else 'pass'}")
    print(f"  bore         Ø{P.BOSS_D + 2 * P.BORE_CLEARANCE:.1f} clears the "
          f"Ø{P.BOSS_D:.0f} boss by {P.BORE_CLEARANCE:.1f} all round, "
          f"over {P.MOUNT_T:.0f} of its {P.BOSS_PROUD:.0f} mm")

    print("")
    stack = BORE_L + 1.6 + 6.5          # washer + M8 nut
    avail = P.SHAFT_LAND_L + P.THREAD_L
    for line in (
        f"reduction              {P.TEETH}:{P.MOTOR_TEETH} = {P.REDUCTION:.1f}:1"
        f"  (from machine/wen33013.toml)",
        f"centre distance        {mount.C:.2f} mm on a {P.BELT_TEETH}T belt",
        f"motor axis             {mount.MOTOR_Z:.1f} up / {mount.MOTOR_Y:.1f} across",
        f"belt plane             X {mount.MPUL_X0 + P.FLANGE_T:.1f}"
        f" .. {mount.MPUL_X1 - P.FLANGE_T:.1f}",
        f"motor face / shaft tip X {mount.MOTOR_FACE_X:.1f}"
        f" / {mount.MOTOR_FACE_X - P.NEMA_SHAFT_L:.1f}",
        f"bracket envelope       X 0..{mount.MOTOR_FACE_X:.1f},"
        f" Y +-{P.MOTOR_PLATE_W / 2:.1f},"
        f" Z {mount.BRACKET_BOT:.1f}..{mount.BRACKET_TOP:.1f}",
        f"M6 length needed       {P.MOUNT_T + P.PLATE_T + 10:.0f} mm min"
        f" ({P.MOUNT_T:.0f} bracket + {P.PLATE_T:.0f} plate + ~10 thread)",
        "",
        f"40T pitch dia {pd:.3f}, tooth OD {2 * ro:.3f}, flange OD {P.FLANGE_OD:.1f}",
        f"width {PULLEY_W:.1f} = flange {P.FLANGE_T:.1f} + seat {P.SEAT_W:.1f}"
        f" + flange {P.FLANGE_T:.1f}",
        f"bore {BORE_D:.2f} x {BORE_L:.1f} deep,"
        f" keyway {P.KEY_W + P.KEY_FIT:.2f} x {P.KEY_HUB_DEPTH:.1f}",
        f"nut recess {P.CBORE_D:.1f} dia x {P.CBORE_DEPTH:.1f} deep",
        "",
        f"land {P.SHAFT_LAND_L:.2f}, bore {BORE_L:.2f}"
        f" -> clears the land by {BORE_L - P.SHAFT_LAND_L:.2f}",
        f"washer+nut ends at {stack:.2f}, shaft ends at {avail:.2f}"
        f" -> {avail - stack:.2f} spare",
        f"key {P.KEY_L:.1f} long, hub covers {min(P.KEY_L, BORE_L):.1f} of it",
    ):
        print(line)

    doc.recompute()
    doc.saveAs(OUT)

    print("\nsaved", OUT)


main()
