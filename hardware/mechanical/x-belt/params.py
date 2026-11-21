"""Dimensions for the X belt drive on the STOCK bearing-seat plate.

The stock plate and its bearings go back on; this bolts to the same two M6
holes and carries a bought NEMA 23 plate. No bore, no bearings, no spacers,
no circlip - it is a bracket and two printed pulleys, and it prints fast.

Supersedes hardware/mechanical/x-end for now (ADR-0010's housing is parked,
not abandoned: it is still the right answer to the axial play).

Axis: +X along the screw, outboard, X = 0 at the stock plate's OUTER face.
Z = 0 on the screw axis, +Z up.

MEASURED  calipers on the machine
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
if _DRIVE.kind != "belt":
    raise SystemExit("axis x is not a belt drive in machine/wen33013.toml")

TEETH = _DRIVE.screw_teeth
MOTOR_TEETH = _DRIVE.motor_teeth
PITCH = _DRIVE.belt_pitch_mm
BELT_W = _DRIVE.belt_width_mm
BELT_TEETH = 100                  # 200 mm closed loop

# ------------------------------------------------- the stock screw stub
# From the plate's outer face. The boss stands 16 proud and the pulley seats
# on its face, so the usable shaft starts there.
BOSS_PROUD = 16.0                 # MEASURED
FREE_LAND = 10.0                  # MEASURED  "the entire drivable part is 10mm"
THREAD_L = 13.0                   # MEASURED
LAND_X0 = BOSS_PROUD
LAND_X1 = LAND_X0 + FREE_LAND     # 26
THREAD_X1 = LAND_X1 + THREAD_L    # 39
SHAFT_D = 10.00
THREAD_D = 8.0
KEY_W, KEY_H, KEY_L = 4.0, 4.0, 16.0
KEY_PROUD = 1.5
KEY_HUB_DEPTH = 1.80              # DIN 6885 t2 for a 4x4 key
KEY_FIT = 0.05
WASHER_T, NUT_T = 1.6, 6.5        # M8

# ----------------------------------------------------- GT2 tooth form
PLD, GROOVE_R, TIP_R, GROOVE_H = 0.254, 0.555, 0.15, 0.76

# --------------------------------------------------------- the pulleys
# Both printed. The screw one is keyed and clamped by the stock M8 nut; the
# motor one has an 8 mm bore and grub screws, because the 10 mm bore pulleys
# in the drawer will not fit an 8 mm shaft.
#
# The SEAT is 8 for a 6 mm belt - 2 mm of lateral slack. That is not padding:
# the two pulleys cannot be perfectly in plane, because the motor's shaft tip
# is fixed once the plate has cleared the nut, and the slack is what absorbs
# the 7.4 mm of overlap being less than either seat.
# 11, not 8. The binding constraint is not the nut - it is the END OF THE
# THREAD at X 39, which sticks 3.9 mm past the nut and which the motor plate
# must also clear. That fixes the plate at X 40 and the motor's shaft tip at
# 22, so the overlap is (17.5 + seat) - 22 = seat - 4.5 and a 6 mm belt needs
# seat >= 10.5. The slack is not padding; it is what the layout costs.
SEAT_W = BELT_W + 5.0             # 11.0
FLANGE_T = 1.5
FLANGE_PROUD = 1.7                # flange stands this proud of the tooth OD
PULLEY_W = 2 * FLANGE_T + SEAT_W  # 11.0 - against 19 for the old 15 mm belt
BORE_FIT = 0.02
MOTOR_SHAFT_D = 8.0               # MEASURED
MOTOR_HUB_L = 6.0
SETSCREW_TAP_D = 3.3              # M4

# --------------------------------------------- the stock plate we bolt to
PLATE_T = 12.0                    # MEASURED
BOSS_D = 35.0                     # MEASURED
BOLT_PITCH = 72.0                 # MEASURED
BOLT_ABOVE = 15.7                 # MEASURED two ways
BOLT_CLEAR_D = 6.5                # M6
M6_HEAD_D = 10.0                  # STANDARD ISO 4762
BORE_CLEARANCE = 3.5              # radial, so a Ø42 bore over the Ø35 boss

# ------------------------------------------------------------- bracket
MOUNT_T = 8.0
BOSS_CLEAR = 2.0
BOSS_WALL = 2.0
M5_TAP_D = 4.2
TAP_DEPTH = 8.0

# ------------------------------------------- the bought NEMA 23 plate
PLATE_T_AL = 3.0
PLATE_W_AL, PLATE_L_AL = 60.0, 96.5
PLATE_PILOT_FROM_TOP = 29.70
PLATE_SLOT_FROM_TOP = (66.95, 88.45)
PLATE_SLOT_Y = (-20.0, -10.0, 0.0, 10.0, 20.0)
PLATE_SLOT_W = 5.10
NEMA_FRAME, NEMA_BOLT_PITCH, NEMA_PILOT_D = 56.4, 47.14, 38.1
NEMA_SHAFT_L = 21.0               # ASSUMED

# --------------------------------------------------------- derived chain
PULLEY_X0 = LAND_X0
PULLEY_X1 = PULLEY_X0 + PULLEY_W
NUT_END_X = PULLEY_X1 + WASHER_T + NUT_T
if NUT_END_X > THREAD_X1:
    raise SystemExit(
        f"washer and nut reach {NUT_END_X:.1f} but the thread ends at "
        f"{THREAD_X1:.1f} - the nut would run off")
