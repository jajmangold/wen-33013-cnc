# ADR-0004: One machine description, everything generated

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

Several files need to agree about the same physical facts:

- LinuxCNC's INI needs `SCALE` in steps/mm, velocities, limits, homing.
- The node firmware needs steps/mm, step-rate ceilings, encoder counts/mm.
- udev needs each USB node's serial.
- The wiring documentation needs microstep and current DIP settings.

Kept by hand, these drift. The failure is not loud: when the INI and the
firmware disagree about steps/mm, **nothing errors**. LinuxCNC commands a
distance, the machine travels a different one, and every file looks correct
when read on its own.

This exact bug class has already cost real time on another machine here - a
`rotation_distance` left over from a previous extruder produced 2.5x
over-extrusion and went unexplained for months.

## Decision

`machine/wen33013.toml` is the single source of truth. Every machine-dependent
file is generated from it by `tools/machinegen`, carries a `DO NOT EDIT`
banner and a `source-fingerprint`, and `make verify` fails the build if any
generated file has drifted.

Crucially, the generators are covered by a test that asserts their outputs
**agree with each other** - `tests/unit/test_emit.py::TestScaleAgreement`
compares the INI's `SCALE` against the firmware's `STEPS_PER_MM` for every
axis.

## Alternatives rejected

- **Hand-maintained files with a comment saying "keep in sync"** - this is the
  status quo everywhere, and it is precisely what failed before. A comment
  cannot fail a build.
- **Firmware reads its config at runtime from the host** - attractive, and
  removes the agreement problem by construction. Rejected for now because it
  moves scale into runtime state, where a node that boots before the host, or
  misses a packet, runs on stale or default numbers. Worth revisiting once the
  protocol is proven.
- **Generate the firmware constants only, hand-write the INI** - the INI is
  where `SCALE` lives, so this leaves exactly the dangerous half manual.

## Consequences

- Changing a machine fact is a one-line edit plus `/regen`.
- Generated files are committed, so the repo always shows what is actually on
  the machine, and the diff of a regeneration is reviewable.
- Anything the generator cannot express has to be added to the generator. That
  is friction by design: it keeps hand-written constants from creeping back.
- Hand-written HAL glue still exists alongside the generated INI, and it must
  not contain numbers. Any constant in a HAL file is a bug.

## Evidence

- The arithmetic under test: 200 steps/rev x 32 microsteps / 5 mm lead =
  1280 steps/mm; 14-bit encoder over a 20T GT2 pulley = 16384 / 40 mm =
  409.6 counts/mm.
- During development of this very tool, a real defect was caught by its own
  tests: `parse_machine` silently dropped the encoder `mount` field, so every
  belt encoder fell back to motor-shaft arithmetic (3276.8 instead of 409.6
  counts/mm - a factor of 8). It produced entirely plausible output.
