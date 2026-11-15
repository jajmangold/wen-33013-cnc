# wen-33013-cnc

Converting a **WEN 33013** benchtop mill to CNC under LinuxCNC.

```
LinuxCNC (Raspberry Pi 4 "lcnc", PREEMPT_RT kernel)
   |
   |-- SPI ------ motion0  (RP2040)  PIO step/dir -> DM542T -> NEMA 23
   |                                 SPI1 -> 14-bit belt encoders
   |
   '-- USB ------ pendant  (RP2040)  DWIN T5UIC1 panel (Ender 3 V2 screen)
```

| | |
|---|---|
| Base machine | WEN 33013, R8 spindle, 100-2500 RPM, 130 lb |
| Travels | X 300 mm, Y 130 mm, Z 177.8 mm |
| Drives | DM542T at 32x microstepping, NEMA 23 |
| Resolution | 1280 steps/mm (0.78 um per microstep) |
| Feedback | 14-bit absolute encoders, GT2 belt driven, 409.6 counts/mm (2.44 um) |
| Controller | LinuxCNC 2.9.8 on Pi 4, 1 kHz servo thread |

## The idea

One file, `machine/wen33013.toml`, describes the machine. Everything else is
generated from it:

```
machine/wen33013.toml ──┬──► linuxcnc/configs/wen33013/wen33013.ini
                        ├──► firmware/pico-spi/include/machine_config_*.h
                        └──► pi/provision/99-cnc-nodes.rules
```

That means the scale LinuxCNC commands and the scale the firmware applies
cannot drift apart, because a test asserts they are the same number. When they
do drift, nothing errors - the machine just cuts everything at the wrong size.

## Quick start

```bash
make test        # unit tests (fast, no hardware)
make check       # validate the machine against physical limits
make gen         # regenerate everything
make verify      # fail if generated files are stale
make all         # verify + lint + test, before committing
```

No `make` (e.g. Windows)? Same targets via the stdlib task runner:

```bash
python tasks.py all
```

No runtime dependencies - stdlib only, so it runs on a bare Pi. `pytest` and
`ruff` are dev-only.

## Layout

| Path | What |
|---|---|
| `machine/` | the single source of truth |
| `tools/machinegen/` | model, constraints, generators |
| `linuxcnc/` | generated INI, hand-written HAL glue, HAL components |
| `firmware/pico-spi/` | RP2040 SPI slave + PIO step generation |
| `ui/` | SVG -> DWIN panel compiler, screen designs |
| `pi/provision/` | how the Pi is built, from blank card to running |
| `hardware/` | wiring, DIP settings, BOM, CAD |
| `docs/decisions/` | ADRs - why things are the way they are |
| `docs/commissioning/` | procedures for bringing the machine up safely |
| `tests/` | `unit` (always), `integration` (needs LinuxCNC), `hardware` (needs the mill) |

## Safety

The E-stop is **hardwired** and kills driver power through a physical
contactor. Software only observes it. Realtime and safety duties (step
generation, limits, probing) are confined to the SPI node; USB is for the
screen, which is never in the stop path. These rules are enforced by
`tools/machinegen/constraints.py`, not just documented.

## Status

Early. The Pi is provisioned and on the network; the machine description,
generators and constraint checks are working and tested. The RP2040 firmware
and the mechanical conversion are not started.

See `CHANGELOG.md` for what has actually been done, and `AGENTS.md` for the
working standards.

## Licensing

Mixed on purpose: `tools/`, `ui/` and `firmware/` are MIT (clean-room);
`linuxcnc/components/` is GPL-2.0 because it links LinuxCNC; the DWIN pendant
driver is GPL-3.0. See `AGENTS.md` section 7 before moving code between them.
