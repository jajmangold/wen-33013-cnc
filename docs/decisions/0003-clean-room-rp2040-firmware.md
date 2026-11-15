# ADR-0003: Clean-room RP2040 firmware

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

Remora is the established LinuxCNC component + MCU firmware project for this
kind of setup, so the obvious move is to start from it. Investigation found
that the specific thing we need does not exist there, and that the parts which
do exist carry licensing problems.

What actually exists upstream:

| Transport | Supported MCUs |
|---|---|
| SPI (`Remora-spi`) | LPC176x, STM32F4 |
| Ethernet W5500 | RP2040, STM32H7, RT1052 |

**RP2040-over-SPI is not in that table.** The RP2040 port was Ethernet from
its first forum post; no fork adds an SPI slave transport. Whichever way we go,
the RP2040 SPI-slave module is new code.

Licensing compounds it:

- `scottalford75/Remora` and `Remora-RP2040-W5500`: **no license declared** -
  no grant of rights to build on them at all.
- `remora-cnc/remora-core`: GPL-3.0.
- LinuxCNC: GPL-2.0, but `hal_lib` is **LGPL-2**.

## Decision

Write the RP2040 firmware clean-room against the Pico SDK, MIT licensed. Do
not copy from the Remora repositories.

## Alternatives rejected

- **Derive from `remora-core` (GPL-3.0)** - legitimate and would reuse proven
  packet framing and module structure. Rejected because the largest piece we
  need (SPI slave on RP2040) is absent anyway, so the reuse is smaller than it
  first appears, and it would commit the firmware to GPL-3.0 for that partial
  benefit.
- **Derive from the older Remora repos** - rejected outright. No license means
  no permission, regardless of how convenient the code is.
- **Use the Ethernet firmware as-is** - would work and is maintained, but
  needs a W5500 per node and gives up the SPI decision in ADR-0002.

## Consequences

- More work up front: SPI slave, packet framing, CRC, PIO step generation.
- All of it is ours to license (MIT) and ours to test. The pure logic -
  framing, CRC, stepgen accumulator arithmetic - is host-testable without
  hardware, which suits the TDD policy.
- We lose compatibility with the existing `Remora-spi` LinuxCNC component and
  must write our own HAL component. That component links LinuxCNC and is
  therefore GPL-2.0, in `linuxcnc/components/` with its own LICENSE.
- No upstream to pull fixes from. Our bugs are entirely our own.

## Evidence

- GitHub API, 2026-11-15: `scottalford75/Remora` and
  `scottalford75/Remora-RP2040-W5500` return no SPDX license;
  `remora-cnc/remora-core` returns GPL-3.0; `LinuxCNC/linuxcnc` returns
  GPL-2.0 while `src/hal/hal_lib.c` declares "License: LGPL Version 2".
- `Remora/LinuxCNC/Components/` contains `Remora-spi` and `Remora-eth`,
  confirming the transport split above.
- The "Remora for RP2040" forum thread opens with a Wiznet W5500-EVB-Pico and
  never discusses SPI to a Pi.
