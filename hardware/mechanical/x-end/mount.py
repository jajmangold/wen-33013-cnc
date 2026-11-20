"""Motor tower for the X end housing.

Same job as x-drive/mount.py and the same hard-won rules - the NEMA 23's
screws go into blind holes so a corridor has to stay open to each of them,
and the M6s into the table casting likewise - but it stands on the bearing
housing instead of on the stock plate.
"""
import math

import params as P
from fcutil import box as _box
from fcutil import xcyl as _xcyl
from fcutil import xslot as _xslot
from fcutil import xwindow as _xwindow


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

# The screw pulley is 17 overall. PROVISIONAL split: flange 1, teeth 7,
# flange 1, hub 8 with the HUB OUTBOARD, so the grub screws are reachable and
# the M8 washer bears on the hub's end face - which lands on the thread.
BELT_X0 = P.PULLEY_X0 + 1.0
BELT_X1 = BELT_X0 + P.BELT_W + 1.0
MOTOR_FACE_X = BELT_X1 + 1.0 + P.MOTOR_HUB_ALLOW
MPLATE_X0 = MOTOR_FACE_X - P.MOTOR_PLATE_T
WALL_X1 = MPLATE_X0
BRACKET_TOP = MOTOR_Z + P.MOTOR_PLATE_H / 2.0
WEB_T = 8.0

# The tower must clear the M6 counterbores: head and driver run outboard
# along X at Y = +-36, Z = 15.7. Anything of ours at that Y has to start
# above it. Same rule that forced the x-drive walls up.
M6_CLEAR_TOP = P.BOLT_ABOVE + P.CB_D / 2.0 + 0.8
WALL_BOT = M6_CLEAR_TOP


def add_tower(b, body_top):
    """Fuse the back web, side walls and motor plate onto the housing."""
    half_hi = P.MOTOR_PLATE_W / 2.0
    wy0, wy1 = P.WALL_Y_IN, P.WALL_Y_IN + P.WALL_T
    mh, mw = P.MOTOR_PLATE_H / 2.0, P.MOTOR_PLATE_W / 2.0

    b = b.fuse(_box(0, WEB_T, -half_hi, half_hi, body_top, BRACKET_TOP))
    for s in (+1, -1):
        b = b.fuse(_box(WEB_T, WALL_X1, s * wy0, s * wy1, WALL_BOT, BRACKET_TOP))
    b = b.fuse(_box(MPLATE_X0, MOTOR_FACE_X, MOTOR_Y - mw, MOTOR_Y + mw,
                    MOTOR_Z - mh, MOTOR_Z + mh))
    b = b.removeSplitter()

    pilot = P.NEMA_PILOT_D + P.TENSION_SLOT + 1.0
    b = b.cut(_xcyl(pilot, MPLATE_X0 - 1.0, MOTOR_FACE_X + 1.0, MOTOR_Y, MOTOR_Z))
    h = P.NEMA_BOLT_PITCH / 2.0
    for dy in (-h, h):
        for dz in (-h, h):
            b = b.cut(_xslot(P.NEMA_BOLT_CLEAR, MPLATE_X0 - 1.0,
                             MOTOR_FACE_X + 1.0, MOTOR_Y + dy, MOTOR_Z + dz,
                             P.TENSION_SLOT))
    # The motor's screws can only enter from inboard. This window carries the
    # corridor through the back web - exactly the convex hull of the four.
    r = P.TOOL_ACCESS_D / 2.0
    b = b.cut(_xwindow(-1.0, WEB_T + 1.0,
                       MOTOR_Y - (h + r), MOTOR_Y + (h + r),
                       MOTOR_Z - (h + P.TENSION_SLOT / 2.0 + r),
                       MOTOR_Z + (h + P.TENSION_SLOT / 2.0 + r), r))
    return b.removeSplitter()


# ------------------------------------------- the bought aluminium plate
# Where the plate sits: outboard of the screw pulley, and far enough out
# that the motor's own shaft tip clears the housing.
NEMA_SHAFT_L = 21.0               # ASSUMED - measure if the motor is in hand
# Only ONE thing sets this: the plate must clear the screw pulley. An earlier
# version also made the motor's shaft tip clear the housing, which pushed the
# plate 2.5 mm further out - and was nonsense, because the motor sits 60 mm
# ABOVE the screw and its shaft passes nothing. That 2.5 mm mattered: it left
# the motor pulley's teeth only 4.5 mm of overlap with the screw pulley's,
# and the belt is 6 wide. Modelling the whole drive is what caught it.
PLATE_X0 = P.PULLEY_X1 + 1.0
PLATE_X1 = PLATE_X0 + P.PLATE_T_AL
AL_MOTOR_FACE_X = PLATE_X1

PLATE_TOP_Z = C + P.PLATE_PILOT_FROM_TOP
SLOT_Z_HI = PLATE_TOP_Z - P.PLATE_SLOT_FROM_TOP[0]      # upper end of travel
SLOT_Z_LO = PLATE_TOP_Z - P.PLATE_SLOT_FROM_TOP[1]

BOSS_Y_IN = P.PULLEY_MAX_OD / 2.0 + P.BOSS_CLEAR
BOSS_Y_OUT = 20.0 + P.M5_TAP_D / 2.0 + P.BOSS_WALL + 2.0


def bolt_positions():
    """Which of the plate's slots we can actually bolt into.

    The outer slots sit at Y = +-20. A tapped M5 there needs the boss face
    to be at most 20 - M5/2 - wall; the pulley says it must be at least
    its own radius plus clearance. Whether both ends of the slot are usable
    therefore depends on the pulley's largest diameter, which is why that is
    a parameter and not a constant.
    """
    beside_pulley_ok = BOSS_Y_IN <= 20.0 - P.M5_TAP_D / 2.0 - P.BOSS_WALL
    zs = [SLOT_Z_HI - 3.0]
    if beside_pulley_ok:
        zs.append(SLOT_Z_LO + 3.0)
    return [(sy * 20.0, z) for sy in (1, -1) for z in zs], beside_pulley_ok


def add_plate_mount(b):
    """Two bosses standing off the housing face to carry the plate."""
    bolts, both = bolt_positions()
    z_lo = (SLOT_Z_LO - 2.0) if both else (SLOT_Z_HI - 8.0)
    z_hi = SLOT_Z_HI + 3.0
    for sy in (+1, -1):
        b = b.fuse(_box(P.BODY_L_CLEAR - 2.0, PLATE_X0,
                        sy * BOSS_Y_IN, sy * BOSS_Y_OUT, z_lo, z_hi))
    b = b.removeSplitter()
    for y, z in bolts:
        b = b.cut(_xcyl(P.M5_TAP_D, PLATE_X0 - 12.0, PLATE_X0 + 1.0, y, z))
    return b.removeSplitter()


# Where the motor pulley lands, given the shaft it has to sit on.
MOTOR_SHAFT_X0 = AL_MOTOR_FACE_X - NEMA_SHAFT_L
MPUL_X0 = max(MOTOR_SHAFT_X0, P.PULLEY_X0)
MPUL_X1 = MPUL_X0 + P.PULLEY_W
MOTOR_TEETH_X0 = MPUL_X0 + 1.0
MOTOR_TEETH_X1 = MOTOR_TEETH_X0 + P.BELT_W + 1.0
