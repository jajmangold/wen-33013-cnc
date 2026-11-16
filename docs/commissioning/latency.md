# Latency

What the Pi can actually guarantee, measured rather than assumed. A latency
number without its kernel, governor and load condition is not evidence.

## 2026-11-15 - first measurement

| | |
|---|---|
| Host | `lcnc`, Raspberry Pi 4 Model B Rev 1.2, 4 GB |
| Kernel | `6.12.34+rpt-rpi-v8-rt`, `SMP PREEMPT_RT` |
| Tool | `cyclictest` V2.60, `-t 1 -p 80 -m -i 1000` |
| Load | `stress-ng --cpu 4 --io 2 --vm 1 --vm-bytes 128M` |
| Servo period | 1,000,000 ns (1 kHz) |

| Condition | Duration | Min | Avg | **Max** | % of period |
|---|---|---|---|---|---|
| Idle, `ondemand` | 90 s | 4 us | 14 us | **50 us** | 5% |
| Loaded, `ondemand` | 300 s | 5 us | 22 us | **264 us** | 26% |
| Loaded, `performance` | 300 s | 4 us | 22 us | **231 us** | 23% |

Temps 54-56 C after load, `vcgencmd get_throttled` = `0x0` throughout, so no
thermal throttling influenced any run.

## Verdict: 1 kHz is viable

Worst case is **23-26% of the servo period**. That is comfortable *for this
architecture* and would not be for a different one:

- Step generation runs on the **RP2040**, not the Pi. The Pi only has to
  deliver one packet per servo period, and the node buffers it, so jitter
  inside the period is absorbed rather than appearing as misplaced pulses.
- Had we used Pi GPIO step generation, 264 us of jitter at a 53 kHz step rate
  would displace pulses by ~14 steps - visible in the work. ADR-0001 and
  ADR-0002 chose the MCU for latency-independence; this measurement is why
  that mattered.

Do **not** raise the servo rate above 1 kHz on this hardware. At 2 kHz the
same 264 us would be half the period.

## Governor: use `performance`

`ondemand` scales CPU frequency and adds jitter for no benefit on a machine
that does one job. The improvement is modest (264 -> 231 us) but free, and it
removes a variable.

Made persistent by `pi/provision/cpu-governor.service`.

## Idle numbers are worthless here

The idle run was 50 us and the loaded run 264 us - a factor of five. Any
latency figure quoted without saying what else was running should be
discarded, including this file's own idle row, which is kept only to show the
size of the difference.

## Not yet tried

If more margin is ever needed, in order of expected benefit:

1. `isolcpus=3` plus pinning the RT thread - nothing is isolated today.
2. Disabling the serial console (`console=ttyS0,115200` is still in cmdline).
3. Disabling wifi power management, or running wired only.

None of these are needed at present.

## Re-measure after

- any kernel or `apt` upgrade (the Pi carries **both** an RT and a stock
  kernel; an upgrade can repoint the default and `uname -r` must still end
  in `-rt`)
- adding anything else to this Pi
- any change to `servo_period_ns`
