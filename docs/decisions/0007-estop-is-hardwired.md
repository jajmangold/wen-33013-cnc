# ADR-0007: E-stop is hardwired; software only observes it

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

Every part of this control chain can fail in a way that leaves motion running:
the Pi can lock up, the SPI link can stop being serviced, a node can hang in a
loop, firmware can have a bug, a USB device can drop off the bus.

If stopping the machine depends on any of those working, then stopping the
machine depends on the thing that just failed.

## Decision

The E-stop is a **physical contactor chain** that removes power from the
stepper drivers and the spindle directly. It is wired in series through the
E-stop button and any other safety interlocks, and it functions with the Pi
powered off, crashed, or absent.

Software's only role is to **observe** E-stop state so LinuxCNC can fault and
stop queuing motion. No software path is permitted to be the only thing
standing between a command and a moving axis.

Related rules, enforced in `tools/machinegen/constraints.py`:

- Limit switches and probing are `safety_inputs` and must be on the SPI node.
  Declaring them on a USB node is a hard error.
- A node with role `motion` or `io` cannot be declared on USB at all.

## Alternatives rejected

- **Software E-stop via the pendant** - the pendant is on USB CDC, which has
  no latency guarantee and can disconnect entirely. A stop button that
  sometimes takes an unbounded time to act, and sometimes is not connected, is
  worse than no button because it is trusted.
- **E-stop handled in node firmware** - better, but still depends on firmware
  we wrote being correct and the node being alive. It is a useful *second*
  layer, never the first.
- **Relying on LinuxCNC's E-stop chain alone** - LinuxCNC's estop is a
  software state. It is correct and should be wired up; it is not a substitute
  for removing power.

## Consequences

- The electrical design has to come first: contactor, latching E-stop button,
  and a path for the controller to sense the chain's state. This is in
  `hardware/electrical/`.
- Driver power being cut means the axes are unpowered and can back-drive. On
  Z, that means **the head can drop** when E-stop is hit. The Z axis needs
  either a brake, a self-locking screw, or a counterbalance; a ballscrew is
  explicitly not self-locking.
- Recovering from E-stop requires re-homing, because position is lost when the
  drivers lose power. That is the correct behaviour, not an inconvenience to
  engineer around.

## Open item

**Z drop on E-stop is unresolved.** The conversion plan uses a 1605 ballscrew
on Z, which will back-drive under the weight of the head. Until this is
answered - brake, gas spring, counterweight, or accepting a controlled drop -
the machine must not be left with a tool in the spindle over a workpiece.

## Evidence

- Untested assumption to retire during commissioning: that the contactor drops
  out fast enough to matter at rapid, and that the controller sees the state
  change and faults rather than continuing to queue motion.
