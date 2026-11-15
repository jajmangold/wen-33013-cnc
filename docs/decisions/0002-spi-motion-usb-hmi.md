# ADR-0002: SPI for motion and safety, USB for the screen

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

The design uses several RP2040 nodes, not one. Once there is more than one
node, the question becomes which bus each one sits on - and the buses are not
interchangeable.

SPI from the Pi is a master-driven, deterministic exchange: the host clocks a
packet every servo period and knows when it completes. USB CDC is scheduled by
the host controller with no latency guarantee; it is usually fast and
occasionally not, and nothing tells you which.

## Decision

Duties are assigned by what failure looks like, not by convenience:

- **SPI** - step generation, limit switches, probing. Anything realtime, and
  anything that must stop the machine.
- **USB CDC** - the DWIN pendant, and any future display or data-logging node.

This is **enforced in code**, not documented and hoped for:
`tools/machinegen/constraints.py` raises a hard error if a node with role
`motion` or `io`, or with `safety_inputs`, is declared on USB.

## Alternatives rejected

- **Everything on USB** (the Klipper-style arrangement) - works there because
  Klipper schedules moves ahead on the MCU with timestamps. LinuxCNC's servo
  thread expects a response each period. Different model, different bus.
- **Everything on SPI** - would mean running SPI to the pendant on the control
  cabinet door for no benefit. The screen does not need determinism, and a
  longer SPI run is a signal-integrity problem we would be creating for free.
- **Ethernet (W5500) for everything** - the maintained Remora RP2040 transport,
  and a reasonable design. Rejected for now because it adds a W5500 per node
  when the Pi 4 can already drive SPI directly (ADR-0001). Worth revisiting if
  SPI signal integrity proves troublesome over the real cable runs.

## Consequences

- A stuttering screen is cosmetic. That is the entire point of the split.
- USB nodes need stable identity or they swap places on reboot; the generator
  emits udev rules keyed on USB serial for exactly this reason.
- Adding a safety input later means adding it to the SPI node, not to whatever
  node is convenient. The constraint check will refuse the shortcut.

## Evidence

- DM542T timing demands (2.5 us pulse, 5 us direction setup, 200 kHz ceiling)
  are met by PIO on the node; the bus only has to carry step *counts* per
  servo period, not individual pulses.
- At a 1 kHz servo period and the DM542T's 200 kHz ceiling, the largest
  possible burst is 200 steps per packet - comfortably inside a single byte,
  which is what the protocol encodes.
- Untested assumption: that 10 MHz SPI over the real cable run is clean. The
  `spi_clock_hz` value is PROVISIONAL and must only be raised against an
  observed CRC error count of zero.
