# ADR-0008: The gamepad commands motion but can never stop the machine

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

An Xbox controller is the primary jog input. It is genuinely good at this:
proportional sticks give fine control near centre and rapid traverse at full
deflection, which a step/detent pendant cannot.

But a stick is a motion command with no spring-loaded honesty about whether
anyone is holding the controller. Three failure modes have to be answered
before one is allowed near a mill:

1. **Nobody is holding it.** A pad set down on the table with a worn stick
   resting off-centre is a standing jog command.
2. **It disappears.** A wireless pad that goes flat or out of range leaves
   `hal_input`'s pins at their *last* value. Mid-jog, that is a stick still
   deflected, and nothing in the stack notices.
3. **It looks like a stop.** The temptation to map a big red button to
   E-stop is strong and must be refused.

## Decision

The gamepad is read on the **Pi** by LinuxCNC's `hal_input`
(`/usr/bin/hal_input`, present on the image) into `halui.axis.N.analog`. No
custom firmware, no RP2040 USB host.

Three rules, recorded in `machine/wen33013.toml` under `[input.gamepad]` and
asserted by `tests/unit/test_gamepad.py`:

- **Deadman.** `LB` must be held for any jog. The analog jog pins are ANDed
  with it. Let go, motion stops.
- **Watchdog.** No pad events for `watchdog_ms` (150 ms) drops the deadman.
  At the fastest configured rapid that bounds a runaway to under 10 mm, and
  the test states it in millimetres rather than milliseconds because that is
  the number that matters.
- **Deadzone.** `halui.joint.jog-deadband` set above the controller's actual
  resting drift, measured on the real pad rather than assumed.

**No E-stop on the pad, ever.** E-stop is the hardwired contactor chain
(ADR-0007). A pad button that looks like an E-stop is worse than none,
because it will be trusted - and it fails silently in exactly the case you
need it, when the pad has disconnected.

Rumble is confirmation only, never information: gloves, shop noise and a
put-down controller all defeat it.

## Alternatives rejected

- **Gamepad into the pendant RP2040.** Would need USB host on the RP2040 (
  possible via PIO, fiddly) and then relaying over CDC, adding latency and a
  failure point to reach a place LinuxCNC can already read natively.
- **No deadman, rely on the deadzone.** A deadzone stops drift, not a pad
  that someone leaned on, and does nothing about disconnection.
- **Software E-stop on the pad in addition to the hardwired one.** Rejected
  because a second, less reliable stop teaches the operator to reach for the
  wrong one.

## Consequences

- Jogging requires two hands-ish: deadman plus stick. That is deliberate and
  matches industrial hold-to-run practice.
- A wired pad is safer than wireless and is the default in the TOML. Wireless
  is permitted but makes the watchdog load-bearing rather than belt-and-braces.
- The panel's rotary encoder keeps a job the pad is bad at: single-step MPG
  jogging at a chosen step size.

## Evidence

- `halui.axis.L.analog` takes a float used as a jog-speed multiplier;
  `halui.joint.jog-deadband` ignores analog inputs below a threshold. Both
  documented in LinuxCNC's halui manual.
- **Untested assumption:** that `hal_input` pins genuinely freeze rather than
  zero on disconnect. The watchdog is designed on the pessimistic reading.
  Retire this by pulling the batteries mid-jog during commissioning - that
  test is listed in `docs/commissioning/README.md`.
