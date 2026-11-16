# Pendant node wiring - Waveshare RP2040-Zero to DWIN T5UIC1

The pendant is an Ender 3 V2 display panel driven by a Waveshare RP2040-Zero
over USB CDC to the Pi. HMI only - it is never in the stop path (ADR-0007).

## Board

| | |
|---|---|
| Board | Waveshare RP2040-Zero |
| Runtime | MicroPython 1.29.0 (`WAVESHARE_RP2040_ZERO-20260824-v1.29.0.uf2`) |
| USB serial | `505431651893921C` |
| Flash free | ~1.25 MB after the driver |
| RAM after import | ~196 KB free (driver import costs ~33 KB) |
| Status LED | WS2812 on **GP16** (there is no plain LED on this board) |

**The USB serial is not the BOOTSEL serial.** In BOOTSEL the board enumerates
as mass storage with a different id (`E0C9125B0D9B` here). The one udev needs
is the running one, `505431651893921C`, which equals `machine.unique_id()`.

## Panel connector

10-way IDC on the back of the display PCB:

```
 pin  signal              direction          stock colour
  1   +5V                 power in           black
  2   GND                 power in           white
  3   Encoder A           out to host        grey
  4   Encoder B           out to host        purple
  5   Beeper              in from host       blue
  6   Encoder button      out to host        green
  7   TX   display -> host                   yellow
  8   RX   display <- host                   orange
  9   NC                                     red
 10   NC                                     brown
```

## Corroboration from Marlin, and why the numbering confuses everyone

Marlin's `Marlin/src/pins/stm32f1/pins_CREALITY_V4.h` documents the **board**
side of this same ribbon, with an explicit diagram:

```
   Creality V4 EXP3              with HAS_DWIN_E3V2:
        ------
  PC6  | 1  2 | PB2             3  PB10  USART3 TX  -> panel RX
  PB10 | 3  4 | PB11            4  PB11  USART3 RX  <- panel TX
  PB14   5  6 | PB13            5  PB14  BTN_ENC    (button)
  PB12 | 7  8 | PB15            6  PB13  BEEPER
   GND | 9 10 | 5V              7  PB12  BTN_EN2    (encoder B)
        ------                  8  PB15  BTN_EN1    (encoder A)
```

(`BOARD_LCD_SERIAL_PORT 3` -> USART3 -> PB10/PB11 = EXP3 pins 3 and 4.)

**That is the board numbering. The table above is the panel numbering, and the
two are mirror images** - two IDC headers facing each other through a straight
ribbon. Reverse Marlin's (n -> 11-n) and every one of the ten lines matches,
including which encoder channel is A and which is B.

This mirroring is the reason TX/RX are documented wrongly all over the
internet, and the reason an off-the-shelf adapter in mriscoc/Ender3V2S1 #462
had to be re-pinned. Note it also explains why panel pins 9 and 10 read as
"NC": they are board PC6/PB2, which the DWIN simply does not use.

