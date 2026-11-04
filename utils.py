"""
utils.py
--------
Small, dependency-light helpers shared across modules:
    * FPSCounter   - rolling FPS estimator
    * draw_hud     - on-screen heads-up display (FPS, current action, etc.)
    * put_text     - text with a thin shadow for legibility
    * euclidean    - 2D Euclidean distance
"""

import math
import time

import cv2


def euclidean(p1, p2):
    """Euclidean distance between two 2D points (tuples or lists)."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def put_text(img, text, org, scale=0.7, color=(255, 255, 255), thickness=2):
    """Render text with a black drop-shadow for readability on any backdrop."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, (org[0] + 2, org[1] + 2), font, scale,
                (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, color, thickness, cv2.LINE_AA)


class FPSCounter:
    """Smoothed frames-per-second counter using exponential averaging."""

    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.fps = 0.0
        self._prev = time.time()

    def update(self):
        """Call once per frame; returns the smoothed FPS value."""
        now = time.time()
        dt = now - self._prev
        self._prev = now
        if dt > 0:
            instant = 1.0 / dt
            # Exponential moving average
            self.fps = (1 - self.alpha) * self.fps + self.alpha * instant
        return self.fps


def draw_hud(frame, fps=None, action=None, state=None,
             active_area=None, color=(0, 255, 0)):
    """Draw a heads-up display on the given frame.

    Parameters
    ----------
    frame : np.ndarray
        Image to draw on (modified in place).
    fps : float | None
        Frames-per-second to display. None hides it.
    action : str | None
        Last action name (e.g. "Click", "Dragging").
    state : str | None
        Current gesture state (e.g. "IDLE", "CURSOR").
    active_area : tuple | None
        (x1, y1, x2, y2) rectangle of the cursor-active region. None hides it.
    color : tuple
        Default text colour.
    """
    h, w = frame.shape[:2]

    # Translucent header strip for legibility
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 70), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    if fps is not None:
        put_text(frame, f"FPS: {fps:5.1f}", (10, 28), 0.7, color, 2)
    if action is not None:
        put_text(frame, f"Action: {action}", (10, 58), 0.7, (0, 255, 255), 2)
    if state is not None:
        put_text(frame, f"State: {state}", (w - 230, 28), 0.7, (255, 200, 0), 2)

    if active_area is not None:
        x1, y1, x2, y2 = active_area
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
