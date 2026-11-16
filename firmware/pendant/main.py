"""Pendant node - runs on every power-up.

Draws the DRO chrome immediately and sits in standby until the host takes
over. Deliberately minimal: a blank panel is indistinguishable from a dead
one, so the board's first duty is to prove it is alive and that the link to
the glass works. It does NOT invent machine state - the zeros are clearly
zeros and the status says NO HOST, because a pendant showing plausible
numbers that nothing is measuring is worse than one showing none.

The host (LinuxCNC on the Pi) interrupts this over the USB REPL and drives
the same widgets, so there is no screen transition when it connects - the
NO HOST text simply becomes a machine state.

HMI only: this node can ask for things and can never be the thing that stops
the machine (ADR-0007).

Nothing here is covered by the test suite. It cannot be - it only does
anything with a panel attached. Keep it thin; anything with a right answer
belongs in ui/dwinui, which is tested.
"""

import time

import dro_screen as s
from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.transport import open_uart

# See hardware/electrical/pendant-wiring.md. Panel pin numbering.
UART_ID = 0
PIN_TX = 0          # -> panel pin 8 (its RX)
PIN_RX = 1          # <- panel pin 7 (its TX)

# The stock CFG boots rotated; our screens are drawn for orientation 1,
# giving a 272x480 portrait frame. Measured, not assumed. Remove this and
# everything lands off-screen with no error reported.
ORIENTATION = 1

BACKLIGHT = 0xC0

# Slow enough to read as "alive", not as something demanding attention.
HEARTBEAT_MS = 1000


def open_panel():
    panel = T5UIC1Display(open_uart(UART_ID, tx=PIN_TX, rx=PIN_RX),
                          handshake=True)
    panel.set_orientation(ORIENTATION)
    panel.set_backlight(BACKLIGHT)
    return panel


def standby(panel):
    """Chrome, honest zeros, and a heartbeat."""
    s.draw(panel)
    s.update(panel, 'link', False)
    s.update(panel, 'wcs', '--- ')
    for name in ('homed.x', 'homed.y', 'homed.z'):
        s.update(panel, name, False)
    for name in ('dro.x', 'dro.y', 'dro.z'):
        s.update(panel, name, '   -----')
    s.update(panel, 'feed', '    - mm/min')
    s.update(panel, 'spindle', '    - rpm')
    s.update(panel, 'spindle.run', False)

    # A cycling ellipsis distinguishes "alive and waiting" from "frozen",
    # which a static NO HOST cannot. One update a second is nothing on an
    # 11.5 KB/s link.
    phase = 0
    while True:
        s.update(panel, 'state', 'NO HOST' + ('.' * phase) + (' ' * (3 - phase)))
        phase = (phase + 1) % 4
        time.sleep_ms(HEARTBEAT_MS)


def main():
    try:
        panel = open_panel()
    except Exception as exc:                 # noqa: BLE001
        # No panel, or it is not answering. Say so on the USB console rather
        # than failing silently - this is the message someone will be looking
        # for when the screen is dark.
        print('pendant: panel did not come up:', exc)
        print('check wiring: GP0 -> panel pin 8, GP1 <- panel pin 7, 5V, GND')
        return
    standby(panel)


main()