A third source agrees, in board-end numbering, and is DWIN-specific:
[klipper-dwin-ui](https://github.com/andersevenrud/klipper-dwin-ui) gives
10=5V, 9=GND, 3=RX, 4=TX, 8=A, 7=B, 5=ENT, 6=BEEP, 1-2 unused, and its Pico
GPIO assignments match ours including BEEP on GP5.

Beware when searching: the widely-linked povlhp gist
(`1a5c200d79638afc3c2040f4335d44f1`) and `rfblock/ender3-lcd-arduino` are for
the **old Ender 3 / CR-10 ST7920 12864 LCD**, which uses SID/SCLK/CS on the
same style of 10-pin header. Applying that pinout to a DWIN panel puts SPI
signals where the serial and power lines should be.

## Connections

RP2040-Zero pads are numbered **anticlockwise from the USB connector**
(confirmed against Apache NuttX's board docs): pads 1-3 are 5V / GND / 3V3 at
the USB end of one side rail, and pads 18-23 are GP5..GP0 at the USB end of
the other. So everything we need is two short runs, both nearest the USB end.

| Signal | GPIO | Zero pad | Panel pin |
|---|---|---|---|
| +5V | - | **1** | 1 |
| GND | - | **2** | 2 |
| UART0 TX -> panel RX | GP0 | **23** | 8 |
| UART0 RX <- panel TX | GP1 | **22** | 7 |
| Encoder A | GP2 | **21** | 3 |
| Encoder B | GP3 | **20** | 4 |
| Encoder button | GP4 | **19** | 6 |
| Beeper | GP5 | **18** | 5 |

GP0/GP1 are the RP2040's **default UART0** pins, so no remapping is involved.
The WS2812 status LED is on GP16, which is internal and not brought out to a
pad.

```
 panel 1  (+5V)      <-  5V pad      (pad 1, USB VBUS on the Zero)
 panel 2  (GND)      <-> GND
 panel 3  (enc A)    ->  GP2
 panel 4  (enc B)    ->  GP3
 panel 5  (beeper)   <-  GP5          optional, see below
 panel 6  (button)   ->  GP4
 panel 7  (TX)       ->  GP1          UART0 RX
 panel 8  (RX)       <-  GP0          UART0 TX
```

Panel pin 5 is a **beeper driven by the host** (board PB13 in Marlin).
Audible feedback on a pendant - limit hit, job complete, fault - is genuinely
useful on a machine you are standing beside rather than looking at.

### The beeper does NOT work driven straight from GP5

Measured 2026-11-15. Driving GP5 with PWM produces sound, but it is not a
tone: every edge makes one identical click, and raising the frequency just
delivers clicks faster. Evidence, in the order it was gathered:

- Sweeping 400 Hz - 5 kHz: loudest at the *bottom* of the range, quieter all
  the way up. No resonant peak, which a buzzer always has.
- Sweeping 80 Hz - 800 Hz: still rising toward the bottom. The peak is below
  80 Hz, i.e. there is no peak.
- Duty 3% vs 50% at 200 Hz: barely any difference. Same edge count, very
  different energy - so energy is not what is making the sound.
- 5 Hz and 12 Hz: individually countable ticks, not low pitches.

That is an element being snapped by edge transitions with too little energy
to ring.

**This is usable as-is, and needs no extra hardware.** Clicks fuse into
perceived pitch above roughly 30 Hz, so it does produce notes - just with a
loud bottom end and a weak top. The chime palette therefore lives in
110-440 Hz (`firmware/pendant/chimes.py`) and uses contour and rhythm for
distinction rather than timbre. Writing it at 523-1568 Hz, as the first
version did, put half the set below audibility; that was a design error, not
a hardware fault.

A transistor driver would make it louder and is written up below as an
**optional upgrade**. It is not required.

**Two possible causes, needing opposite fixes.** Distinguish with a meter,
panel unplugged, measuring panel pin 5 to pin 2 (GND):

| Reading | Meaning | Fix |
|---|---|---|
| a few ohms to a few hundred | pin 5 IS the buzzer coil | NPN + 5 V, below |
| ~1 kohm, or very high | panel has its own driver; pin 5 is a logic input | 3.3 V -> 5 V level shift |

The logic-input case is quite likely: the Ender 3 V2 panel is driven from a
5 V mainboard, and a 3.3 V signal into a 5 V-referenced transistor base turns
it on only partially - which looks exactly like this. It is also what this
repo's own note about driving it "via a driver" was pointing at.

If pin 5 is the element directly:

```
  GP5 --[1k]--+ base
               NPN (BC337 / 2N3904 / S8050)
  GND --------+ emitter
  +5V --- buzzer --- collector
          +--|<--+   1N4148 flyback, cathode to +5V (magnetic buzzers only)
```

A magnetic buzzer wants 20-40 mA; an RP2040 GPIO sags above about 12 mA.

Serial crosses over: host TX (GP0) goes to panel **RX, pin 8**; host RX (GP1)
comes from panel **TX, pin 7**.

GPIO assignments are identical to the Pico example - only the power pad name
differs (the Zero has a `5V` castellation where a Pico has VBUS on pin 40).

## Before applying power

- **Panel logic is 3.3 V**, so the RP2040 connects directly with no level
  shifting. The 5 V is for the panel's own supply and backlight only.
- **Do not probe the panel's own shrouded header at all.** Knowing the signal
  order does not tell you which physical end it starts from, and 5 V on a
  signal line destroys the panel.

  Instead, do what `klipper-dwin-ui` recommends: **leave the stock ribbon
  plugged into the display and wire to its other end** - the plug that
  normally goes into the printer's mainboard. That end is the well-documented
  one (Marlin's EXP3 numbering, below), so the ambiguity disappears entirely.

  Then confirm before powering:

  1. Continuity from mainboard-end **hole 9 to the display's GND**, and
     **hole 10 to its VCC**.
  2. Cross-check by plugging the ribbon into the Creality board's EXP3 and
     measuring 5 V with the printer on - a known-good reference.
- The `open_uart` docstring in `dwin-t5uic1` used to point TX/RX at panel pins
  3 and 4, which are the **encoder** lines. Fixed upstream 2026-11-15; if you
  are reading an older checkout, pins 7 and 8 are correct.

## Orientation - measured, not assumed

**Orientation 1, giving a 272x480 PORTRAIT frame.** Determined on the bench by
sweeping all four orientations and asking which read upright with its
top-left marker in the top-left; 1 won, and corner markers at (271, 0) and
(0, 479) landed on-glass with no clipping.

This is the stock CFG default, and it is what the driver's own
`WIDTH=272, HEIGHT=480` already assumed. An earlier guess here had the screens
drawn landscape 480x272, which was wrong.

The firmware MUST call `set_orientation(1)` before drawing.
`machine/wen33013.toml` records it as `node.pendant.orientation = "portrait"`,
and a unit test asserts the TOML and `ui/dwinui` agree - a mismatch draws
everything off-screen and the panel reports nothing.

Portrait suits a DRO anyway: three big axis rows stacked, readable across a
shop.

## Deploying

```bash
# BOOTSEL (hold BOOT while plugging in), then copy the UF2 to RPI-RP2.
python -m mpremote connect port:COM20 fs cp -r dwin_t5uic1 :
python -m mpremote connect port:COM20 fs cp examples/pico_hello.py :pico_hello.py
```

`pico_hello.py` is deliberately **not** installed as `main.py` - nothing
should auto-run and drive an unwired or mis-wired panel. Promote it to
`main.py` only after the wiring above is verified with a meter.

## Verified on hardware (2026-11-15)

- Wiring as above is correct: the panel draws what we send.
- **Handshake succeeds** - two-way comms, so the RX wire and pin 7/8
  orientation are both right. `set_orientation(..., wait_ack=True)` is acked.
- Orientation 1 confirmed upright, 272x480 frame confirmed by corner markers.
- The generated `dro_screen.py` renders on the glass, 24 draw calls.

Getting there needed a driver fix: `protocol.take_response()` trimmed its RX
buffer with `del buffer[:n]` and `buffer.clear()`, neither of which exists on
MicroPython's bytearray, so every read path raised on the first inbound byte.
The symptom - draws fine, never answers - looks exactly like TX/RX swapped,
which is a good reason to test the handshake separately from drawing. Fixed
upstream in `dwin-t5uic1` with a regression test.

Not yet done: encoder and button inputs, the beeper, and anything that talks
to LinuxCNC.
