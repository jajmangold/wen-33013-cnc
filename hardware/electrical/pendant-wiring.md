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

```
 panel 1  (+5V)      <-  5V pad      (USB VBUS on the Zero)
 panel 2  (GND)      <-> GND
 panel 3  (enc A)    ->  GP2
 panel 4  (enc B)    ->  GP3
 panel 5  (beeper)   <-  GP5          optional, see below
 panel 6  (button)   ->  GP4
 panel 7  (TX)       ->  GP1          UART0 RX
 panel 8  (RX)       <-  GP0          UART0 TX
```

Panel pin 5 is a **beeper driven by the host** (board PB13 in Marlin). Not
used by the stock example, but worth wiring: audible feedback on a pendant -
jog detent, limit hit, cycle complete - is genuinely useful on a machine you
are standing beside rather than looking at.

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
- Do not trust the `open_uart` docstring in the `dwin-t5uic1` repo: it says to
  wire TX/RX to panel pins 3 and 4, which are the **encoder** lines. Pins 7
  and 8 are correct, per that repo's own `wiring.md`. Reported upstream.

## Orientation

The stock panel CFG boots **rotated 90 degrees**, presenting the 480x272 LCD
as a **272x480 portrait** frame - which is why the driver defaults to
`WIDTH=272, HEIGHT=480`.

Our screens in `ui/screens/` are designed **landscape 480x272**, so the
pendant firmware MUST call `set_orientation(0)` during startup, before drawing
anything. `machine/wen33013.toml` records this as
`node.pendant.orientation = "landscape"`, and a unit test asserts the compiler
and that setting agree - get this wrong and every element is drawn off-screen
or rotated, with no error reported.

## Deploying

```bash
# BOOTSEL (hold BOOT while plugging in), then copy the UF2 to RPI-RP2.
python -m mpremote connect port:COM20 fs cp -r dwin_t5uic1 :
python -m mpremote connect port:COM20 fs cp examples/pico_hello.py :pico_hello.py
```

`pico_hello.py` is deliberately **not** installed as `main.py` - nothing
should auto-run and drive an unwired or mis-wired panel. Promote it to
`main.py` only after the wiring above is verified with a meter.

## Verified so far

- MicroPython boots, driver imports, protocol frames encode correctly
  (header `0xAA`, correct tail) against the loopback transport.
- **Not yet verified:** anything involving the physical panel. No panel has
  been connected.
