---
name: commission-axis
description: Bring a single axis up safely for the first time, in an order that cannot crash it - direction, then scale, then limits, then speed. Use when wiring a new axis, after changing a ballscrew, pulley, microstep setting or encoder, or when an axis moves the wrong distance or direction.
when_to_use: Before an axis moves under power for the first time, and after any mechanical or scale change. Required before that axis is allowed to cut.
argument-hint: [x|y|z]
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(python *) Bash(ssh *) Read Edit
---

## Commission axis $1

**The machine can hurt you. Keep a hand on the E-stop for every step below.**

This order exists because each step depends on the one before it. Doing them
out of order is how an axis gets driven into its own hard stop at full rapid.

### 0. Before power

- [ ] E-stop tested: pressing it removes driver power at the contactor, with
      the Pi still running. Software is not involved in this.
- [ ] `make check` clean for this axis.
- [ ] DM542T DIP switches match `machine/wen33013.toml`:
      current `current_a`, microstep `microsteps`. See
      `hardware/electrical/dm542t.md`.
- [ ] Axis free to move by hand through its full travel.
- [ ] Limit switches wired and verified in HAL *before* any motion:
      watch `halmeter` while triggering each by hand.

### 1. Direction, at the slowest speed that moves

Jog one step. Confirm it moves the direction you asked for.

- If reversed: set `invert_direction` in the TOML for this axis and `/regen`.
- Do NOT fix direction by swapping motor wires - the model would then be
  lying about the machine, and the next person to regenerate gets a surprise.

### 2. Scale, measured not assumed

Command exactly 50.000 mm. Measure the actual travel with an indicator or
calipers.

```
actual_steps_per_mm = configured_steps_per_mm * (commanded / measured)
```

- Within 0.05 mm: accept.
- Off by a clean ratio (2x, 2.5x, 1.25x): the microstep DIP switches disagree
  with `microsteps` in the TOML, or the ballscrew lead is not what was
  assumed. Fix the TOML - never a generated file.
- Off by a small odd amount: measure again over a longer distance before
  changing anything.

Record the measurement in `docs/commissioning/` with the date.

### 3. Encoder agreement

With the encoder connected, command 50 mm again and compare encoder-reported
travel against commanded.

- They should agree to within a few counts (ours resolve 2.44 um).
- Disagreeing by a constant ratio means `pulley_teeth` or `belt_pitch_mm` is
  wrong in the TOML. Remember this encoder measures the **table**, not the
  motor - if it disagrees with the motor it may be *right* and the motor
  losing steps.

### 4. Limits and homing

- [ ] Home the axis. Confirm it searches in the direction the model says.
      **Z homes UP** - if Z searches downward, stop immediately.
- [ ] Confirm it stops on the switch and backs off to latch.
- [ ] Jog to each soft limit and confirm it stops short of the hard stop.
- [ ] Deliberately trigger the limit mid-jog and confirm the machine faults.

### 5. Speed, approached from below

Start at 25% of `max_velocity_mm_s` and raise in steps, listening for stall.

- A stall sounds like a buzz with no motion; the axis has lost position.
- Back off to 70% of whatever first stalled and record it as the real limit.
- Update `max_velocity_mm_s` in the TOML and `/regen`.

### 6. Finish

- [ ] Update the TOML with every measured value, removing the PROVISIONAL note.
- [ ] `/regen`, `make test`.
- [ ] Record results and date in `docs/commissioning/`.
- [ ] `CHANGELOG.md` entry.

An axis is not commissioned until every measured value has replaced its
PROVISIONAL guess.
