---
name: latency-check
description: Measure realtime latency on the LinuxCNC Pi under load and record the result, deciding whether the servo period in machine/wen33013.toml is actually achievable. Use before trusting any timing, after a kernel or OS update, and when motion is rough or the machine throws realtime errors.
when_to_use: Run before the first commissioning of any axis, after any apt upgrade on the Pi, and whenever "unexpected realtime delay" appears.
allowed-tools: Bash(ssh *) Bash(python *) Read Edit Write
---

## Latency check on `lcnc`

Latency decides what servo period is honest. A 1 kHz servo thread needs worst
case jitter comfortably under 1,000,000 ns; if latency exceeds the period the
machine throws realtime errors mid-cut, and the first symptom is usually
ruined work rather than an error message.

### Tools

`latency-test` and `latency-histogram` ship with LinuxCNC but are **Tk GUI
apps** - useless on a headless box, and VNC does not currently work on this
Pi. Use `cyclictest`, which is the standard and runs over SSH:

```bash
ssh josh@lcnc 'command -v cyclictest stress-ng'
# if missing:
ssh josh@lcnc 'sudo apt-get install -y rt-tests stress-ng'
```

Note this build is **cyclictest V2.60, which has no `-n` flag** -
`clock_nanosleep` is the default. Passing `-n` makes it print usage and exit,
which looks like a crash.

### Run it

**Idle numbers flatter the machine. Always measure under load.**

```bash
# baseline, 90s
ssh josh@lcnc 'sudo cyclictest -t 1 -p 80 -m -i 1000 -D 90 -q'

# the number that matters: 5 minutes under load
ssh josh@lcnc 'stress-ng --cpu 4 --io 2 --vm 1 --vm-bytes 128M --timeout 310s >/dev/null 2>&1 &
               sleep 3; sudo cyclictest -t 1 -p 80 -m -i 1000 -D 300 -q'
```

`-i 1000` matches the configured 1 kHz servo period deliberately - measure at
the rate you intend to run at, not a convenient one.

### Interpreting

Compare **Max** (microseconds) against `servo_period_ns` / 1000, currently
1000 us:

| Max jitter | Verdict |
|---|---|
| < 100 us | Healthy. 1 kHz is fine. |
| 100-250 us | Usable. Do not raise the servo rate. |
| 250-500 us | Marginal. Investigate before cutting. |
| > 500 us | Do not run the machine. Find the cause. |

### Things that actually move the number

Check these before concluding the hardware is inadequate:

1. **CPU governor.** `ondemand` scales frequency and adds jitter;
   `performance` pins it. Check with
   `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`.
2. **Wrong kernel booted.** The Pi carries both an RT and a stock kernel, and
   an `apt upgrade` can repoint the default. `uname -r` MUST end in `-rt`.
3. **Thermal throttling.** `vcgencmd measure_temp` and
   `vcgencmd get_throttled` - anything but `0x0` invalidates the run.
4. **No CPU isolation.** There is no `isolcpus` in this Pi's cmdline. Worth
   trying if the loaded number is marginal.
5. Anything else sharing the box. This Pi should be doing one job.

### Record it

Write the result to `docs/commissioning/latency.md`: date, kernel version,
governor, **whether it ran under load**, duration, and Min/Avg/Max. A latency
number without its kernel and load condition is not evidence.

If the measured latency cannot support the configured `servo_period_ns`,
change the TOML and `/regen` - do not just hope.
