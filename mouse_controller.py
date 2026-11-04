"""
mouse_controller.py
-------------------
Thin OS-mouse wrapper around PyAutoGUI.

Centralising mouse interactions here keeps gesture logic free of any
platform-specific quirks and makes the system easier to swap to another
backend (e.g. pynput) later.
"""

import pyautogui


class MouseController:
    """Wrapper around PyAutoGUI providing safe, low-latency mouse actions."""

    def __init__(self, failsafe=True):
        # FAILSAFE: jerk the cursor to a screen corner to abort if something
        # goes wrong. Keep it on by default - it has saved many demos.
        pyautogui.FAILSAFE = failsafe
        pyautogui.PAUSE = 0  # Disable PyAutoGUI's built-in delay
        self.screen_w, self.screen_h = pyautogui.size()

    # ---------------------------------------------------------- Movement ---
    def move(self, x, y):
        """Move the cursor to absolute screen coordinates (clamped to bounds)."""
        x = max(0, min(self.screen_w - 1, int(x)))
        y = max(0, min(self.screen_h - 1, int(y)))
        try:
            pyautogui.moveTo(x, y, _pause=False)
        except pyautogui.FailSafeException:
            # Surfaced for the caller; we deliberately don't re-raise so a
            # corner overshoot doesn't crash the whole loop.
            print("[MouseController] FailSafe triggered (cursor at corner).")

    # ------------------------------------------------------------ Clicks ---
    def click(self):
        pyautogui.click(_pause=False)

    def right_click(self):
        pyautogui.rightClick(_pause=False)

    def double_click(self):
        pyautogui.doubleClick(_pause=False)

    # ------------------------------------------------ Drag (manual hold) ---
    def mouse_down(self):
        pyautogui.mouseDown(_pause=False)

    def mouse_up(self):
        pyautogui.mouseUp(_pause=False)

    # ------------------------------------------------------------ Scroll ---
    def scroll(self, amount):
        """Vertical scroll. Positive = up, negative = down."""
        if amount == 0:
            return
        pyautogui.scroll(int(amount), _pause=False)
