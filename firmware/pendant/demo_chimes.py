"""Audition every chime, with its name on the panel.

Plays each in turn so they can be judged as a set rather than one at a time -
the thing that matters is whether you can tell them apart without looking,
and whether any of them would irritate after the hundredth time.

Run with:
    python -m mpremote connect port:COM20 run firmware/pendant/demo_chimes.py
"""

import time

import jog_screen as s
from chimes import CATEGORY, CHIMES, DEFAULT_ON, Chimes
from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.transport import open_uart

PIN_BEEP = 5

# Audition order: routine first, then state changes, then the ones that want
# your attention. Judged in this order you hear the dynamic range.
ORDER = (
    'tick', 'confirm', 'cancel',
    'ready', 'homed', 'start', 'pause', 'resume', 'probe',
    'complete', 'toolchange',
    'limit', 'fault', 'linklost',
)

# The phrase each chime is written to scan like. Shown while it plays so you
# can hear whether the rhythm matches the words.
SAYS = {
    'tick': '(click)',
    'confirm': 'o-KAY',
    'cancel': 'CAN-cel',
    'ready': 'REA-dy',
    'homed': 'all HOMED',
    'start': 'a-WAY',
    'pause': 'PAUS-ed',
    'resume': 're-SUME',
    'probe': 'touch',
    'complete': 'job com-PLETE',
    'toolchange': 'TOOL CHANGE x2',
    'limit': 'LIM-it',
    'fault': 'FAULT FAULT FAULT',
    'linklost': 'LINK LOST',
}

WHAT = {
    'tick': 'encoder detent',
    'confirm': 'button press',
    'cancel': 'back / dismissed',
    'ready': 'pendant booted',
    'homed': 'homing finished',
    'start': 'program started',
    'pause': 'program paused',
    'resume': 'program resumed',
    'probe': 'probe contact',
    'complete': 'JOB COMPLETE',
    'toolchange': 'tool change due',
    'limit': 'soft limit hit',
    'fault': 'FAULT',
    'linklost': 'comms lost',
}


def main():
    panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=True)
    panel.set_orientation(1)
    panel.set_backlight(0xC0)
    s.draw(panel)
    s.update(panel, 'link', True)
    s.update(panel, 'jog.axis', 'SND')

    # Audition EVERYTHING, including the ones that are off by default, so
    # the policy can be judged by ear rather than taken on trust.
    buzzer = Chimes(PIN_BEEP, categories=('attention', 'state', 'confirm'))
    policy = Chimes(PIN_BEEP, muted=True)      # default policy, for reporting

    s.update(panel, 'deadman', '   READY?')
    print('starting in 3s - the name appears on the panel before each sound')
    time.sleep_ms(3000)

    # Long enough to judge each sound on its own rather than as a run-on
    # sequence, with a longer break where the category changes so the step
    # from routine to attention is obvious.
    GAP_MS = 2000
    CATEGORY_GAP_MS = 3500

    previous_category = None
    for name in ORDER:
        category = CATEGORY[name]
        if previous_category is not None and category != previous_category:
            print('--- %s ---' % category)
            time.sleep_ms(CATEGORY_GAP_MS)
        previous_category = category

        # MicroPython's str has no rjust/ljust - pad by hand.
        label = name[:8]
        s.update(panel, 'jog.value', ' ' * (8 - len(label)) + label)
        s.update(panel, 'jog.step', SAYS[name][:10])
        s.update(panel, 'deadman', '  LISTEN')
        on = 'ON ' if policy.allows(name) else 'off'
        print('%-11s %-9s %s  %-18s %s'
              % (name, CATEGORY[name], on, '"' + SAYS[name] + '"', WHAT[name]))

        buzzer.play(name)
        # Serviced from a loop, exactly as the real pendant will do it, so
        # this also proves the sequencer does not block.
        while buzzer.busy:
            buzzer.service()
            time.sleep_ms(2)
        time.sleep_ms(GAP_MS)

    s.update(panel, 'jog.value', '    done')
    s.update(panel, 'deadman', '  HOLD LB')
    enabled = [n for n in CHIMES if policy.allows(n)]
    print('')
    print('%d chimes, %d on by default (%s)'
          % (len(CHIMES), len(enabled), ', '.join(DEFAULT_ON)))
    print('silent by default:', ', '.join(n for n in CHIMES if not policy.allows(n)))


main()
