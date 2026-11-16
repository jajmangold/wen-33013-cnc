# Pendant UI design

272x480 portrait DWIN panel, an Xbox controller, and the panel's own rotary
encoder. This document is the thinking; `ui/screens/*.svg` is the result.

---

## 1. Who is using this, and when

Not someone sitting at a desk. Someone **standing at the machine**, often
with one hand on the work, sometimes with chips flying, usually within arm's
reach of the E-stop. Glanceable beats dense. Every number that matters must
be readable from two metres away.

The user stories, in rough order of how often they happen:

| # | Story | What the UI owes them |
|---|---|---|
| 1 | "Where is the tool right now?" | Big DRO, always visible, no navigation |
| 2 | "Move the table there" | Proportional jog + fine MPG, no mode hunting |
| 3 | "Set this corner as zero" | Touch-off in two button presses, confirmed |
| 4 | "Is it homed? Can I trust the numbers?" | Unmissable NOT HOMED state |
| 5 | "Run the program" | Progress, line, time remaining, current tool |
| 6 | "It's chattering - slow it down" | Feed override reachable **while cutting**, one control |
| 7 | "Stop. Now." | Hardwired E-stop. The UI is not in this path |
| 8 | "Why won't it move?" | Diagnostics that name the blocker |
| 9 | "Did it lose steps?" | Following error from the belt encoders, visible |
| 10 | "Find the top of the part" | Probe cycle with a clear result |
| 11 | "Something went wrong" | Full-screen alarm, stating what and what to do |

Stories 6 and 7 are the ones that are usually designed badly. Feed override
must be adjustable **without navigating anywhere**, because by the time you
have found a menu the cut is ruined. It is therefore on an analog trigger,
live on every screen.

---

## 2. Input model

Three input devices, each doing what it is good at.

### Xbox controller - navigation and coarse motion

Plugged into the **Pi**, read by LinuxCNC's `hal_input` (already present at
`/usr/bin/hal_input`), feeding `halui.axis.N.analog` for proportional jog.
No custom firmware, no RP2040 USB host.

| Control | Function |
|---|---|
| **LB (hold)** | **DEADMAN.** No jog happens unless held. See safety. |
| Left stick | X / Y proportional jog, speed by deflection |
| Right stick (Y) | Z jog |
| RT (analog) | Feed override, live, on every screen |
| LT (analog) | Rapid modifier while jogging |
| D-pad L/R | Previous / next screen |
| D-pad U/D | Select field or axis |
| **A** (green) | Confirm / act |
| **B** (red) | Back / cancel |
| **X** (blue) | Zero the selected axis (confirm required) |
| **Y** (amber) | Cycle jog step size |
| Start | Program start / pause |
| Back | Mode menu |
| Rumble | Soft limit reached, fault raised, step boundary crossed |

### Panel encoder - precision

The gamepad is bad at moving 0.01 mm; a detented encoder is excellent at it.
So the encoder is a classic **MPG**: one detent = one step of the selected
axis at the selected step size. The panel button selects the axis.

This split is the whole point: **coarse and navigation on the pad, precise on
the wheel.** Neither tries to do the other's job.

### Rumble is feedback, never information

A vibration may confirm something you already saw. It must never be the only
indication of anything, because gloves, noise and a put-down controller all
defeat it.

---

## 3. Safety rules for a gamepad on a milling machine

These are not optional and belong in HAL, not in the screen.

1. **Deadman.** `LB` must be held for any jog to occur. The analog jog pins
   are ANDed with the deadman. Let go, motion stops.
2. **Disconnect must stop motion.** A wireless pad that goes flat or out of
   range leaves `hal_input` pins at their last value - which, mid-jog, means
   a stick still deflected. A **watchdog** on the pad's event stream must
   drop the deadman if events stop arriving. Untested assumption until
   proven by pulling the batteries mid-jog, which is a commissioning item.
3. **Deadzone.** Worn sticks do not centre. `halui.joint.jog-deadband` must
   be set above the resting drift of the actual controller, measured.
4. **No E-stop on a button.** E-stop is the hardwired contactor chain
   (ADR-0007). A pad button that *looks* like an E-stop is worse than none,
   because it will be trusted.
5. **Jog scale ramps.** Stick deflection maps to speed non-linearly (squared)
   so small movements are precise and full deflection is a rapid.

---

## 4. Screen map

