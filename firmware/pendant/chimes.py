"""Chimes for the pendant buzzer.

The governing test for every sound here:

    Does it tell you something you CANNOT already see?

A chime that confirms an action you just took, while looking at a screen that
already changed, is pure noise - and noise is what gets a buzzer unplugged
within a week. So the confirmation sounds exist but are **off by default**,
and only the ones that reach you when you are not looking are enabled.

Hence the categories below. `ATTENTION` and `STATE` are on; `CONFIRM` is off
unless something turns it on.

Other rules:

1. **Short.** Everything under 150 ms except the two that want you to look
   up: COMPLETE and FAULT.
2. **A consistent language.** Rising = something good finished. Falling =
   something stopped. Repeated and dissonant = something is wrong. You
   should be able to tell them apart from across the shop without learning
   a manual.
3. **Pentatonic.** Notes come from C major pentatonic, so any two of them
   sound fine together and nothing lands on a minor second. This is what
   keeps it from sounding like a cheap toy.
4. **Non-blocking.** `play()` returns immediately and `service()` advances
   the sequence. A blocking chime inside a jog loop makes the encoder feel
   broken, which is a worse problem than having no sound at all.

The buzzer is PASSIVE: it needs a square wave, not a level. Driving the pin
high is silent and looks exactly like a wiring fault.
"""

import time

from machine import PWM, Pin

# Pitches chosen for THIS element, measured 2026-11-15.
#
# It is not a resonant buzzer. Each edge produces one click; above ~30 Hz the
# clicks fuse and you hear a pitch, but amplitude falls steadily with
# frequency because a faster click train carries no more energy. Measured
# loudest at the bottom of the range and quieter all the way up.
#
# So the whole palette lives in 110-440 Hz where it is actually loud, and
# distinction comes from CONTOUR and RHYTHM rather than timbre. Writing it at
# 523-1568 Hz, as the first version did, put half the set below audibility.
#
# Low notes also need longer tones: one cycle at 110 Hz is 9 ms, so a 30 ms
# blip is three cycles and reads as a thud rather than a note.
REST = 0
A2, C3, D3, E3, G3 = 110, 131, 147, 165, 196
A3, C4, D4, E4, G4, A4 = 220, 262, 294, 330, 392, 440

# name -> ((freq_hz, duration_ms), ...)
# Each chime is written to the RHYTHM AND STRESS of the words it stands for.
#
# People recognise speech rhythm far faster than they identify a pitch, so a
# cue that scans like its phrase is recognisable before you have consciously
# worked out which one it was. The grammar:
#
#   trochee  STRONG-weak   "LIM-it"   long high -> short low   (falling)
#   iamb     weak-STRONG   "com-PLETE" short low -> long high  (rising)
#   spondee  STRONG-STRONG "TOOL CHANGE" two equal, insistent
#
# English statements fall at the end, so falling reads as finality - which is
# why "stopped" things fall and "finished well" things rise.
CHIMES = {
    # --- feedback, heard constantly, so kept tiny ---
    'tick':      ((G4, 12),),                        # a click, not a word
    'confirm':   ((E4, 45), (A4, 60)),               # "o-KAY"      iamb
    'cancel':    ((E3, 90), (C3, 60)),               # "CAN-cel"    trochee

    # --- state changes, heard occasionally ---
    'ready':     ((E4, 100), (C4, 70)),              # "REA-dy"     trochee
    'homed':     ((C4, 70), (G4, 160)),              # "all HOMED"  iamb
    'start':     ((D4, 70), (G4, 120)),              # "a-WAY"      iamb
    'pause':     ((D4, 90), (A3, 190)),              # "PAUS-ed"    falling
    'resume':    ((C4, 90), (G4, 150)),              # "re-SUME"    iamb

    'probe':     ((E4, 35),),                        # "touch"      one beat

    # --- look up ---
    'complete':  ((C4, 80), (E4, 80), (A4, 240)),    # "job com-PLETE"
    # "TOOL CHANGE", said twice. Two equal stresses, then a pause, then
    # again - the rhythm of someone repeating themselves to be heard.
    'toolchange': ((D4, 120), (REST, 60), (D4, 120), (REST, 170),
                   (D4, 120), (REST, 60), (D4, 120)),

    # --- something is wrong ---
    # Lowest notes in the set: these two MUST cut through, and A2 is where
    # this element is loudest.
    'limit':     ((D3, 150), (A2, 110)),             # "LIM-it"     trochee
    # "FAULT. FAULT. FAULT." One hard syllable, repeated, not a melody.
    'fault':     ((A2, 160), (REST, 80), (A2, 160), (REST, 80), (A2, 220)),
    'linklost':  ((G3, 110), (D3, 200)),             # "LINK LOST"  falling
}

