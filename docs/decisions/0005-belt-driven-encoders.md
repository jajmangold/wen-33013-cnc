# ADR-0005: Encoders belted to the axis, not on the motor shaft

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

We have a quantity of 14-bit absolute magnetic encoders on hand and want
position feedback, mainly to detect lost steps before they become scrap.

The obvious mounting is on the motor shaft, which is also how closed-loop
stepper kits do it. But a motor-shaft encoder measures **what the motor did**,
and that is not the question being asked. Between motor and table sit a
coupling, a ballscrew, its nut and its bearings - all of which can lose or add
motion that a shaft encoder cannot see:

- backlash in the nut
- coupling slip or windup
- screw thermal growth over a long cut
- the screw turning while the table does not

## Decision

Mount each encoder on a GT2 pulley belted to the axis, so it measures real
table travel.

Resolution therefore derives from the **pulley circumference**, not the
ballscrew lead - 16384 counts over a 20T x 2 mm = 40 mm circumference gives
409.6 counts/mm, or 2.44 um.

The model enforces this distinction: `Encoder.mount` is `"belt"` or
`"motor"`, and a belt-mounted encoder must declare `pulley_teeth` and
`belt_pitch_mm`.

## Alternatives rejected

- **Motor-shaft mounting** - finer on paper (16384 / 5 mm lead = 3277
  counts/mm, 0.31 um) and simpler to mount, but blind to everything between
  motor and table. The extra resolution measures the wrong thing precisely.
- **Linear scales** - the right answer for accuracy, and the wrong answer for
  a $1200 benchtop mill's budget and mounting space.
- **No feedback at all** - the normal arrangement for a hobby conversion. We
  already own the encoders, and a mill that silently loses a step ruins the
  part and sometimes the cutter.

## Consequences

- The feedback is **coarser than a microstep** (2.44 um versus 0.78 um). This
  is expected and correct for the job: the encoder exists to catch lost
  motion, not to resolve individual microsteps. The constraint checker emits a
  WARNING saying so, deliberately not an error.
- Following-error limits must clear the encoder resolution or noise will trip
  them mid-cut. `MIN_FERROR` is generated as `max(0.05 mm, 10 x encoder
  resolution)` for this reason.
- The belt itself is now in the measurement path. A loose or stretched belt
  reports position error that is not there. Belt tension becomes a
  commissioning item.
- Encoders hang off the RP2040's **SPI1** as master. SPI0 is the slave link
  carrying step commands from the Pi, and the model refuses an encoder
  declared on `spi0`.

## Evidence

- 14-bit = 16384 counts/rev. 20T GT2 = 40 mm circumference -> 409.6 counts/mm
  -> 2.44 um. A 12T pulley would give 1.46 um if finer proves necessary.
- 32x microstepping on a 5 mm lead = 1280 steps/mm -> 0.78 um per microstep.
- Untested: whether a belted pulley introduces enough compliance of its own to
  muddy the reading. To be checked during commissioning by comparing
  commanded, encoder-reported, and indicator-measured travel over 50 mm.
