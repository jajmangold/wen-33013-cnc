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
# The FREE keyed length, outboard of the bearing stack - not the whole land.
# 18.81 was the stub exposed with the plate on; with the plate off the plain
# shaft measures about 50 against the ChArUco board, and the bearings,
# spacers and retainer take all but the last 10 of it.
SHAFT_LAND_L = 10.0    # MEASURED, with the stack assembled
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
# Deep enough to swallow an M8 washer (1.6) and nut (6.5). The washer's
# ~8.4 bore cannot pass over the Ø10 land, so the counterbore FLOOR has
# to land on the thread - which is what sets the pulley's width.
CBORE_DEPTH = 8.5
SETSCREW_TAP_D = 3.3     # M4 tapping drill

# -------------------------------------------- the mill's X-axis end plate
# Origin: X = 0 at the plate's OUTER face, Z = 0 on the screw centreline,
# +X outboard, +Z up.
PLATE_T = 12.0           # MEASURED
# From Josh's traced model of the plate (plate2.FCStd, drawn over a photo).
# It is in arbitrary units, but it carries two features whose true size is
# known, so it calibrates itself: scaling by the 72 bolt pitch and by the
# 45.42 plate height agree to 1.4%, and the hole-below-top falls out at
# 21.0-21.3 against the 21.5 measured on the machine. The holes are
# symmetric - 22.7 from the left edge, 22.2 from the right - so an earlier
# guess that they sat off-centre was wrong.
PLATE_W = 117.0          # TRACED    22.5 + 72 + 22.5, good to about +-1
PLATE_H = 45.42          # MEASURED  the plain part of the plate

# Holes are given the way they were MEASURED - from the plate's edges - rather
# than as centres someone derived. Four rounds of tape measurements disagreed
# with each other until the 30 turned out to be a corner diagonal:
# sqrt(21.5^2 + 21.5^2) = 30.4.
HOLE_D = 10.0            # MEASURED  clearance holes; the M5s thread into the table
HOLE_FROM_TOP_EDGE = 16.0    # MEASURED  top edge of the hole to the top of the plate
HOLE_FROM_SIDE_EDGE = 16.5   # MEASURED  21.5 centre - 5 radius
BOLT_PITCH = 72.0        # MEASURED + STEP  centre to centre, and 82.39 across the
                         # outer edges = 72 + 10. Three routes, one number.
# M6, not M5. WEN parts list #17 "Cap Screw, M6 X 16", which the exploded
# view on page 18 shows entering both holes of #18, the X-Axis Bearing Seat.
# The list alignment is confirmed by four parts measured on the machine:
# #2-1 Key 4x16, #13 Ball Bearing 8200, #14 Washer M8, #15 Nut M8.
# An M6 cap head is Ø10 - the same as the plate's holes - so the head sits
# on their chamfer. Our 6.5 slots are narrower, so they retain it properly.
BOLT_CLEAR_D = 6.5       # M6 clearance in our parts

# Centres, measured directly. The edge readings above corroborate them to
# within 0.5 mm (16 + 5 = 21.0 against 21.5), and the corner diagonal is the
# third route: sqrt(21.5^2 + 21.5^2) = 30.4, which is the 30 that was measured.
HOLE_BELOW_TOP = 21.5    # MEASURED  hole centre below the top edge
HOLE_FROM_SIDE = 22.5    # TRACED    hole centre in from each side edge

# MEASURED two independent ways, which is why this one is finally believed.
# Both are hard edges a caliper can sit on, and they agree to 0.6 mm:
#
#   top edge -> TOP of the boss      19.40 + 17.5 = 36.90 below the top
#   top edge -> BOTTOM of the lobe   54.99 - 17.5 = 37.49 below the top
#
# Four earlier attempts spanned 25 mm (26.3 from a third-party model, 1.0
# from "screw on the centreline", ~10.5 from how a printed gauge sat, 16-30
# from photogrammetry) and every one of them inferred this from something
# else rather than measuring it.
TOP_EDGE_TO_BOSS_TOP = 19.40      # MEASURED
TOP_EDGE_TO_LOBE_BOTTOM = 54.99   # MEASURED
_VIA_TOP = TOP_EDGE_TO_BOSS_TOP + 35.0 / 2.0
_VIA_BOTTOM = TOP_EDGE_TO_LOBE_BOTTOM - 35.0 / 2.0
if abs(_VIA_TOP - _VIA_BOTTOM) > 1.5:
    raise SystemExit(
        f"the two routes to the screw axis disagree: "
        f"{_VIA_TOP:.2f} vs {_VIA_BOTTOM:.2f} below the top edge")
SCREW_BELOW_TOP = (_VIA_TOP + _VIA_BOTTOM) / 2.0        # 37.20
BOLT_ABOVE = SCREW_BELOW_TOP - HOLE_BELOW_TOP           # 15.7 above the screw

# The slots stay. They cost nothing and the register bore locates the part.
BOLT_SLOT_TRAVEL = 16.0

# The screw is NOT central: 37.2 down a 45.42 plate, 8.2 above its bottom
# edge, with the boss lobe hanging ~9 below that edge. An earlier model had
# the plate 73.8 tall on the assumption the screw was centred - it is not.
PLATE_TOP_ABOVE = SCREW_BELOW_TOP
PLATE_BOT_BELOW = PLATE_H - SCREW_BELOW_TOP             # 8.2
BOSS_D = 35.0            # MEASURED  bearing boss OD - this is the REGISTER
BOSS_PROUD = 16.0        # MEASURED  how far it stands off the plate face
# The bore CLEARS the boss, it does not register on it. Nothing about this
# bracket needs locating tightly: the pulley planes are set by the pulleys on
# their own shafts, centre distance is adjustable through the motor's +-8 mm
# slots, and lateral offset only changes the direction of belt pull. A close
# register bought precision nothing consumes, while adding the one failure
# mode that stops a part going on at all - which is exactly what happened to
# the first bracket.
BORE_CLEARANCE = 3.5     # radial, so the bore is Ø42 over a Ø35 boss

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
FIT_PLATE_T = 4.0        # the fit coupon: the bracket's first 4 mm, nothing else
WALL_T = 8.0
MOTOR_PLATE_T = 8.0
# Inner face of the side walls. The belt needs ~13 and the 40T flange 14.2,
# but the binding constraint is the BOSS: it stands 16 proud and so pokes 8
# past the backplate into this channel, at Ø35 plus whatever the loose bore
# lets it sit off-centre. 17.5 + 3.5 = 21.0, so 22.5 keeps 1.5 in hand.
WALL_Y_IN = 22.5
BACK_W_LOW = 96.0
BACK_W_HIGH = 56.0
MOTOR_PLATE_W = 70.0
MOTOR_PLATE_H = 70.0
