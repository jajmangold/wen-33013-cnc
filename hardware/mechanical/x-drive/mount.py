"""NEMA 23 bracket + 20T motor pulley for the WEN 33013 X axis.

Coordinates:  X = along the lead screw, 0 at the OUTER face of the mill's
12 mm end plate, +X outboard.  Z = up, 0 on the screw centreline.  Y across.
"""
import math

import gt2
import params as P
import Part
from fcutil import box as _box
from fcutil import xcyl as _xcyl
from fcutil import xslot as _xslot
from FreeCAD import Placement, Rotation, Vector


def centre_distance():
    d1 = P.PITCH * P.TEETH / math.pi
    d2 = P.PITCH * P.MOTOR_TEETH / math.pi
    b = P.BELT_TEETH * P.PITCH - (math.pi / 2.0) * (d1 + d2)
    disc = b * b - 2.0 * (d1 - d2) ** 2
    if disc < 0:
        raise ValueError("belt is too short for this pulley pair")
    return (b + math.sqrt(disc)) / 4.0


C = centre_distance()
MOTOR_Z = C * math.cos(math.radians(P.MOTOR_ANGLE))
MOTOR_Y = C * math.sin(math.radians(P.MOTOR_ANGLE))

# --- axial layout, all driven by where the d10 land starts
SEAT_MID_X   = P.LAND_START_X + P.FLANGE_T + P.SEAT_W / 2.0   # belt plane centre
MPUL_X0      = SEAT_MID_X - P.SEAT_W / 2.0 - P.FLANGE_T       # motor pulley inner face
MPUL_X1      = MPUL_X0 + P.SEAT_W + 2 * P.FLANGE_T
MOTOR_FACE_X = MPUL_X1 + P.MOTOR_HUB_ALLOW                    # motor front face
MPLATE_X0    = MOTOR_FACE_X - P.MOTOR_PLATE_T
WALL_X1      = MPLATE_X0
BRACKET_TOP  = MOTOR_Z + P.MOTOR_PLATE_H / 2.0
BRACKET_BOT  = -(P.CLEARANCE_D / 2.0 + 5.0)




# --------------------------------------------------------------- 20T pulley
def make_motor_pulley():
    wire, pd, ro = gt2.tooth_profile_wire(P.MOTOR_TEETH, P.PITCH, P.PLD,
                                          P.GROOVE_R, P.TIP_R, P.GROOVE_H)
    seat = Part.Face(wire).extrude(Vector(0, 0, P.SEAT_W))
    seat.Placement = Placement(Vector(P.FLANGE_T, 0, 0), Rotation(Vector(0, 1, 0), 90))
    fl_od = 2 * ro + 2 * 1.7
    body = seat.fuse(_xcyl(fl_od, 0.0, P.FLANGE_T))
    body = body.fuse(_xcyl(fl_od, P.FLANGE_T + P.SEAT_W,
                           2 * P.FLANGE_T + P.SEAT_W))
    body = body.removeSplitter()
    hub_l = P.MOTOR_HUB_ALLOW - 1.0
    body = body.fuse(_xcyl(P.MOTOR_HUB_OD, 2 * P.FLANGE_T + P.SEAT_W,
                           2 * P.FLANGE_T + P.SEAT_W + hub_l))
    body = body.removeSplitter()
    body = body.cut(_xcyl(P.NEMA_SHAFT_D + 0.08, -1.0,
                          MPUL_X1 - MPUL_X0 + hub_l + 1.0))
    # two M4 grub screws at 90 deg, in the hub
    gx = 2 * P.FLANGE_T + P.SEAT_W + hub_l / 2.0
    for rot in (0, 90):
        a = math.radians(rot)
        d = Vector(0, math.cos(a), math.sin(a))
        body = body.cut(Part.makeCylinder(P.SETSCREW_TAP_D / 2.0, P.MOTOR_HUB_OD,
                                          Vector(gx, 0, 0), d))
    return body.removeSplitter(), pd, ro


