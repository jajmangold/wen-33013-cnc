# ADR-0009: Belt drive onto the stock lead screw, ballscrews later

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

The machine description has declared `screw_pitch_mm = 5.0  # 1605 ballscrew`
for X since the project started. That was a plan, not an observation.

Measuring the X screw end on 2026-11-19 settled it. What is on the machine is
unmistakably the **stock** screw:

- a Ø10 plain land, 18.8 mm long, carrying a 4 × 4 × 16 key standing 1.5 proud
- an M8 thread, 13.0 mm, beyond it
- running in the cast X-axis bearing seat on an 8200 thrust bearing

The WEN parts list agrees in three independent places: `#13 Ball Bearing,
8200` is a 10 × 26 × 11 thrust bearing (10 mm bore), `#14`/`#15` are an M8
washer and nut, and `#2-1` is `Key, 4 × 16`. An SFU1605 drive end is Ø10 with
an M10×1 locknut in a BK12 block and has no 4 mm keyway.

Ballscrews are still wanted. They are not here yet, and the mill is not
usefully CNC until something turns the screw.

## Decision

Drive the **stock** X lead screw with a NEMA 23 through a **2:1 GT2 belt**,
bolted to the existing bearing-seat plate. Treat it as the real configuration,
not a mock-up: it goes in the model and the generated configs follow it.

The reduction is therefore part of the machine model. `Axis.drive` is a
`Drive` with `kind = "belt"` and a tooth count each end, and `steps_per_mm`
becomes `steps_per_rev * reduction / screw_pitch_mm`.

## Why a reduction at all

The stock screw is coarse-threaded and stiff, and the stock handwheel gave the
operator a long lever. A NEMA 23 does not have one. 2:1 doubles torque at the
screw and halves the rapids, which is the right trade on an axis whose rapids
are already limited by the screw's lead rather than the motor.

It also doubles resolution for free, which partly offsets the stock screw's
backlash - though it does not remove it, and nothing here should be mistaken
for making an Acme screw into a precision drive.

## Alternatives rejected

- **Direct coupling to the stock screw.** Simplest, and the jaw coupler is
  cheaper than two pulleys and a belt. Rejected: no torque multiplication, and
  a coupler puts the motor's full weight on the screw's single thrust bearing
  in line with the axis rather than off to one side where a bracket can carry
  it.
- **Wait for ballscrews.** Rejected: it blocks every other part of the
  project - homing, the pendant, the encoders, LinuxCNC commissioning - behind
  a parts order. The belt drive is also not wasted when the ballscrews arrive;
  only `screw_pitch_mm` and the pulley bore change.
- **Driving through the existing handwheel boss with a friction coupling.**
  Rejected for the obvious reason.

## Consequences

- **Every X number downstream changed.** 32x microstepping at 2 mm lead with
  2:1 demanded 266,688 Hz, over the DM542T's 200 kHz ceiling - the constraint
  checker refused to generate, which is exactly what it is for. X is now 16x
  microstepping at 10 mm/s, giving 3200 steps/mm and 32 kHz.
- The velocity ceiling is now the **motor**, not the driver: 10 mm/s on a 2 mm
  lead through 2:1 already asks 600 motor rpm.
- `screw_pitch_mm = 2.0` for X is **PROVISIONAL and unmeasured**. It is the
  most dangerous number in the TOML, because a wrong lead cuts everything at
  the wrong size without erroring. Measure it: ten full turns of the X
  handwheel, divide the table travel by ten.
- **Y and Z still declare 5 mm ballscrew leads** and have not been looked at.
  If they are also stock, they are wrong in the same way X was.
- The CAD that cuts the pulleys reads its tooth counts from the TOML, so the
  reduction cannot drift between the model and the metal.

## Evidence

- Screw end, measured 2026-11-19: Ø10 land 18.81, M8 thread 12.99, key 15.38
  long standing ~1.5 proud → a 4 × 4 key sunk 2.5 (DIN 6885 t1), hub keyway
  1.8 deep (t2).
- End plate: 12 mm thick, two M5 **clearance** holes 72 mm apart (from the
  stock table geometry in the third-party STEP model), 26.3 mm above the screw
  centreline. The stock M5 × 15 screws pass through it into the table casting.
- 2:1 at 2 mm lead, 16x microstepping → 3200 steps/mm, 0.31 µm per microstep,
  against a 2.44 µm encoder count.
