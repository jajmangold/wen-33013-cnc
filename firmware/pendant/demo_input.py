"""Exercise the knob, its button and the beeper.

Everything here is input-side, so it cannot be unit tested - it only means
anything with a hand on the knob. Run it, turn, press, listen.

Run with:
    python -m mpremote connect port:COM20 run firmware/pendant/demo_input.py

Pins (hardware/electrical/pendant-wiring.md):
    GP2 <- panel 3  encoder A
    GP3 <- panel 4  encoder B
    GP4 <- panel 6  encoder button
    GP5 -> panel 5  beeper   PASSIVE - needs a square wave, not a level
"""

import time

import jog_screen as s
from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.input.quadrature import Quadrature
from dwin_t5uic1.transport import open_uart

from machine import PWM, Pin

PIN_ENC_A = 2
PIN_ENC_B = 3
PIN_BUTTON = 4
PIN_BEEP = 5

# The stock Ender 3 V2 knob is 4 quadrature counts per physical detent. Set
# this to 1 and the DRO leaps four steps for every click of the wheel.
DETENT_COUNTS = 4

RUN_SECONDS = 45

# Jog step sizes, cycled by the button - the MPG behaviour the knob is for.
STEPS = (0.001, 0.010, 0.100, 1.000)


class Beeper:
    """Passive buzzer on a PWM pin.

    A passive buzzer makes no sound from a steady level; it needs a square
    wave at an audible frequency. Driving it with a plain high would be
    silent and look like a wiring fault.
    """

    def __init__(self, pin):
        self._pwm = PWM(Pin(pin))
        self._pwm.freq(2400)
        self._pwm.duty_u16(0)

    def tone(self, freq, ms):
        self._pwm.freq(freq)
        self._pwm.duty_u16(16000)       # ~25%, quieter and less harsh than 50%
        time.sleep_ms(ms)
        self._pwm.duty_u16(0)

    def tick(self):
        self.tone(2600, 8)              # one detent: short and dry

    def confirm(self):
        self.tone(1800, 40)             # button: lower, longer

    def limit(self):
        self.tone(500, 160)             # you have run out of travel

    def off(self):
        self._pwm.duty_u16(0)


def main():
    panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=True)
    panel.set_orientation(1)
    panel.set_backlight(0xC0)
    s.draw(panel)
    s.update(panel, 'link', True)
    s.update(panel, 'jog.axis', 'ENC')

    knob = Quadrature(a=PIN_ENC_A, b=PIN_ENC_B, button=PIN_BUTTON,
                      detent_counts=DETENT_COUNTS)
    beeper = Beeper(PIN_BEEP)
    # Three beeps = "go". Without an audible start the operator does not know
    # the window is open, which is exactly how the first run was wasted.
    for _ in range(3):
        beeper.tone(1800, 70)
        time.sleep_ms(90)

    step_index = 1
    position = 0.0
    presses = 0

    s.update(panel, 'jog.step', '%.3f mm' % STEPS[step_index])
    s.update(panel, 'deadman', '   TURN IT')
    print('turn the knob and press it for %ds' % RUN_SECONDS)

    deadline = time.ticks_add(time.ticks_ms(), RUN_SECONDS * 1000)
    last_report = 0

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        delta = knob.take_delta()
        if delta:
            position += delta * STEPS[step_index]
            # Soft limits are real even in a demo: this is the behaviour the
            # machine will have, and the tone is how you notice without
            # looking.
            if position < 0.0 or position > 298.0:
                position = 0.0 if position < 0.0 else 298.0
                beeper.limit()
            else:
                beeper.tick()
            s.update(panel, 'jog.value', '%8.3f' % position)
            s.update(panel, 'jog.rate', '%+3d det' % delta)
            s.update(panel, 'map.z', position * 0.5)

        if knob.pressed():
            presses += 1
            step_index = (step_index + 1) % len(STEPS)
            beeper.confirm()
            s.update(panel, 'jog.step', '%.3f mm' % STEPS[step_index])
            s.update(panel, 'deadman', ' PRESS %2d' % presses)
            print('press', presses, '-> step', STEPS[step_index])

        now = time.ticks_ms()
        if time.ticks_diff(now, last_report) > 1000:
            last_report = now
            s.update(panel, 'jog.headroom', '%6.1f mm' % (298.0 - position))

        time.sleep_ms(5)

    beeper.off()
    print('')
    print('counts seen   :', knob.position())
    print('button presses:', presses)
    print('diagnostics   :', knob.diagnostics())


main()
