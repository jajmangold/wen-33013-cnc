# AGENTS.md - RP2040 motion node firmware

Root `AGENTS.md` applies. This adds the rules specific to code that runs on
the node and moves the machine.

## What this is

Clean-room firmware (ADR-0003). **Do not copy from the Remora repositories** -
the original ones declare no license, and `remora-core` is GPL-3.0 while this
directory is MIT.

Responsibilities:

- SPI **slave** on SPI0 to the Pi, one packet exchange per servo period
- PIO step/dir generation into DM542T drivers
- SPI1 **master** reading 14-bit absolute encoders
- Limit switch and probe inputs (this node carries `safety_inputs`)

## Hard constraints

- `machine_config_<node>.h` is **generated**. Never edit it, never retype a
  constant it already provides.
- SPI0 is the slave link. Encoders go on SPI1 or PIO - never SPI0.
- DM542T timing is physical: PUL low >= **2.5 us**, DIR setup >= **5.0 us**,
  <= **200 kHz**. The generated header exports these as
  `STEP_PULSE_MIN_NS`, `DIR_SETUP_MIN_NS`, `MAX_STEP_RATE_HZ`. The PIO
  program MUST be derived from them, not from a number typed in by hand.
  Violating them does not fail loudly - the driver drops steps and the axis
  loses position mid-cut.
- This node holds safety inputs. A limit switch must be acted on within one
  servo period, every period. No code path in the realtime loop may block,
  allocate, `printf`, or be unbounded.

## Testing

The realtime path cannot be unit tested on a dev box, but most of the logic
is not realtime-specific. Split it so it can be:

- **Host-testable, MUST be TDD** - packet framing, CRC, the stepgen
  accumulator arithmetic, encoder count unwrapping and wraparound, command
  validation. Keep these in plain C with no SDK dependency so they compile
  and run on the host under `tests/`.
- **Needs hardware** - PIO timing, SPI electrical behaviour, encoder reads.
  Verify with a scope and record the measurement in `docs/commissioning/`.

Specifically test the arithmetic that is easy to get subtly wrong:

- accumulator fractional carry over many cycles (does 1000 cycles of 0.3
  steps produce exactly 300 steps?)
- encoder wraparound at the 14-bit boundary in both directions
- CRC rejecting a single flipped bit anywhere in the packet
- a burst count larger than the field can hold being refused, not truncated

## Style

- C11, Pico SDK, no dynamic allocation after init.
- Core 1 runs the realtime loop; keep anything that can block on core 0.
- A magic number in this directory is a bug. It belongs in the machine model.
