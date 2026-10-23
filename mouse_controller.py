"""
mouse_controller.py — Thin wrapper around PyAutoGUI for all mouse actions.

Responsibilities:
  - Move the cursor to a given (x, y) position.
  - Execute left click, right click, double click.
  - Press and release mouse buttons for drag-and-drop.
  - All methods are safe to call from the main loop; they handle PyAutoGUI
    fail-safe disabling internally so accidental corner-touches do not abort
    the application.
"""

import logging

import pyautogui

log = logging.getLogger(__name__)

# Disable PyAutoGUI fail-safe (moving to screen corner would otherwise raise).
# We rely on the ESC key to quit instead.
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0       # Remove built-in inter-call delay for real-time use


class MouseController:
    """Wraps PyAutoGUI mouse operations."""

    def __init__(self):
        self._dragging = False
        log.info("MouseController initialised (FAILSAFE=False, PAUSE=0).")

    # ─────────────────────────────────────────────────────────────────────────
    def move(self, x: int, y: int) -> None:
        """Move cursor to (x, y) without clicking."""
        try:
            pyautogui.moveTo(x, y)
        except Exception as exc:
            log.warning("moveTo failed: %s", exc)

    def left_click(self) -> None:
        try:
            pyautogui.click(button="left")
            log.debug("Left click")
        except Exception as exc:
            log.warning("left_click failed: %s", exc)

    def right_click(self) -> None:
        try:
            pyautogui.click(button="right")
            log.debug("Right click")
        except Exception as exc:
            log.warning("right_click failed: %s", exc)

    def double_click(self) -> None:
        try:
            pyautogui.doubleClick(button="left")
            log.debug("Double click")
        except Exception as exc:
            log.warning("double_click failed: %s", exc)

    # ── Drag ─────────────────────────────────────────────────────────────────
    def start_drag(self) -> None:
        if not self._dragging:
            try:
                pyautogui.mouseDown(button="left")
                self._dragging = True
                log.debug("Mouse button DOWN (drag start)")
            except Exception as exc:
                log.warning("mouseDown failed: %s", exc)

    def end_drag(self) -> None:
        if self._dragging:
            try:
                pyautogui.mouseUp(button="left")
                self._dragging = False
                log.debug("Mouse button UP (drag end)")
            except Exception as exc:
                log.warning("mouseUp failed: %s", exc)

    def force_release(self) -> None:
        """
        Unconditionally release the mouse button.
        Called on hand-loss or application shutdown to prevent a stuck button.
        """
        try:
            pyautogui.mouseUp(button="left")
        except Exception:
            pass
        self._dragging = False
        log.debug("Force release mouse button.")

    @property
    def is_dragging(self) -> bool:
        return self._dragging

    # ── Scroll ───────────────────────────────────────────────────────────────
    def scroll(self, clicks: int) -> None:
        """
        Scroll by `clicks` units.
        Positive = scroll down, negative = scroll up (PyAutoGUI convention).
        """
        if clicks == 0:
            return
        try:
            pyautogui.scroll(-clicks)   # PyAutoGUI: positive = up, negate for intuitive sign
            log.debug("Scroll %d", clicks)
        except Exception as exc:
            log.warning("scroll failed: %s", exc)
