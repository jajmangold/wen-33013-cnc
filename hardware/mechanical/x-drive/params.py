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
BOLT_PITCH = 72.0        # STEP      (Josh's tape read 70; the model is finer)
BOLT_ABOVE = 26.3        # STEP      bolt line above the screw centreline
BOLT_CLEAR_D = 5.5       # M5 clearance
PLATE_TOP_ABOVE = 34.5   # ASSUMED   45 tall, bolts 26.3 up
PLATE_BOT_BELOW = 10.5   # ASSUMED
BOSS_D = 38.0            # ASSUMED   bearing boss OD - this is the REGISTER
BOSS_PROUD = 10.0        # ASSUMED   how far it stands off the plate face
LAND_START_X = 10.0      # ASSUMED   plate face to the start of the d10 land
REGISTER_FIT = 0.15

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
