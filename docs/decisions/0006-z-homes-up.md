# ADR-0006: Z homes up

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

Homing direction is a one-character change in a config file and has
asymmetric consequences on a vertical axis.

A Z axis homing **downward** drives the spindle toward the table at homing
speed. If the switch is mis-wired, mis-positioned, or simply not reached, the
axis keeps going until it hits something - a vise, a workpiece, the table, or
a cutter. On a mill with a 0.75 HP head, that is a broken tool at best.

A Z axis homing **upward** retracts away from everything. A failure to find
the switch ends with the axis at the top of its travel, which is harmless.

## Decision

Z homes in the positive direction, toward the top of travel.
`home_direction = 1` for `axis.z`, and `HOME_SEARCH_VEL` in the generated INI
is positive as a result.

## Alternatives rejected

- **Z homes down to the table** - used on some machines to reference the table
  surface directly. Rejected: it makes every homing operation a controlled
  collision attempt. Tool length referencing belongs to a probe cycle, not to
  homing.

## Consequences

- Homing sequence puts Z first (`HOME_SEQUENCE = 0` for the Z joint when it is
  ordered first) so the tool is clear before X and Y move. The generated INI
  currently assigns sequences in XYZ order; **this is a known gap** - see
  below.
- Work offsets are referenced from a probe cycle, not from homing.

## Homing order - resolved 2026-11-15

Originally the generator emitted `HOME_SEQUENCE` in axis order (X=0, Y=1,
Z=2), which homes X and Y *before* Z retracts - dragging the table under a
tool that is still down.

Fixed: `emit.home_sequence()` now assigns **Z sequence 0** and the remaining
axes follow. The generated INI reads `HOME_SEQUENCE = 0` on the Z joint.

Defended in two places, because this one is silent when wrong:

- `tests/unit/test_homing.py` asserts Z is first in both the helper and the
  rendered INI, that sequences are unique, and that an XY-only machine still
  numbers from zero.
- `constraints._check_homing_order` raises an ERROR if any axis would home at
  or before Z, so a future change to the generator cannot reintroduce it
  quietly.

## Evidence

- `tests/unit/test_emit.py::TestIni::test_home_search_direction_follows_the_axis`
  asserts the Z joint's `HOME_SEARCH_VEL` is positive.
- `tests/unit/test_model.py::TestRealMachine::test_z_homes_up` asserts the
  model value directly, so the rule survives a generator rewrite.
