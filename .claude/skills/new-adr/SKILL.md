---
name: new-adr
description: Write an architecture decision record capturing a choice and the evidence behind it, especially what was ruled out and why. Use when a decision closes off an alternative - hardware selection, transport, licensing, or a safety rule.
when_to_use: Any time a choice is made that someone could reasonably revisit later. If the answer to "why isn't this done the obvious way?" is non-trivial, it needs an ADR.
argument-hint: [short-title]
disable-model-invocation: true
allowed-tools: Bash(ls *) Bash(git *) Read Write
---

## New ADR: $1

Existing records:

```!
ls -1 docs/decisions/
```

### Write it

Create `docs/decisions/NNNN-$1.md`, numbering one past the highest above, using
`docs/decisions/template.md`.

### What makes these worth writing

The value is not the decision - it is the **evidence and the discarded
alternatives**. A year from now the question will be "why didn't we just use
Ethernet?", and an ADR that only records the choice answers nothing.

So:

- **Record measurements, with their units and the date.** "SPI runs at 10 MHz
  with zero CRC errors over 30 minutes" beats "SPI is fast enough".
- **Name what was ruled out and the specific reason.** Not "Ethernet was
  considered" but "Ethernet needs a W5500 on each node; the SPI link already
  exists and the Pi 4 can drive it".
- **Record the constraint that forced it**, where there was one - a datasheet
  limit, a license, a physical dimension.
- **Be honest about what is unverified.** If a decision rests on an
  assumption nobody has tested, say so explicitly. That sentence is often the
  most useful one in the file.

### Status values

`Proposed` -> `Accepted` -> later possibly `Superseded by ADR-NNNN`.

Never delete or rewrite an ADR to reflect a new decision. Write a new one and
mark the old superseded - the reasoning that turned out wrong is exactly what
stops it being repeated.

### Finish

- Link it from any code comment or TOML line that depends on it.
- Add a `CHANGELOG.md` line if the decision changes behaviour.