# ----------------------------------------------------------------- bracket
def make_bracket():
    half_lo = P.BACK_W_LOW / 2.0
    half_hi = P.BACK_W_HIGH / 2.0
    wy0, wy1 = P.WALL_Y_IN, P.WALL_Y_IN + P.WALL_T
    mh = P.MOTOR_PLATE_H / 2.0
    mw = P.MOTOR_PLATE_W / 2.0

    # backplate: wide where it bolts on, narrower as it rises
    b = _box(0, P.MOUNT_T, -half_lo, half_lo, BRACKET_BOT, P.PLATE_TOP_ABOVE)
    b = b.fuse(_box(0, P.MOUNT_T, -half_hi, half_hi,
                    P.PLATE_TOP_ABOVE, BRACKET_TOP))
    # side walls -> a U channel that doubles as a belt guard
    for s in (+1, -1):
        b = b.fuse(_box(P.MOUNT_T, WALL_X1, s * wy0, s * wy1,
                        BRACKET_BOT, BRACKET_TOP))
    # motor plate
    b = b.fuse(_box(MPLATE_X0, MOTOR_FACE_X, MOTOR_Y - mw, MOTOR_Y + mw,
                    MOTOR_Z - mh, MOTOR_Z + mh))
    b = b.removeSplitter()

    # --- cuts
    # Clearance for the retainer and the pulley flange - NOT a register.
    # There is no raised boss to register on, so the bolts locate the
    # bracket and the backplate bearing flat on the plate takes the moment
    # from the motor hanging outboard.
    b = b.cut(_xcyl(P.CLEARANCE_D, -1.0, P.MOUNT_T + 1.0))
    # the two stock M5s, clearance - they thread into the table casting
    for s in (+1, -1):
        b = b.cut(_xcyl(P.BOLT_CLEAR_D, -1.0, P.MOUNT_T + 1.0,
                        s * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))
    # motor: pilot clearance, generous so the motor can slide to tension
    pilot = P.NEMA_PILOT_D + P.TENSION_SLOT + 1.0
    b = b.cut(_xcyl(pilot, MPLATE_X0 - 1.0, MOTOR_FACE_X + 1.0, MOTOR_Y, MOTOR_Z))
    # 4 motor bolts in vertical slots
    h = P.NEMA_BOLT_PITCH / 2.0
    for dy in (-h, h):
        for dz in (-h, h):
            b = b.cut(_xslot(P.NEMA_BOLT_CLEAR, MPLATE_X0 - 1.0, MOTOR_FACE_X + 1.0,
                             MOTOR_Y + dy, MOTOR_Z + dz, P.TENSION_SLOT))
    return b.removeSplitter()


# ------------------------------------------------- reference: NEMA 23 body
def make_nema23():
    f = P.NEMA_FRAME / 2.0
    body = _box(MOTOR_FACE_X, MOTOR_FACE_X + 76.0,
                MOTOR_Y - f, MOTOR_Y + f, MOTOR_Z - f, MOTOR_Z + f)
    body = body.fuse(_xcyl(P.NEMA_PILOT_D, MOTOR_FACE_X - 1.6, MOTOR_FACE_X,
                           MOTOR_Y, MOTOR_Z))
    body = body.fuse(_xcyl(P.NEMA_SHAFT_D, MOTOR_FACE_X - P.NEMA_SHAFT_L,
                           MOTOR_FACE_X, MOTOR_Y, MOTOR_Z))
    return body.removeSplitter()


# ------------------------------------------- reference: the mill's end plate
def make_end_plate():
    half = P.PLATE_W / 2.0
    p = _box(-P.PLATE_T, 0, -half, half, -P.PLATE_BOT_BELOW, P.PLATE_TOP_ABOVE)
    p = p.cut(_xcyl(P.RETAINER_D, -2.0, 0.0))     # the casting is recessed here
    p = p.cut(_xcyl(26.0, -P.PLATE_T - 1, 1.0))
    for s in (+1, -1):
        p = p.cut(_xcyl(P.BOLT_CLEAR_D, -P.PLATE_T - 1, 1,
                        s * P.BOLT_PITCH / 2.0, P.BOLT_ABOVE))
    return p.removeSplitter()
