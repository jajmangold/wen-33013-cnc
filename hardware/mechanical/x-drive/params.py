"""Dimensions for the X-axis belt drive.

Two kinds of number live here and they are NOT interchangeable:

* Machine numbers - tooth counts, belt pitch, belt width - are read from
  `machine/wen33013.toml`. They decide `steps_per_mm`, so per AGENTS.md
  section 2 they may not be written down a second time here.
* Shop numbers - what the screw end actually measures, what the GT2 tooth
  form is, how thick we want a web - are local. Each is tagged with where it
  came from.

MEASURED  calipers on the machine, 2026-11-19
MANUAL    WEN 33013 parts list / specifications
STEP      the third-party `WEN 33013.STEP` conversion model
ASSUMED   a placeholder. Confirm before cutting metal.
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
    raise SystemExit("axis x is not declared as a belt drive in machine/wen33013.toml")

# ------------------------------------------------- from the machine model
TEETH = _DRIVE.screw_teeth            # 40T on the screw
MOTOR_TEETH = _DRIVE.motor_teeth      # 20T on the motor
PITCH = _DRIVE.belt_pitch_mm          # 2.0, GT2
BELT_W = _DRIVE.belt_width_mm         # 15.0
SCREW_PITCH_MM = _AXIS.screw_pitch_mm
REDUCTION = _DRIVE.reduction

# ---------------------------------------------------------- lead screw end
SHAFT_D = 10.00          # MEASURED  plain keyed land
SHAFT_LAND_L = 18.8      # MEASURED  (18.81) length of that land
THREAD_D = 8.0           # MANUAL    #14 Washer M8 / #15 Nut M8
THREAD_L = 13.0          # MEASURED  (12.99) threaded stub beyond the land
KEY_W = 4.00             # MANUAL    #2-1 "Key, 4 X 16", confirmed by measurement
KEY_H = 4.00             # square key
KEY_L = 16.0             # MEASURED  15.38 -> 16 nominal
KEY_PROUD = 1.5          # MEASURED  stands 1.5 proud, so t1 = 2.5 (DIN 6885)
KEY_HUB_DEPTH = 1.80     # DIN 6885 t2 for a 4x4 key
KEY_FIT = 0.05           # extra width in the hub keyway

# --------------------------------------------------------- GT2 tooth form
PLD = 0.254              # pitch line differential
GROOVE_R = 0.555         # groove root radius
TIP_R = 0.15             # tooth tip fillet
GROOVE_H = 0.76          # groove depth

# ------------------------------------------------------------ 40T pulley
SEAT_W = BELT_W + 1.0    # toothed width
FLANGE_T = 1.5
FLANGE_OD = 28.4         # ~1.7 proud of the tooth OD
HUB_OD = 22.0
BORE_FIT = 0.02          # bore = SHAFT_D + this, reamed
BORE_OVERRUN = 0.5       # bore runs this far past the end of the land
CBORE_D = 17.0           # recess for the stock M8 washer + nut
CBORE_DEPTH = 2.5
SETSCREW_TAP_D = 3.3     # M4 tapping drill

# -------------------------------------------- the mill's X-axis end plate
# Origin: X = 0 at the plate's OUTER face, Z = 0 on the screw centreline,
# +X outboard, +Z up.
PLATE_T = 12.0           # MEASURED
PLATE_W = 115.0          # MEASURED  21.5 + 72 + 21.5; the original 120 was a tape read
PLATE_H = 73.8           # DERIVED   2 x 36.9; the first 45 was paced, not measured

# Holes are given the way they were MEASURED - from the plate's edges - rather
# than as centres someone derived. Four rounds of tape measurements disagreed
# with each other until the 30 turned out to be a corner diagonal:
# sqrt(21.5^2 + 21.5^2) = 30.4.
HOLE_D = 10.0            # MEASURED  clearance holes; the M5s thread into the table
HOLE_FROM_TOP_EDGE = 16.0    # MEASURED  top edge of the hole to the top of the plate
HOLE_FROM_SIDE_EDGE = 16.5   # MEASURED  21.5 centre - 5 radius
BOLT_PITCH = 72.0        # MEASURED + STEP  centre to centre, and 82.39 across the
                         # outer edges = 72 + 10. Three routes, one number.
BOLT_CLEAR_D = 5.5       # M5 clearance in our parts

# Centres, measured directly. The edge readings above corroborate them to
# within 0.5 mm (16 + 5 = 21.0 against 21.5), and the corner diagonal is the
# third route: sqrt(21.5^2 + 21.5^2) = 30.4, which is the 30 that was measured.
HOLE_BELOW_TOP = 21.5    # MEASURED  hole centre below the top edge
HOLE_FROM_SIDE = 21.5    # MEASURED  hole centre in from each side edge

# MEASURED at last, and directly: 19.40 from the plate's top edge down to the
# top of the boss. Both are hard edges a caliper can sit on, which is why
# this one is believable where four earlier attempts were not - a STEP model
# said 26.3, "screw on the centreline" said 1.0, the printed gauge implied
# ~10.5 and photogrammetry said 16-30 from photos whose own checks failed.
TOP_EDGE_TO_BOSS = 19.40   # MEASURED
SCREW_BELOW_TOP = TOP_EDGE_TO_BOSS + 35.0 / 2.0     # 36.9, boss is Ø35
BOLT_ABOVE = SCREW_BELOW_TOP - HOLE_BELOW_TOP       # 15.4 above the screw

# The slots stay. They cost nothing, and after this many contradictory
# answers a part that tolerates +-8 mm is worth more than one that trusts a
# single reading. The register bore still does the locating.
BOLT_SLOT_TRAVEL = 16.0

# The plate is far taller than the 45 first paced out: 36.9 above the screw
# alone. Only the backplate OUTLINE depends on this - it needs to reach past
# the top of the slots so they are slots and not an open fork.
PLATE_TOP_ABOVE = SCREW_BELOW_TOP
PLATE_BOT_BELOW = 24.5     # ASSUMED - affects overhang only, nothing that fits
BOSS_D = 35.0            # MEASURED  bearing boss OD - this is the REGISTER
BOSS_PROUD = 16.0        # MEASURED  how far it stands off the plate face
REGISTER_FIT = 0.15

# The pulley seats against the BOSS face, not the plate face, so these are the
# same number. Confirmed in the side-on photo: scaling off the pulley's known
# 28.4 flange OD gave its width as 21.4 against the modelled 21.8, so that
# photo's scale is good to about 2%.
LAND_START_X = BOSS_PROUD

# ---------------------------------------------------------------- NEMA 23
NEMA_FRAME = 56.4
NEMA_BOLT_PITCH = 47.14
NEMA_PILOT_D = 38.1
NEMA_SHAFT_D = 6.35
NEMA_SHAFT_L = 21.0
NEMA_BOLT_CLEAR = 5.5
TENSION_SLOT = 10.0      # total travel in the motor slots
MOTOR_HUB_ALLOW = 8.0    # axial room for the bought 20T pulley's hub
MOTOR_HUB_OD = 14.0      # reference only

# ------------------------------------------------------------ the bracket
BELT_TEETH = 100         # 200 mm closed loop. Sets the centre distance.
MOTOR_ANGLE = 0.0        # degrees from straight up, toward +Y
MOUNT_T = 8.0            # backplate, bears on the mill plate
WALL_T = 8.0
MOTOR_PLATE_T = 8.0
WALL_Y_IN = 20.0         # inner face of the side walls; the belt needs ~13
BACK_W_LOW = 96.0
BACK_W_HIGH = 56.0
MOTOR_PLATE_W = 70.0
MOTOR_PLATE_H = 70.0
