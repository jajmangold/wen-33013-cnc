"""Motor tower for the X end housing.

Same job as x-drive/mount.py and the same hard-won rules - the NEMA 23's
screws go into blind holes so a corridor has to stay open to each of them,
and the M6s into the table casting likewise - but it stands on the bearing
housing instead of on the stock plate.
"""
import math

import params as P
import Part
from fcutil import box as _box
from fcutil import xcyl as _xcyl
from fcutil import xslot as _xslot
from fcutil import xwindow as _xwindow
from FreeCAD import Vector


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

# The screw pulley's TEETH, which is what the belt plane is. Hub inboard,
# so: hub 8, flange 1, teeth 7, flange 1 outboard.
if P.PULLEY_HUB_INBOARD:
    BELT_X0 = P.PULLEY_X0 + P.PULLEY_HUB_L + P.PULLEY_FLANGE_T
else:
    BELT_X0 = P.PULLEY_X0 + P.PULLEY_FLANGE_T
BELT_X1 = BELT_X0 + P.PULLEY_TEETH_W
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
# The plate has to clear the M8 NUT, not just the pulley. The nut is what
# clamps the bearing stack, so it is always the outermost thing on the
# screw - and at Y=0, Z=0 it runs straight through where the plate wants to
# be. Pairing ScrewEnd with AlPlate is what the hand-written clash list
# never did; the exhaustive audit found it immediately.
NUT_END_X = P.PULLEY_X1 + P.WASHER_T + P.NUT_T
PLATE_X0 = max(P.PULLEY_X1, NUT_END_X) + 1.0
PLATE_X1 = PLATE_X0 + P.PLATE_T_AL
AL_MOTOR_FACE_X = PLATE_X1

PLATE_TOP_Z = C + P.PLATE_PILOT_FROM_TOP
SLOT_Z_HI = PLATE_TOP_Z - P.PLATE_SLOT_FROM_TOP[0]      # upper end of travel
SLOT_Z_LO = PLATE_TOP_Z - P.PLATE_SLOT_FROM_TOP[1]

# Where the motor pulley lands, given the shaft it has to sit on.
MOTOR_SHAFT_X0 = AL_MOTOR_FACE_X - NEMA_SHAFT_L
# The motor pulley goes on the other way round - hub OUTBOARD - so its teeth
# sit at its inboard end and can reach back to meet the screw's. Where it
# sits on the shaft is a free adjustment: slide it until the belt lines up.
MPUL_X0 = max(BELT_X0 - P.PULLEY_FLANGE_T, MOTOR_SHAFT_X0)
MPUL_X1 = MPUL_X0 + P.PULLEY_W
MOTOR_TEETH_X0 = MPUL_X0 + P.PULLEY_FLANGE_T
MOTOR_TEETH_X1 = MOTOR_TEETH_X0 + P.PULLEY_TEETH_W
TEETH_OVERLAP = min(BELT_X1, MOTOR_TEETH_X1) - max(BELT_X0, MOTOR_TEETH_X0)


BOSS_Y_IN = P.PULLEY_MAX_OD / 2.0 + P.BOSS_CLEAR
BOSS_Y_OUT = 27.0
PAD_X0 = P.PULLEY_X1 + 0.5        # outboard of the pulley, so the pad is free
TAP_DEPTH = 8.0

# Bolt heights. The upper row has to clear the pulley AND leave wall round
# the tapped hole; the lower row only has to stay inside the slot.
BOLT_Z_HI = (P.PULLEY_MAX_OD / 2.0 + P.BOSS_CLEAR + P.BOSS_WALL
             + P.M5_TAP_D / 2.0)
BOLT_Z_LO = SLOT_Z_LO + 3.75
# Travel left for tensioning: the slot's length less how far apart the rows
# are. Two bolts at different heights lock the plate unless both stay inside
# their own slots, so the spread is paid for out of the adjustment.
SLOT_TRAVEL = P.PLATE_SLOT_FROM_TOP[1] - P.PLATE_SLOT_FROM_TOP[0]
TENSION_TRAVEL = SLOT_TRAVEL - (BOLT_Z_HI - BOLT_Z_LO)


def bolt_positions():
    """Five: three across the top, two at the bottom of the outer slots.

    The centre slot is usable because the belt's two runs are at Y = +-12.73
    and there is nothing between them at this height - the pulley tops out
    below. The +-10 slots are NOT usable: a tapped M5 there reaches Y 12.1,
    which is 0.6 from the belt.
    """
    return ([(y, BOLT_Z_HI) for y in (-20.0, 0.0, 20.0)]
            + [(y, BOLT_Z_LO) for y in (-20.0, 20.0)])


def add_plate_mount(b):
    """Bosses standing off the housing face to carry the plate.

    The outer ones are a narrow web where they pass the pulley, flaring to a
    full pad outboard of it - so the tapped holes sit in material that never
    had to squeeze past a flange, and the lower row works whatever the
    pulley's flange diameter turns out to be.
    """
    z_lo, z_hi = SLOT_Z_LO - 2.0, BOLT_Z_HI + 3.0
    for sy in (+1, -1):
        b = b.fuse(_box(P.BODY_L_CLEAR - 2.0, PAD_X0,
                        sy * BOSS_Y_IN, sy * BOSS_Y_OUT, z_lo, z_hi))
        # The pad flares inward past the pulley. As a step it was a 4 mm
        # ledge hanging in the air, which the overhang audit rejected; at
        # 45 degrees it carries itself.
        flare = BOSS_Y_IN - 13.0
        pts = [(PAD_X0, BOSS_Y_IN), (PAD_X0 + flare, 13.0),
               (PLATE_X0, 13.0), (PLATE_X0, BOSS_Y_OUT),
               (PAD_X0, BOSS_Y_OUT), (PAD_X0, BOSS_Y_IN)]
        wire = Part.makePolygon([Vector(x, sy * y, z_lo) for x, y in pts])
        b = b.fuse(Part.Face(wire).extrude(Vector(0, 0, z_hi - z_lo)))
    # the centre boss lives between the belt's two runs
    # Its underside is the closest thing to the pulley anywhere on the part:
    # at Y = 0 the distance from the screw axis IS the height, so the boss
    # has to start at the pulley's radius plus clearance, not at whatever
    # the bolt's wall happens to need.
    cy = P.M5_TAP_D / 2.0 + P.BOSS_WALL + 1.0
    b = b.fuse(_box(P.BODY_L_CLEAR - 2.0, PLATE_X0, -cy, cy,
                    BOSS_Y_IN, z_hi))
    b = b.removeSplitter()
    for y, z in bolt_positions():
        b = b.cut(_xcyl(P.M5_TAP_D, PLATE_X0 - TAP_DEPTH, PLATE_X0 + 1.0, y, z))
    return b.removeSplitter()
