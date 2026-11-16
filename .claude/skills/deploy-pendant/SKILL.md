---
name: deploy-pendant
description: Export the SVG screens and deploy them plus the pendant firmware to the RP2040-Zero over USB. Use when a screen design changed, after editing firmware/pendant/, or when setting up a replacement pendant board.
when_to_use: Run after editing anything in ui/screens/ or firmware/pendant/. Also when a new RP2040-Zero needs provisioning.
disable-model-invocation: true
allowed-tools: Bash(python *) Read Edit
argument-hint: [COM port, e.g. COM20]
---

## Deploy to the pendant

Target port: **$1** (default COM20 - `python -m mpremote devs` lists them).

### 1. Validate the screens first

```bash
python -m dwinui check
```

A screen that fails to compile is a blank panel. Fix it before deploying -
the board will happily run a half-updated set of files.

### 2. Export

```bash
python -m dwinui export ui/screens/dro.svg -o ui/screens/dro_screen.py
```

Exported modules are **not committed** - they are regenerated here so the
device can never run a screen that disagrees with the SVG in the repo.

### 3. Deploy

```bash
python -m mpremote connect port:$1 fs cp -r <path-to>/dwin_t5uic1 :
python -m mpremote connect port:$1 fs cp ui/screens/dro_screen.py :dro_screen.py
python -m mpremote connect port:$1 fs cp firmware/pendant/main.py :main.py
```

The driver (`dwin_t5uic1`) comes from the separate `dwin-t5uic1` repo and is
**GPL-3.0** - it is deployed to the device, never vendored into this MIT repo.

### 4. Check before it runs unattended

Copying `main.py` makes it **run on every power-up**. Do not do that until the
wiring is verified with a meter (`hardware/electrical/pendant-wiring.md`). To
test without committing to autorun:

```bash
python -m mpremote connect port:$1 run firmware/pendant/main.py
```

### 5. Confirm

```bash
python -m mpremote connect port:$1 fs ls
python -m mpremote connect port:$1 exec "import machine,ubinascii; print(ubinascii.hexlify(machine.unique_id()).decode().upper())"
```

The unique id must match `node.pendant.usb_serial` in
`machine/wen33013.toml`. If a board was swapped, update the TOML and `/regen`
so the udev rule follows - otherwise the Pi pins the wrong device.

### Rules

- The panel boots **rotated**. `main.py` calls `set_orientation(0)` before
  drawing; never remove that or every element lands off-screen with no error.
- Keep logic out of `main.py`. It cannot be unit tested - anything with a
  right answer belongs in `ui/dwinui`, which is.
- If `import` fails with `MemoryError`, cross-compile with `mpy-cross` rather
  than trimming the driver. There was ~196 KB free at last check, so this
  should not happen without something else having grown.
