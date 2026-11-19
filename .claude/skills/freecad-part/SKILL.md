---
name: freecad-part
description: Build, verify, render and export a mechanical part in hardware/mechanical/. Use when adding or changing any printed or machined part - pulleys, brackets, mounts - or when a part needs re-cutting after a measurement changes.
when_to_use: Use for anything under hardware/mechanical/. Also use when a dimension tagged ASSUMED in a params.py gets measured for real, or when a machine number the CAD depends on changes in machine/wen33013.toml.
allowed-tools: Bash(python *) Bash(FreeCADCmd *) Bash(*/FreeCADCmd.exe *) Read Edit Write Glob Grep
---

## Build a mechanical part

Parts are **scripts, not saved documents**. The `.FCStd` is a build artifact
and is gitignored; `build.py` is the source. Never open a part in the GUI and
save it - the next build silently overwrites the change.

### Layout

```
hardware/mechanical/
  lib/        gt2.py (tooth form), fcutil.py (helpers + checks), render.py, fcrpc.py
  x-drive/    params.py  build.py  mount.py  verify.py  export.py  stl/
```

### The loop

```bash
cd hardware/mechanical/<part>
FreeCADCmd build.py        # geometry + clash audit -> <part>.FCStd
FreeCADCmd verify.py       # numeric audit of the features that matter
FreeCADCmd export.py       # STLs, with a mesh audit
```

Then, only if the shape changed in a way worth looking at:

```bash
python ../lib/render.py <part>.FCStd ../../../docs/renders <port>
```

`render.py` needs a running FreeCAD **GUI**; FreeCADCmd cannot take a picture.
Find the port in `%APPDATA%/FreeCAD/mcp_instances/<pid>.json` - never assume
9875, several instances run at once and each takes the next free port.

### Rules

1. **A machine number may not be retyped.** Tooth counts, belt pitch, belt
   width and screw lead come from `machine/wen33013.toml` via `machinegen`,
   because they decide `steps_per_mm`. See AGENTS.md section 2. Only shop
   dimensions - what the part measures, what the tooth form is - live in
   `params.py`, and each one carries its provenance tag:
   `MEASURED` / `MANUAL` / `STEP` / `ASSUMED`.

2. **Every solid goes through `fcutil.check()`.** A boolean that severs a part
   returns a *valid* shape with more than one solid, and the failure surfaces
   several steps later as a nonsense STL. Check `solids == 1`, `isValid()` and
   `isClosed()` at every step, not at the end.

3. **Assert contact and fit, not the absence of overlap.** A part mirrored or
   rotated wrongly also fails to overlap. `fcutil.clearance()` reports the
   interference volume between two shapes; `build.py` must fail on a clash,
   and `verify.py` must probe the features that carry load.

4. **Verify numerically, never by eye.** Probe with `Shape.isInside`, count
   solids, sum face areas, cross-check a volume by hand. A render is for the
   reader, not for you.

5. **Probe in the ASSEMBLED frame.** `build.py` places parts at their fitted
   positions, so a probe plane written against the part's own origin silently
   misses it and reads "no material" everywhere. Derive probe coordinates from
   `params.py`, never as literals.

6. **An `ASSUMED` value may not be printed in metal.** Say so in the output
   and in the part's README. When it gets measured, change `params.py` and
   re-run the whole loop - build, verify, export, render.

### Gotchas

- `Part.makeBox` fails with "width of box too small" when a mirrored feature
  produces a negative extent. `fcutil.box()` sorts its pairs for this reason.
- A cylinder tangent to a plane tessellates non-manifold, the STL exports open
  and the slicer patches it silently. Overlap by 0.01 mm instead, and trust
  `export.py`'s mesh audit (`isSolid`, `hasNonManifolds`,
  `hasSelfIntersections`) rather than the slicer.
- Grub screws need a hub. A tapping hole through a 1.5 mm flange breaks out
  into the belt seat and shows up as a self-intersecting mesh.
- Heavy boolean loops crash FreeCAD outright. Keep roughly one part's worth of
  booleans per run; build repeated features as one profile and extrude once
  rather than fusing N solids.

### Finishing

- `CHANGELOG.md` under `## [Unreleased]`: what changed about the *part*.
- If the change closed off an alternative - a different drive ratio, a
  different mounting - write an ADR with `/new-adr`. Record the measurements.
