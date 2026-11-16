"""Pendant bring-up diagnostic - run this before trusting anything.

Tests the link in a deliberate order, so a failure says WHICH thing is wrong
rather than just "no picture":

  1. UART opens at all
  2. Panel ANSWERS (handshake) - proves RX works, not just TX
  3. Orientation can be set and acknowledged
  4. Something visible actually lands on the glass

A black-but-backlit panel is the classic symptom of TX/RX swapped: the panel
powers up and lights its backlight from the 5 V rail regardless of whether it
ever receives a byte.

Run with:  python -m mpremote connect port:COM20 run firmware/pendant/diagnose.py
"""

from dwin_t5uic1 import T5UIC1Display, rgb565
from dwin_t5uic1.transport import open_uart

UART_ID = 0
PIN_TX = 0      # GP0 -> panel pin 8 (its RX)
PIN_RX = 1      # GP1 <- panel pin 7 (its TX)

RED = rgb565(255, 0, 0)
WHITE = rgb565(255, 255, 255)
BLACK = rgb565(0, 0, 0)


def step(n, what):
    print("[%d] %s ... " % (n, what), end="")


def main():
    step(1, "open UART0 on GP0/GP1 @115200")
    uart = open_uart(UART_ID, tx=PIN_TX, rx=PIN_RX)
    print("ok")

    step(2, "handshake (proves the panel is TALKING BACK)")
    panel = T5UIC1Display(uart, handshake=False)
    try:
        panel.handshake(timeout=2.0)
        print("ok - two-way comms confirmed")
        two_way = True
    except Exception as exc:                      # noqa: BLE001 - report, don't raise
        print("FAILED: %r" % (exc,))
        print("    The panel is not answering. Most likely, in order:")
        print("    - TX/RX swapped: GP0 must go to panel pin 8, GP1 to pin 7")
        print("    - RX wire not actually connected (TX-only looks identical")
        print("      until you try to read)")
        print("    - panel not getting 5 V on pin 1 / GND on pin 2")
        print("    Continuing anyway - a blind write may still show something.")
        two_way = False

    step(3, "backlight on")
    panel.set_backlight(0xC0)
    print("sent")

    step(4, "orientation -> landscape (0)")
    try:
        panel.set_orientation(0, wait_ack=two_way, timeout=2.0)
        print("ok")
    except Exception as exc:                      # noqa: BLE001
        print("no ack: %r" % (exc,))

    step(5, "fill the screen RED")
    panel.clear(RED)
    print("sent")

    step(6, "draw text")
    panel.draw_text(False, True, panel.FONT_16X32, WHITE, RED, 20, 20, "PENDANT OK")
    panel.draw_text(False, True, panel.FONT_8X16, WHITE, RED, 20, 70,
                    "if you can read this, TX works")
    print("sent")

    print("")
    print("RESULT: handshake=%s" % ("OK" if two_way else "FAILED"))
    print("Look at the panel:")
    print("  red screen + text  -> link is good")
    print("  still black        -> TX is not reaching the panel")
    print("  garbage/stripes    -> baud or framing wrong")
    print("Panel frame is %dx%d" % (panel.WIDTH, panel.HEIGHT))


main()