D-pad left/right moves between screens. The DRO is home and is what the
machine sits on.

```
   [MENU] <- Back button, from anywhere
      |
  DRO <-> JOG <-> RUN <-> PROBE <-> DIAG        ALARM (takes over)
   ^ home
```

**ALARM is not in the carousel.** It takes the whole screen when raised and
cannot be navigated away from until acknowledged - a fault you can flick past
is a fault you will miss.

Every screen keeps:

- **Status bar** (top, 30 px): machine state, homed flags, link health
- **Hint bar** (bottom, 31 px): the controller glyphs that do something
  *here*. Context-sensitive, so nothing has to be memorised.

### Screens

| Screen | Core content |
|---|---|
| **DRO** | Three big axis readouts, work/machine coordinate toggle, feed + spindle, XY envelope map |
| **JOG** | Selected axis enlarged, step size, jog speed, the envelope map with live position |
| **RUN** | Program name, progress arc, line number, elapsed / remaining, tool, overrides |
| **PROBE** | Probe type, Z result, retract state, big confirm |
| **DIAG** | SPI link health, per-axis following error bars, limit states, encoder vs commanded, temps |
| **ALARM** | What failed, which axis, what to do, acknowledge |

---

## 5. Visual design

### Principles

1. **The numbers are the interface.** Everything else is chrome and should
   recede. DRO digits get the largest font the panel has that fits.
2. **Colour means state, never decoration.** Green = ready/ok, amber =
   caution/paused, red = fault, blue = informational, grey = inactive.
3. **Match the physical buttons.** On-screen hints use the Xbox button
   colours: A green, B red, X blue, Y amber. The colour language is already
   in the operator's hand.
4. **Rules, not boxes.** Thin 1 px separators structure the layout; filled
   panels only where something genuinely groups.
5. **Nothing moves unless it means something.** No decorative animation.

### Grid

- 272 x 480, **16 px side margin**, 8 px vertical rhythm
- Status bar 0-29, content 31-448, hint bar 449-479

### Type scale (device fonts, fixed pitch)

| Role | Font | Cell |
|---|---|---|
| DRO value | 6 | 20x40 |
| Secondary value | 3 | 12x24 |
| Axis label | 2 | 10x20 |
| Body / hints | 1 | 8x16 |
| Dense tables | 0 | 6x12 |

### Palette

Chosen to survive RGB565 - the compiler warns when a colour shifts more than
8 per channel, and these do not.

| Token | Hex | Use |
|---|---|---|
| bg | `#0d1117` | background |
| surface | `#161d26` | bars, grouped panels |
| line | `#222c38` | separators |
| line-strong | `#2d3b4e` | section edges |
| text | `#e6edf3` | DRO and primary values |
| muted | `#7d8a99` | labels |
| info | `#8fb4d9` | informational, X button |
| ok | `#5ac57a` | ready, running, A button |
| warn | `#f0a830` | caution, paused, Y button |
| fault | `#e5484d` | faults, B button |
| motion | `#4dd0e1` | live motion, traversed path |

---

## 6. Visualisation - earning its place

Each of these answers a question an operator actually asks. Anything that
does not is left out.

- **XY envelope map.** A plan view of the 300 x 130 table with the tool as a
  dot and the traversed path behind it. Answers "where am I, and am I about
  to run out of table" instantly, which three numbers do not.
- **Z bar.** Vertical scale beside it; height at a glance.
- **Following-error meters.** A thin centre-zero bar per axis that deflects
  with commanded-minus-actual. This is what the belt encoders are *for*, and
  it makes lost motion visible before it is scrap.
- **Spindle tick.** A short rotating mark while the spindle runs - the one
  piece of animation that is purely confirmatory, and it is there because a
  stopped spindle and a running one otherwise look identical on screen.
- **Progress arc.** Program completion, readable from across the shop.
- **Link heartbeat.** A small dot that pulses with each good SPI exchange.
  Stops pulsing the moment comms do.

### How animation works here

The panel is a **115200 baud serial device**: roughly 11.5 KB/s. Redrawing a
full screen at 10 Hz does not fit. So the architecture is:

- **Static chrome** is drawn once, at screen entry
- **Bound widgets** are small named regions redrawn in place

That is not an optimisation, it is the only thing that fits in the bandwidth,
and it is why `ui/dwinui` compiles an SVG into a static op list **plus** a
widget table rather than one flat list.
