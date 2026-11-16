"""Pendant node - MicroPython on a Waveshare RP2040-Zero.

Drives the Ender 3 V2 DWIN T5UIC1 panel and reports the encoder to the Pi
over USB CDC. HMI only: this node can ask LinuxCNC for things, and is never
the thing that stops the machine (ADR-0007).

Deploy with /deploy-pendant. Wiring in hardware/electrical/pendant-wiring.md -
read it before applying power; 5 V on a signal line destroys the panel.

NOTE: nothing in this file is covered by the test suite. It cannot be - it
only does anything with a panel attached. Keep the logic here thin and put
anything with a right answer in ui/dwinui, which is tested.
"""

from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.input.quadrature import Quadrature
from dwin_t5uic1.transport import open_uart

# Pin map - see hardware/electrical/pendant-wiring.md.
# Panel pin numbering, NOT the mainboard-end numbering that Marlin documents.
UART_ID = 0
PIN_TX = 0          # -> panel pin 8 (its RX)
PIN_RX = 1          # <- panel pin 7 (its TX)
PIN_ENC_A = 2       # <- panel pin 3
PIN_ENC_B = 3       # <- panel pin 4
PIN_BUTTON = 4      # <- panel pin 6
PIN_BEEP = 5        # -> panel pin 5

# Measured on the real panel: orientation 1 reads upright on this glass,
# giving a 272x480 portrait frame. MUST be applied before drawing or
# everything lands off-screen and the panel reports nothing.
ORIENTATION_PORTRAIT = 1

BACKLIGHT = 0xC0


def open_panel():
    """Bring the panel up in the orientation our screens are drawn for."""
    panel = T5UIC1Display(open_uart(UART_ID, tx=PIN_TX, rx=PIN_RX))
    panel.set_orientation(ORIENTATION_PORTRAIT)
    panel.set_backlight(BACKLIGHT)
    return panel


def draw_screen(panel, module_name="dro_screen"):
    """Replay an exported screen.

    Screens are authored as SVG in ui/screens/ and exported with
    `python -m dwinui export`. Nothing here knows about layout.
    """
    module = __import__(module_name)
    module.draw(panel)


def main():
    panel = open_panel()
    try:
        draw_screen(panel)
    except ImportError:
        # No screen exported yet - prove the link instead of failing silently.
        from dwin_t5uic1 import rgb565
        panel.clear(rgb565(32, 36, 44))
        panel.draw_text(False, True, panel.FONT_8X16,
                        rgb565(255, 176, 0), rgb565(32, 36, 44),
                        8, 8, "no screen exported")

    knob = Quadrature(a=PIN_ENC_A, b=PIN_ENC_B, button=PIN_BUTTON)
    while True:
        delta = knob.read()
        if delta:
            # TODO: forward to the Pi over USB CDC once the host side exists.
            print("enc", delta)


if __name__ == "__main__":
    main()
