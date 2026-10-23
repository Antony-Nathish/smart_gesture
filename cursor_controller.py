"""
cursor_controller.py — Maps normalised hand coordinates to screen coordinates
and applies smoothing, dead-zone, and adaptive filtering.

Responsibilities:
  - Accept a normalised (0-1) cursor position from the gesture detector.
  - Map the configured active region of the camera to the full screen.
  - Apply exponential smoothing with adaptive fast-catch-up on large jumps.
  - Enforce a dead zone to suppress micro-jitter when the hand is nearly still.
  - Return the filtered (x, y) screen pixel position ready for mouse control.
"""

import logging
import math
from typing import Optional, Tuple

import pyautogui

import config

log = logging.getLogger(__name__)

# Fetch screen dimensions once at import time
SCREEN_W, SCREEN_H = pyautogui.size()


def _map_to_screen(norm_x: float, norm_y: float) -> Tuple[float, float]:
    """
    Map a normalised coordinate (0-1) inside the active camera region to
    screen pixel coordinates.

    The camera frame is mirrored horizontally (flip_x=True) so movement feels
    natural — moving your hand right moves the cursor right.
    """
    ax1 = config.ACTIVE_REGION_X1
    ax2 = config.ACTIVE_REGION_X2
    ay1 = config.ACTIVE_REGION_Y1
    ay2 = config.ACTIVE_REGION_Y2

    # Flip x so camera mirror feels natural
    flipped_x = 1.0 - norm_x

    # Clamp within active region, then remap to [0, 1]
    rx = (flipped_x - ax1) / (ax2 - ax1)
    ry = (norm_y    - ay1) / (ay2 - ay1)
    rx = max(0.0, min(1.0, rx))
    ry = max(0.0, min(1.0, ry))

    sx = rx * SCREEN_W
    sy = ry * SCREEN_H
    return sx, sy


class CursorController:
    """
    Converts raw normalised hand positions into smooth, stable screen coordinates.

    Call update(norm_x, norm_y) each frame.
    Returns the filtered (screen_x, screen_y) tuple.
    """

    def __init__(self):
        self._smooth_x: Optional[float] = None
        self._smooth_y: Optional[float] = None
        log.info("CursorController initialised (screen=%dx%d, smoothing=%.2f)",
                 SCREEN_W, SCREEN_H, config.CURSOR_SMOOTHING)

    # ─────────────────────────────────────────────────────────────────────────
    def update(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        Accept a raw normalised position and return a smoothed screen position.

        Algorithm:
          1. Map active-region coords → screen pixels.
          2. On first call, initialise the filter.
          3. Compute the raw jump distance in screen pixels.
          4. If jump > CURSOR_JUMP_THRESHOLD → use fast smoothing to catch up.
             Otherwise → use the normal smoothing factor.
          5. Apply exponential moving average.
          6. Apply dead zone: if movement is tiny, hold the previous position.
        """
        raw_sx, raw_sy = _map_to_screen(norm_x, norm_y)

        # First frame: seed the filter directly
        if self._smooth_x is None:
            self._smooth_x = raw_sx
            self._smooth_y = raw_sy
            return int(raw_sx), int(raw_sy)

        # Distance of raw jump in screen pixels
        dx = raw_sx - self._smooth_x
        dy = raw_sy - self._smooth_y
        dist = math.hypot(dx, dy)

        # Choose smoothing factor
        if dist > config.CURSOR_JUMP_THRESHOLD:
            alpha = 1.0 - config.CURSOR_JUMP_SMOOTHING   # fast catch-up
        else:
            alpha = 1.0 - config.CURSOR_SMOOTHING        # normal smoothing

        # Exponential moving average
        new_x = self._smooth_x + alpha * dx
        new_y = self._smooth_y + alpha * dy

        # Dead zone: ignore very small movements
        if abs(new_x - self._smooth_x) < config.CURSOR_DEAD_ZONE and \
           abs(new_y - self._smooth_y) < config.CURSOR_DEAD_ZONE:
            return int(self._smooth_x), int(self._smooth_y)

        self._smooth_x = new_x
        self._smooth_y = new_y
        return int(new_x), int(new_y)

    def reset(self):
        """Re-seed the filter on next frame (call after hand-loss recovery)."""
        self._smooth_x = None
        self._smooth_y = None

    @property
    def current_position(self) -> Optional[Tuple[int, int]]:
        if self._smooth_x is None:
            return None
        return int(self._smooth_x), int(self._smooth_y)
