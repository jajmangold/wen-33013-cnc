# ADR-0010: An X end housing replacing the stock bearing seat

- **Status:** Accepted (2026-11-20)
- **Date:** 2026-11-20

## Context

The X drive was built to bolt onto the stock X-axis bearing seat (#18) and
change nothing else. That worked, and a printed fit coupon fitted the machine
on 2026-11-19. But it inherits two things from the stock design:

**The screw is located by one single-direction thrust bearing.** The 8200
takes load one way; the other way is taken by the handwheel nut clamping the
stack. That preload *is* the axial play, and it is set by how hard someone
did a nut up. For a CNC axis it is the difference between holding position
and not.

**The pulley gets whatever shaft is left.** With the stock stack assembled
only 10 mm of the Ø10 land remains outboard, which already forced the 40T
from 21.8 wide down to 19.0 - and nearly produced a pulley whose nut could
not clamp at all, because an M8 washer cannot pass over the Ø10 land and the
counterbore floor had run past the end of the thread.

Taking the plate off for measurement showed the land is really about 50 mm.
The stock bearing stack simply occupies 40 of it.

## Decision

Replace the stock bearing seat with a housing of our own that bolts to the
same two M6 holes in the table casting, and support the screw properly:

- **Two 6000-2RS (10 x 26 x 8) preloaded against each other**, spread as far
  along the land as it allows, pulley immediately outboard, the stock M8 nut
  clamping the whole stack. A preloaded pair takes both axial directions and
  the radial load together.
- **One Ø26 bore.** The 6000 and the stock 8200 thrust bearing share a 26 mm
  outside diameter, so the housing is a single bore at a single diameter -
  and the 8200 remains a drop-in option in the same pocket.
- Bought 10 mm-bore GT2 pulleys on the keyed shaft, retained by a grub screw
  seated **in the keyway slot** with a second at 90 degrees. The key itself
  comes out: it stands 1.5 proud and a plain Ø10 bore will not pass it.

## Alternatives rejected

- **Pulley straddled between the bearings.** Mechanically better - no
  overhang at all. Rejected because the housing then needs a window for the
  belt to escape, exactly where it wants material to hold the two outer races
  concentric. A worse part to make, for 50 N of belt pull.
- **Keeping the 8200 for dedicated thrust alongside the pair.** Runs 4 mm
  over the available land, and is redundant once two deep-groove bearings are
  preloaded against each other. It earns its place in the stock design only
  because there is just one of it.
- **Keeping the stock plate and bolting to it**, which is what exists today.
  Rejected for the two reasons above, not because it does not fit - it does.

## Consequences

- The bolt interface is unchanged and already measured: two M6 at 72 mm
  pitch, screw axis 15.7 mm below the bolt line. ADR-0009's geometry carries
  over intact.
- The register bore and its Ø35 boss disappear with the stock plate. The
  housing bolts flat to the table's end face instead.
- **The axial budget has no slack.** The land is about 50 mm and every
  arrangement considered consumed all of it, because an M8 washer cannot pass
  over the Ø10 land - so the stack must finish exactly where the thread
  starts. The land length is therefore a hard input and must be measured, not
  inferred. It is the reason this ADR is Proposed and not Accepted.
- Screw preload becomes a set-up setting rather than a side effect of handwheel
  assembly, which is what makes commissioning repeatable.

## Resolved

1. **Ø16 shoulder to M8 thread start: 54 mm.** Off a ChArUco frame at
   0.044 mm reprojection, self-calibrated two ways - the shaft reads Ø10.07
   across against a caliper 10.00, the thread 13.5 along against 12.99.
2. **Land outboard of the table face: 38 mm.** Derived from three caliper
   readings already taken - stock plate 12, boss standing 16 proud, 10 mm of
   free land beyond the assembled stock stack. It cross-checks: 54 - 38 = 16
   of shoulder inside the casting, which is the depth of the stock bearing
   pocket. The shoulder itself cannot be reached with calipers, which is why
   asking for "table face to shoulder" was the wrong question.

Both blockers are gone, so this is Accepted and
`hardware/mechanical/x-end/` builds.

**Correction to the costing above.** "Bearing centres 23 mm apart, overhang
ratio 0.59" was computed against the whole 50 mm land. Only 38 of it is
outboard of the mounting face, so the real figures are **12.6 mm apart with
an overhang ratio of 1.21**. Still far inside what a 6000 takes at 50 N of
belt pull - the bearings see about 130 N and are rated 4.5 kN - but it is
worse than this ADR first claimed, and it is why pulley width now matters.

## Still open, on the drive side only

These gate the motor tower and the TOML, not the housing:

1. Pulley width - decides the spacer; this housing tops out at 17.6, so a
   hubbed pulley will not fit.
2. Motor shaft diameter - the 10 mm bore pulleys need a 10 mm shaft.
3. Tooth counts on both pulleys; they drive steps_per_mm.
