# ADR-0010: An X end housing replacing the stock bearing seat

- **Status:** Proposed
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

## Still needed before this is Accepted

1. Ø16 shoulder to M8 thread start, measured.
2. Table end face to that shoulder.
3. Motor shaft diameter - the 10 mm bore pulleys need a 10 mm shaft.
4. Tooth counts on both pulleys; they drive steps_per_mm.
