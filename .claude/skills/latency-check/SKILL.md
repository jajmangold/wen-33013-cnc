---
name: latency-check
description: Measure realtime latency on the LinuxCNC Pi and record the result, deciding whether the servo period in machine/wen33013.toml is actually achievable. Use before trusting any timing, after a kernel or OS update, and when motion is rough or the machine throws realtime errors.
when_to_use: Run before the first commissioning of any axis, after any apt upgrade on the Pi, and whenever "unexpected realtime delay" appears.
allowed-tools: Bash(ssh *) Bash(make *) Read Edit Write
---

## Latency check on `lcnc`

Latency decides what servo period is honest. A 1 kHz servo thread needs worst
case jitter comfortably under 1000000 ns; if latency exceeds the period the
machine will throw realtime errors mid-cut, and the usual first symptom is
ruined work rather than an error message.

### Run it

Over SSH, headless:

```bash
ssh josh@lcnc 'latency-test --help 2>&1 | head -3'
```

`latency-histogram` and `latency-test` want a GUI. Headless, prefer:

```bash
ssh josh@lcnc 'sudo cyclictest -t1 -p 80 -n -i 1000 -l 300000 -q'
```

Run it for at least five minutes, and **run it under load** - an idle box
flatters itself. In a second session:

```bash
ssh josh@lcnc 'stress-ng --cpu 4 --io 2 --vm 1 --timeout 300s'
```

### Interpreting the result

Compare `Max` jitter in ns against `servo_period_ns` (currently 1000000):

| Max jitter | Verdict |
|---|---|
| < 100 us | Healthy. 1 kHz servo thread is fine. |
| 100-250 us | Usable. Keep 1 kHz, but do not raise it. |
| 250-500 us | Marginal. Investigate before cutting anything. |
| > 500 us | Do not run the machine. Find the cause. |

### If it is bad

Check in this order:

1. **Wrong kernel booted.** The Pi has both an RT and a stock kernel
   installed; an `apt upgrade` can repoint the default. Confirm:
   `ssh josh@lcnc uname -r` must end in `-rt`.
2. GPU/firmware contention, wifi power management, USB polling.
3. Anything else sharing the box - this Pi should be doing one job.

### Record it

Write the result to `docs/commissioning/latency.md` with the date, kernel
version, whether it ran under load, and the max jitter. A latency number
without its kernel version and load condition is not evidence.

If the measured latency cannot support the configured `servo_period_ns`,
change the TOML and `/regen` - do not just hope.
