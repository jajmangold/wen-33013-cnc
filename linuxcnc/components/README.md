# HAL components

**GPL-2.0** (see LICENSE here, not the repo-root MIT one).

These link against LinuxCNC and are therefore GPL-2.0. Do not move code
between this directory and the MIT parts of the repo without reading
`AGENTS.md` section 7.

Planned:

- `wen-spi` - the host side of the SPI link to `motion0`: packs step counts
  per servo period, unpacks position and encoder feedback, exposes HAL pins.

Note LinuxCNC's `hal_lib` is LGPL-2 even though the project COPYING is GPL-2.
