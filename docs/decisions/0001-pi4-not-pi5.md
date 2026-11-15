# ADR-0001: Raspberry Pi 4, not Pi 5

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

The controller needs to talk to RP2040 motion nodes over SPI at the servo
rate. The obvious instinct is to use the newest Pi.

The LinuxCNC SPI component does not use `spidev`. It unloads the kernel driver
and drives the SPI peripheral registers directly, because going through
`spidev` is not fast enough to serve a servo thread.

That approach depends on the peripheral layout of the BCM2711. The Pi 5 moved
its peripherals behind the new **RP1** I/O chip, which breaks direct register
access entirely.

## Decision

Use a **Raspberry Pi 4** as the LinuxCNC host.

## Alternatives rejected

- **Pi 5** - there is no working SPI driver for LinuxCNC on it. This is not a
  performance gap to be tuned around; the register-level access the component
  relies on does not exist in the same form. Choosing a Pi 5 would have forced
  the Ethernet transport (ADR-0002) before we had any reason to want it.
- **spidev on either Pi** - too slow for a servo thread, by the explicit
  design of the existing component.
- **x86 mini PC** - would sidestep all of this and give better latency. Not
  chosen because the Pi 4 is already on hand and its GPIO is wanted for the
  pendant and for hardwired safety signalling. Revisit if latency measurements
  (see `/latency-check`) come back marginal.

## Consequences

- SPI stays available as the motion transport.
- We are on hardware with a known ceiling. If the Pi 4 proves too slow once
  real measurements exist, the fallback is an x86 host, not a Pi 5.
- The Pi 4's quirks are ours to live with, including dual kernels - the
  provisioned machine carries both an RT and a stock kernel, and an
  `apt upgrade` that repoints the default would silently cost us realtime.
  See `pi/provision/README.md`.

## Evidence

- Pi 5 / RP1 incompatibility with the LinuxCNC SPI driver, discussed on the
  Raspberry Pi forums (thread 365950) and in the LinuxCNC forum: "currently
  there is no working driver for SPI comms with the RPi5".
- Provisioned host verified 2026-11-15: Pi 4 Model B Rev 1.2, 4 GB, kernel
  `6.12.34+rpt-rpi-v8-rt`, `SMP PREEMPT_RT`, `/dev/spidev0.0` and `0.1`
  present with `dtparam=spi=on` already in `config.txt`.
- Latency on this host is **not yet measured**. Every timing assumption in
  this repo is provisional until `/latency-check` has been run under load.