# Why each sound exists. This is the policy, not decoration.
ATTENTION = 'attention'   # the machine needs you and you may be elsewhere
STATE = 'state'           # something changed that you did not personally do
CONFIRM = 'confirm'       # confirms an action you just took and can see

CATEGORY = {
    'complete':   ATTENTION,   # job done, you are across the shop
    'fault':      ATTENTION,   # something broke
    'toolchange': ATTENTION,   # the machine is stopped, waiting for you
    'limit':      ATTENTION,   # hit while jogging, eyes on the work not the screen
    'linklost':   ATTENTION,   # motion may have stopped and the screen may be stale
    'probe':      ATTENTION,   # contact, at the instant it happens

    'homed':      STATE,       # ready, without walking over to look
    'pause':      STATE,       # often NOT you: an M0, or a fault-triggered hold
    'ready':      STATE,       # once per power cycle

    'tick':       CONFIRM,     # the knob already has a physical detent you feel
    'confirm':    CONFIRM,     # the screen already changed
    'cancel':     CONFIRM,
    'start':      CONFIRM,     # you pressed the button; you know
    'resume':     CONFIRM,
}

# Default policy: anything that merely confirms what you can already see is
# silent. Turn CONFIRM on deliberately - it is useful while bench-testing the
# encoder, and tiresome on a machine.
DEFAULT_ON = (ATTENTION, STATE)


class Chimes:
    """Non-blocking buzzer sequencer.

    Call `service()` from the main loop. A new `play()` pre-empts whatever is
    sounding: the most recent event is always the one worth hearing, and
    queueing them would mean a fault waiting behind a detent tick.
    """

    # 25% duty is noticeably softer than 50% on these buzzers and much less
    # fatiguing in a quiet workshop.
    DUTY = 16000

    def __init__(self, pin, muted=False, categories=DEFAULT_ON):
        self._pwm = PWM(Pin(pin))
        self._pwm.freq(2400)
        self._pwm.duty_u16(0)
        self.muted = muted
        self.categories = set(categories)
        self._seq = ()
        self._index = 0
        self._next_at = 0

    def allows(self, name):
        """Is this sound useful enough to make, under the current policy?"""
        return CATEGORY.get(name, CONFIRM) in self.categories

    def play(self, name):
        """Start a chime, if policy allows it. Returns immediately."""
        if self.muted or not self.allows(name):
            return False
        seq = CHIMES.get(name)
        if not seq:
            return False
        self._seq = seq
        self._index = 0
        self._next_at = time.ticks_ms()
        self.service()
        return True

    def service(self):
        """Advance the sequence. Call often; cheap when idle."""
        if not self._seq:
            return False
        now = time.ticks_ms()
        if time.ticks_diff(now, self._next_at) < 0:
            return True

        if self._index >= len(self._seq):
            self._pwm.duty_u16(0)
            self._seq = ()
            return False

        freq, ms = self._seq[self._index]
        if freq == REST:
            self._pwm.duty_u16(0)
        else:
            self._pwm.freq(freq)
            self._pwm.duty_u16(self.DUTY)
        self._index += 1
        self._next_at = time.ticks_add(now, ms)
        return True

    @property
    def busy(self):
        return bool(self._seq)

    def stop(self):
        self._seq = ()
        self._pwm.duty_u16(0)

    def mute(self, on=True):
        self.muted = on
        if on:
            self.stop()
