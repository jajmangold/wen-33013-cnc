"""Dimensions for the X end housing (ADR-0010).

Replaces the stock X-axis bearing seat (#36 on the Sieg list, #18 on WEN's)
with a housing that bolts to the same two M6 holes and supports the screw on
a preloaded pair of 6000-2RS instead of one single-direction thrust bearing.

Axis convention: +X along the screw, outboard.  X = 0 at the TABLE'S END
FACE - the machined face the stock plate bolts to.  Note this is NOT the
x-drive origin, which sits on the stock plate's OUTER face, 12 mm further
out.  Z = 0 on the screw axis, +Z up.

MEASURED  calipers on the machine
DERIVED   arithmetic on measured values, with the route written out
PHOTO     off a ChArUco board, self-calibrated against a known length
STANDARD  a catalogue dimension, not ours to choose
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from machinegen import load_machine  # noqa: E402
from machinegen.model import default_machine_path  # noqa: E402

_AXIS = load_machine(default_machine_path()).axis("x")
_DRIVE = _AXIS.drive

# ------------------------------------------------- from the machine model
TEETH = _DRIVE.screw_teeth
MOTOR_TEETH = _DRIVE.motor_teeth
PITCH = _DRIVE.belt_pitch_mm
BELT_W = _DRIVE.belt_width_mm
REDUCTION = _DRIVE.reduction

# ------------------------------------------------------- the screw itself
SHAFT_D = 10.00          # MEASURED  the plain keyed land
THREAD_D = 8.0           # MANUAL    #14 Washer M8 / #15 Nut M8
THREAD_L = 13.0          # MEASURED  12.99

# How much Ø10 land is outboard of the table's end face. This is the whole
# budget for the housing: bearings, spacer and pulley all live in it, and
# the washer and nut then sit on the thread beyond.
#
# DERIVED from three caliper readings, none of them ours:
#   stock plate thickness                     12.0
#   boss standing proud of the plate's face   16.0
#   free keyed land beyond the stock stack    10.0
PLATE_T = 12.0           # MEASURED
BOSS_PROUD = 16.0        # MEASURED
FREE_LAND = 10.0         # MEASURED  "the entire drivable part is 10mm"
LAND_OUTBOARD = PLATE_T + BOSS_PROUD + FREE_LAND          # 38.0

# The whole land, shoulder to thread. PHOTO: a ChArUco frame at 0.044 mm
# reprojection, self-calibrated two ways - the shaft reads Ø10.07 against a
# caliper 10.00 across, and the thread reads 13.5 against 12.99 along.
LAND_TOTAL = 54.0        # PHOTO, +-2

# Where the Ø16 shoulder sits. NEGATIVE: it is inside the casting's pocket,
# which is why it cannot be reached with calipers and why LAND_OUTBOARD is
# the number to work from. The two routes agree: 54 - 38 = 16 inside, and
# the stock pocket is that deep because it held the 8200 stack.
SHOULDER_X = -(LAND_TOTAL - LAND_OUTBOARD)                # -16.0

# ------------------------------------------------------------- bearings
BEAR_ID, BEAR_OD, BEAR_W = 10.0, 26.0, 8.0    # STANDARD  6000-2RS
THRUST_OD, THRUST_W = 26.0, 11.0              # STANDARD  8200 / 51200
# The 26 mm OD is shared, so the housing is one bore at one diameter and the
# stock thrust bearing stays a drop-in option in the same pocket.
BORE_D = BEAR_OD + 0.00                       # press/slip fit, set by print
BORE_FIT = 0.05

# -------------------------------------------- the mounting face, unchanged
# ADR-0009's interface carries over intact, and the fit coupon confirmed it
# physically on 2026-11-19.
BOLT_PITCH = 72.0        # MEASURED + STEP
BOLT_ABOVE = 15.7        # MEASURED two ways, agreeing to 0.6
BOLT_CLEAR_D = 6.5       # M6
M6_HEAD_D = 10.0         # STANDARD  ISO 4762
CB_D = 14.0              # counterbore: takes an M6 washer under the head

# --------------------------------------------------------- the axial stack
# Everything from the shoulder outboard, on the Ø10 land:
#
#   shoulder    inner spacer   | lip brg1 spacer brg2 clip web | gap pulley | nut
#   -16 ........................0 .............................. BODY_L ..... 38 thread
#
# Two hard constraints, and they pull against each other:
#   * an M8 washer's ~8.4 bore CANNOT pass over the Ø10 land, so the pulley's
#     outboard face must REACH the thread at 38;
#   * the nut must still have thread under it, so that face cannot go past
#     about 41.9 either.
# Everything in between - lip, two bearings, the spacer that sets the preload
# span, the circlip, the web, and the pulley's own width - has to fit in that
# window. The spacer is what is left over, not what we choose.
LIP_D, LIP_L = 20.0, 2.0     # inboard seat for the first outer race
CLIP_W = 1.3                 # DIN 472 internal circlip for a 26 bore
WEB = 1.5                    # housing material outboard of the circlip
GAP = 0.5                    # pulley must not rub the housing face
WASHER_T, NUT_T = 1.6, 6.5   # M8
THREAD_MARGIN = 1.0          # thread left under the nut
SPACER_MIN = 3.0             # less than this is not worth calling a spacer

# MEASURED 2026-11-20, the pulley in hand: ~25 mm over the tooth tips (so
# 40T - a 38T is 23.68 and a 42T is 26.23), 17.0 overall, 10 mm bore, 6 mm
# belt. It fits, with 0.6 mm to spare against this housing's 17.6 ceiling.
PULLEY_W = 17.0

FIXED = LIP_D * 0 + LIP_L + 2 * BEAR_W + CLIP_W + WEB + GAP   # 21.3 + spacer
THREAD_END = LAND_OUTBOARD + THREAD_L
FACE_MAX = THREAD_END - THREAD_MARGIN - NUT_T - WASHER_T     # 41.9
FACE_MIN = LAND_OUTBOARD                                      # 38.0

# The widest pulley this housing can take at all, before the spacer vanishes:
PULLEY_W_MAX = round(FACE_MAX - FIXED - SPACER_MIN, 1)

SPACER_L = round(FACE_MAX - PULLEY_W - FIXED, 1)
PULLEY_X0 = FIXED + SPACER_L
PULLEY_X1 = PULLEY_X0 + PULLEY_W

BRG1_X0 = LIP_L
BRG1_X1 = BRG1_X0 + BEAR_W
BRG2_X0 = BRG1_X1 + SPACER_L
BRG2_X1 = BRG2_X0 + BEAR_W
BORE_L = BRG2_X1
BODY_L = BORE_L + CLIP_W + WEB
INNER_SPACER_L = LIP_L - SHOULDER_X

if SPACER_L < SPACER_MIN:
    raise SystemExit(
        f"a {PULLEY_W:.1f} mm pulley leaves only {SPACER_L:.1f} mm of spacer; "
        f"this housing tops out at a {PULLEY_W_MAX:.1f} mm pulley")
if PULLEY_X1 < FACE_MIN:
    raise SystemExit(
        f"pulley face at {PULLEY_X1:.1f} is still on the Ø{SHAFT_D:.0f} land "
        f"(ends {FACE_MIN:.1f}); an M8 washer will not pass over it")

# ---------------------------------------------------------------- NEMA 23
# MEASURED 2026-11-20: the motor shafts are 8 mm. So the 10 mm bore pulleys
# fit the SCREW but not the motor - the 20T has to be bought with an 8 mm
# bore. Noted here because it is a BOM consequence, not a geometry input:
# nothing in this housing touches the motor shaft.
MOTOR_SHAFT_D = 8.0
NEMA_FRAME = 56.4
NEMA_BOLT_PITCH = 47.14
NEMA_PILOT_D = 38.1
NEMA_BOLT_CLEAR = 5.5
TOOL_ACCESS_D = 10.0
TENSION_SLOT = 10.0
MOTOR_HUB_ALLOW = 10.0
BELT_TEETH = 100          # 200 mm closed loop, in 6 mm

# Print the motor tower, or hang the motor off a steel angle bracket?
#
# FALSE is the default and the better engineering. Josh has steel NEMA 23
# angle brackets: steel does not creep under the motor's weight, and taking
# the tower off this part removes the ONLY thing on it that has to bridge -
# the motor plate's underside, 58 mm between the walls. It also drops the
# print from 165 cm3 to 93, and lets the bearing block - the part whose fit
# is actually uncertain - be printed and tried on its own.
#
# The tower code stays, because it is the fallback if the bracket does not
# put the motor where the belt needs it.
PRINTED_TOWER = False

# ------------------------------------------- the bought NEMA 23 mount plate
# RobotDigg / OpenBuilds style, T3 x 60 x 96.5. Dimensions off the drawing.
# Its five slots are the belt tensioning: 21.5 mm of vertical travel, which
# the Pololu L bracket could not give (and whose 65 mm base would have run
# 21 mm inside the table casting anyway).
PLATE_T_AL = 3.0
PLATE_W_AL, PLATE_L_AL = 60.0, 96.5
PLATE_PILOT_FROM_TOP = 29.70      # motor axis, from the plate's top edge
PLATE_SLOT_FROM_TOP = (66.95, 88.45)
PLATE_SLOT_Y = (-20.0, -10.0, 0.0, 10.0, 20.0)
PLATE_SLOT_W = 5.10               # M5

# The pulley's LARGEST diameter decides how close a mounting boss can come.
# MEASURED: teeth 24.96 (so 40T), hub 18.0. The FLANGES have not been
# measured and are the governing number - 18 is smaller than the teeth, so
# that reading was the hub. 30 is the conservative assumption; at a true
# flangeless 25 the lower pair of slots becomes usable too, and build.py
# works that out rather than being told.
PULLEY_MAX_OD = 30.0              # PROVISIONAL - flanges unmeasured
PULLEY_HUB_OD = 18.0              # MEASURED
BOSS_CLEAR = 2.0                  # boss face to the pulley
BOSS_WALL = 2.0                   # tapped hole to the boss face
M5_TAP_D = 4.2

MOTOR_ANGLE = 0.0
WALL_T = 6.0
WALL_Y_IN = 29.0
MOTOR_PLATE_T = 8.0
MOTOR_PLATE_W = 76.0
MOTOR_PLATE_H = 78.0

BODY_L_CLEAR = BODY_L     # the housing's outboard face
