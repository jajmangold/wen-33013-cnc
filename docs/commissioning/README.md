# Commissioning

Procedures for bringing the machine up, and the record of what was actually
measured. A number in `machine/wen33013.toml` marked PROVISIONAL is a guess
until it is replaced by something measured and recorded here.

## Order

Each step assumes the one before it passed.

1. **Electrical safety** - E-stop chain drops driver power with the Pi
   running. Verified by pressing the button, not by forcing a pin (ADR-0007).
2. **Latency** - `/latency-check`. Decides whether the configured 1 kHz servo
   period is honest. Nothing else is trustworthy until this is known.
3. **Communications** - SPI link up, CRC error count zero over a sustained
   run, before any motor is connected.
4. **Per axis** - `/commission-axis x|y|z`: direction, then scale, then
   encoder agreement, then limits and homing, then speed.
5. **Z drop** - unresolved. A 1605 ballscrew back-drives, so the head can fall
   when E-stop removes power. Do not leave a tool over a workpiece until this
   is answered (ADR-0007).
6. **Squareness and backlash** - measured, recorded, compensated.
7. **First cut** - air cut first, then foam or wax, then metal.

## What to record

For each measurement, write down the value, the **date**, and the conditions.
A latency number without its kernel version and load condition is not
evidence; a scale measurement without the distance it was taken over is not
either.

Files in this directory:

| File | Contents |
|---|---|
| `latency.md` | latency runs: date, kernel, load, max jitter |
| `axis-x.md`, `axis-y.md`, `axis-z.md` | per-axis commissioning records |
| `spi-link.md` | clock rate, error counts, cable length |

## Known open items

Ordered by what blocks what. The first two block cutting anything.

1. **Z drop on E-stop** - a 1605 ballscrew back-drives, so removing driver
   power drops the head. Needs a brake, counterbalance, or an explicit
   decision to accept it. Until then, do not leave a tool in the spindle over
   a workpiece (ADR-0007).
2. ~~Latency never measured~~ - **done 2026-11-15**: 231 us worst case under
   load with the `performance` governor, 23% of the servo period. 1 kHz is
   viable *because step generation is on the MCU*. See `latency.md`.
3. **No HAL files yet.** The generated INI references `core.hal`,
   `remora-spi.hal` and `estop.hal`, none of which exist - the config cannot
   load until the SPI HAL component is written. The integration test that
   globs for HAL files currently passes vacuously.
4. **Gamepad watchdog unproven.** ADR-0008 assumes `hal_input` pins freeze
   rather than zero when a pad disconnects, and the watchdog is designed on
   that pessimistic reading. Prove it by **pulling the batteries mid-jog**
   and confirming motion stops within 150 ms. Do this with the spindle off
   and plenty of travel ahead.
5. **Pendant inputs beyond the knob are untested.** The panel itself now works - wiring
   verified, handshake succeeds, the DRO screen renders - but the encoder,
   its button and the beeper have not been exercised, and nothing yet talks
   to LinuxCNC (`hardware/electrical/pendant-wiring.md`).
6. **VNC does not start** on the Pi, so there is no GUI fallback if the
   pendant is unavailable (`pi/provision/README.md`).

Resolved:

- ~~Beeper unusable~~ - it is an edge-clicking element, loud low and weak
  high, so the chime palette was rewritten into 110-440 Hz. Audible and
  distinguishable without any added hardware. A transistor driver remains an
  optional upgrade, not a requirement.

- ~~`HOME_SEQUENCE` order~~ - fixed 2026-11-15, Z now homes first, with a
  constraint check preventing regression (ADR-0006).
