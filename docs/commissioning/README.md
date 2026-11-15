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

- **`HOME_SEQUENCE` order is wrong.** The generator emits sequences in XYZ
  order, so X and Y home before Z retracts. With a tool in the spindle and a
  vise on the table that is the wrong order. Fix before first homing
  (ADR-0006).
- **Z drop on E-stop** - no brake, counterbalance or decision yet (ADR-0007).
- **VNC does not start** on the Pi, so there is no GUI fallback if the
  pendant is unavailable (`pi/provision/README.md`).
- **Latency never measured** - every timing value in the repo is provisional.
