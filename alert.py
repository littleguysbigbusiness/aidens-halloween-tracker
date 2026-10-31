"""Arrival alert — loud/insistent on purpose so it's hard to miss over doorbell
chatter and costumes. Mute state is tracked by the caller (main.py), not here."""

import sys


def beep():
    try:
        if sys.platform == "win32":
            import winsound
            # Three sharp high-pitched beeps rather than one soft tone.
            for _ in range(3):
                winsound.Beep(1500, 180)
        else:
            print("\a\a\a", end="", flush=True)
    except Exception:
        pass
