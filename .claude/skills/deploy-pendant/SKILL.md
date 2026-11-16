---
name: deploy-pendant
description: Export the SVG screens and deploy them plus the pendant firmware to the RP2040 over USB from the Pi. Use when a screen design changed, after editing firmware/pendant/, or when setting up a replacement pendant board.
when_to_use: Run after editing anything in ui/screens/ or firmware/pendant/. Also when a new RP2040 needs provisioning.
disable-model-invocation: true
allowed-tools: Bash(python *) Bash(ssh *) Bash(scp *) Read Edit
argument-hint: [device, default /dev/cnc/pendant]
---

## Deploy to the pendant

The pendant board lives on the **Pi**, not on a workstation. Deployment is
therefore: export locally, copy to the Pi, push from the Pi.

| | |
|---|---|
| Device | `${1:-/dev/cnc/pendant}` - a udev symlink, stable across reboots |
| Host | `josh@lcnc` (tailnet `100.113.70.32`) |
| Tool | `mpremote` 1.29.0 at `/opt/cnc-tools/venv`, symlinked into `/usr/local/bin` |

Use the **symlink, never `/dev/ttyACM0`**. The raw name depends on what
enumerated first; once a second node exists they will swap and you will flash
the wrong board.

### 1. Validate the screens

```bash
python -m dwinui check
```

A screen that fails to compile is a blank panel. Fix it before deploying -
the board will happily run a half-updated set of files.

### 2. Export

```bash
python -m dwinui export ui/screens/dro.svg -o ui/screens/dro_screen.py
python -m dwinui export ui/screens/jog.svg -o ui/screens/jog_screen.py
```

Exported modules are **not committed** - they are regenerated here so the
device can never run a screen that disagrees with the SVG in the repo.

### 3. Copy to the Pi, then push to the board

```bash
scp ui/screens/*_screen.py firmware/pendant/*.py josh@lcnc:/tmp/
ssh josh@lcnc 'cd /tmp && \
  mpremote connect ${1:-/dev/cnc/pendant} fs cp chimes.py :chimes.py + \
                                              cp dro_screen.py :dro_screen.py + \
                                              cp jog_screen.py :jog_screen.py'
```

The `dwin_t5uic1` driver comes from the separate `dwin-t5uic1` repo and is
**GPL-3.0** - deployed to the device, never vendored into this MIT repo.

### 4. Test before committing to autorun

Copying `main.py` makes it **run on every power-up**. Test without that first:

```bash
ssh josh@lcnc 'mpremote connect ${1:-/dev/cnc/pendant} run /tmp/demo_jog.py'
```

Only once it behaves:

```bash
ssh josh@lcnc 'mpremote connect ${1:-/dev/cnc/pendant} fs cp /tmp/main.py :main.py'
```

### 5. Confirm identity

```bash
ssh josh@lcnc 'mpremote connect ${1:-/dev/cnc/pendant} exec \
  "import machine,ubinascii; print(ubinascii.hexlify(machine.unique_id()).decode())"'
```

Must match `node.pendant.usb_serial` in `machine/wen33013.toml`. If a board
was swapped, update the TOML and `/regen` so the udev rule follows.

**The serial is lowercase in udev and conventionally printed uppercase by
MicroPython.** The generator lowercases it for exactly that reason: udev
matches case-sensitively, so an uppercase rule never fires - no error, no
symlink, and nothing to suggest why.

### Rules

- The panel boots **rotated**. Firmware calls `set_orientation(1)` before
  drawing; never remove that or every element lands off-screen with no error.
- Keep logic out of `main.py`. It cannot be unit tested - anything with a
  right answer belongs in `ui/dwinui`, which is.
- If `import` fails with `MemoryError`, cross-compile with `mpy-cross` rather
  than trimming the driver. There was ~196 KB free at last check.
