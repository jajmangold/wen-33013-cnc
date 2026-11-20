# ADR-0011: 1:1, not 2:1

- **Status:** Accepted
- **Date:** 2026-11-20
- **Supersedes:** the reduction chosen in [ADR-0009](0009-belt-drive-onto-the-stock-screw.md)

## Context

ADR-0009 chose a 2:1 belt reduction. It was decided against an **assumed**
2.0 mm screw lead, before anyone had read page 2 of the SIEG X2D User's
Guide, which documents the X and Y feed screws as 0.0625 in (1.5875 mm) per
rotation - 16 TPI.

At the real lead the screw is already an enormous reduction. A 1.5875 mm
lead at ~22% efficiency (fine-pitch acme, bronze nut) turns table force into
very little torque at the screw:

| force at the table | torque at the screw |
|---|---|
| 100 N | 0.12 Nm |
| 300 N - a realistic mini-mill cut | 0.35 Nm |
| 600 N | 0.70 Nm |
| 1000 N | 1.16 Nm |

A NEMA 23 gives about 1.0 Nm at 600 rpm on a DM542T.

## Decision

**1:1.** A 40T GT2 on the motor as well as on the screw.

| | steps/mm | resolution | mm/min at 600 rpm | margin at 300 N |
|---|---|---|---|---|
| **1:1** | **2016** | **0.50 µm** | **952** | 2.9x |
| 2:1 | 4031 | 0.25 µm | 476 | 5.7x |

The 2:1 bought torque margin that was already there twice over, and paid for
it by halving an axis that is slow to begin with. 0.50 µm is still 20x finer
than the 0.010 mm positioning accuracy the manual claims for the machine, so
the resolution it bought is not resolution anyone can use.

## Why the belt stays

The ratio and the belt are separate questions, and only the ratio changes.

The stock screw end finishes in **M8 thread**, so whatever sits outermost
has to be the nut - and the pulley is what the nut clamps. It is doing the
job the handwheel used to. A coupler would have to swallow that 13 mm stub
and still grip the Ø10 land, which needs more bore depth than it has:

- a 30 mm coupler has ~13 mm of bore per side, so after the stub there is
  about **1 mm** of grip left. Not possible.
- a 50 mm CFC-35 has ~22 mm, which leaves 7-11 mm of grip depending on where
  the bearings end. Possible, but tight enough to hinge on the real bore
  depth.

Direct coupling is the right answer at the **far** end of the screw, whose
journal is plain - no thread, nothing competing for the bore. That remains
open as a separate option and does not change this decision.

## Consequences

- `steps_per_mm` for X is 2016, not 4031. Every generated file moves.
- `max_velocity_mm_s` goes 10.0 to 15.0: 600 motor rpm is now 15.875 mm/s
  rather than 7.9.
- **The 200 mm / 100T belt gives a centre distance of 60.00 mm at 1:1**, and
  that is 2.5 mm below what the printed tower can reach. The tower needs its
  motor plate to clear the M6 heads at Z 23.5 and to land on the side walls,
  which floors the motor axis at 62.5. So the motor mount must be a bought
  bracket - which was the better answer anyway, steel not creeping - or the
  belt goes to 220 mm / 110T, where C = 70.0 and the tower fits.
- `hardware/mechanical/x-drive` is superseded twice over now: by ADR-0010 for
  the plate and by this for the ratio.
