"""
gesture_controller.py
---------------------
The "brain" of the system: takes raw hand landmarks each frame, decides
which gesture is currently active, and drives the MouseController
accordingly.

Designed as a finite state machine so behaviours like
    pinch-and-hold -> drag    vs    quick-pinch -> click
work without juggling flags scattered through the code.

State diagram
=============

        +----------+   index up only        +----------+
        |   IDLE   |----------------------> |  CURSOR  |
        +----------+ <--------------------- +----------+
             | ^                                  |
             | | release                          |  pinch
             | +----------------------------------+
             v
       +-----------+   held > DRAG_HOLD_TIME   +-----------+
       | PINCH_DWN |--------------------------> | DRAGGING |
       +-----------+                            +-----------+
            | release (quick)                       |
            v                                       | release
        emits CLICK                                 v
                                                emits DROP

        +-----------+
        | SCROLLING |  (index + middle up; vertical motion drives scroll)
        +-----------+
"""

import time

import numpy as np

import config
from hand_tracker import HandTracker
from utils import euclidean


class GestureController:
    """Translate hand landmarks into mouse actions through a small state machine."""

    # Public state constants (also used for the on-screen badge).
    STATE_IDLE = "IDLE"
    STATE_CURSOR = "CURSOR"
    STATE_PINCH_DOWN = "PINCH"
    STATE_DRAGGING = "DRAG"
    STATE_SCROLLING = "SCROLL"

    def __init__(self, mouse, cam_w, cam_h):
        self.mouse = mouse
        self.cam_w = cam_w
        self.cam_h = cam_h
        self.screen_w = mouse.screen_w
        self.screen_h = mouse.screen_h

        # Gesture state machine
        self.state = self.STATE_IDLE
        self._pinch_start_time = None
        self._last_click_time = 0.0
        self._last_right_click_time = 0.0
        self._scroll_anchor_y = None

        # Smoothing state (None -> not yet initialised)
        self._smooth_x = None
        self._smooth_y = None

        # Diagnostics for the HUD
        self.last_action = "Idle"

    # =====================================================================
    #                       Finger / gesture detection
    # =====================================================================
    @staticmethod
    def _fingers_up(landmarks):
        """Return [thumb, index, middle, ring, pinky] booleans (1 = extended).

        Uses a simple but robust heuristic:
            * Thumb is "up" if its tip is far enough from the index MCP.
            * Other fingers are "up" if the tip's y is above the PIP joint
              (note: image y grows downwards).
        """
        # Thumb (uses Euclidean distance to be orientation-tolerant)
        thumb_dist = euclidean(landmarks[HandTracker.THUMB_TIP],
                               landmarks[HandTracker.INDEX_MCP])
        thumb_up = 1 if thumb_dist > config.THUMB_EXTENDED_DISTANCE else 0

        fingers = [thumb_up]
        for tip, pip in [(HandTracker.INDEX_TIP, HandTracker.INDEX_PIP),
                         (HandTracker.MIDDLE_TIP, HandTracker.MIDDLE_PIP),
                         (HandTracker.RING_TIP, HandTracker.RING_PIP),
                         (HandTracker.PINKY_TIP, HandTracker.PINKY_PIP)]:
            fingers.append(1 if landmarks[tip][1] < landmarks[pip][1] else 0)
        return fingers

    # =====================================================================
    #                          Coordinate mapping
    # =====================================================================
    def _map_to_screen(self, x, y):
        """Map a pixel inside the active camera region to absolute screen coords.

        The cursor sensitivity multiplier scales movement around the screen
        centre so users can keep the same active region and still adjust feel.
        """
        fr = config.FRAME_REDUCTION
        sx = np.interp(x, (fr, self.cam_w - fr), (0, self.screen_w))
        sy = np.interp(y, (fr, self.cam_h - fr), (0, self.screen_h))

        # Sensitivity scaling around centre
        if config.CURSOR_SENSITIVITY != 1.0:
            cx, cy = self.screen_w / 2, self.screen_h / 2
            sx = (sx - cx) * config.CURSOR_SENSITIVITY + cx
            sy = (sy - cy) * config.CURSOR_SENSITIVITY + cy

        # Clamp
        sx = max(0, min(self.screen_w - 1, sx))
        sy = max(0, min(self.screen_h - 1, sy))
        return sx, sy

    def _smooth(self, x, y):
        """Exponential smoothing for buttery cursor motion."""
        a = config.SMOOTHING_FACTOR
        if self._smooth_x is None:
            # First sample - seed the filter
            self._smooth_x, self._smooth_y = x, y
        else:
            self._smooth_x += (x - self._smooth_x) * a
            self._smooth_y += (y - self._smooth_y) * a
        return self._smooth_x, self._smooth_y

    def _reset_smooth(self):
        """Clear smoothing memory (used when the hand re-appears)."""
        self._smooth_x = None
        self._smooth_y = None

    # =====================================================================
    #                              Main update
    # =====================================================================
    def update(self, landmarks):
        """Drive the state machine for one frame's worth of landmarks."""
        # ----- No hand: clean up any active state ---------------------------
        if landmarks is None:
            if self.state == self.STATE_DRAGGING:
                self.mouse.mouse_up()
            self.state = self.STATE_IDLE
            self._scroll_anchor_y = None
            self._pinch_start_time = None
            self._reset_smooth()
            self.last_action = "No Hand"
            return

        fingers = self._fingers_up(landmarks)
        thumb_tip = landmarks[HandTracker.THUMB_TIP]
        index_tip = landmarks[HandTracker.INDEX_TIP]
        middle_tip = landmarks[HandTracker.MIDDLE_TIP]

        pinch_dist = euclidean(thumb_tip, index_tip)
        right_click_dist = euclidean(thumb_tip, middle_tip)
        now = time.time()

        # Classify the *intent* of this frame in priority order.
        is_pinch = pinch_dist < config.PINCH_THRESHOLD
        is_right_click = (
            not is_pinch
            and fingers[2] == 1
            and right_click_dist < config.RIGHT_CLICK_THRESHOLD
        )
        is_scroll = (
            not is_pinch
            and fingers[1] == 1
            and fingers[2] == 1
            and pinch_dist > config.PINCH_THRESHOLD * 1.5
        )
        is_cursor_only = (
            not is_pinch
            and fingers[1] == 1
            and fingers[2] == 0
        )

        # ------------------------------------------------------------------
        # PINCH (potential click or drag)
        # ------------------------------------------------------------------
        if is_pinch:
            # End scrolling if it was active.
            if self.state == self.STATE_SCROLLING:
                self._scroll_anchor_y = None

            if self.state not in (self.STATE_PINCH_DOWN, self.STATE_DRAGGING):
                self._pinch_start_time = now
                self.state = self.STATE_PINCH_DOWN
                self.last_action = "Pinch"
                return

            # Continuing a pinch
            elapsed = now - self._pinch_start_time
            if (self.state == self.STATE_PINCH_DOWN
                    and elapsed > config.DRAG_HOLD_TIME):
                self.mouse.mouse_down()
                self.state = self.STATE_DRAGGING
                self.last_action = "Dragging"

            if self.state == self.STATE_DRAGGING:
                # Use midpoint of thumb+index for a stable drag anchor
                mid = ((thumb_tip[0] + index_tip[0]) // 2,
                       (thumb_tip[1] + index_tip[1]) // 2)
                sx, sy = self._map_to_screen(*mid)
                sx, sy = self._smooth(sx, sy)
                self.mouse.move(sx, sy)
                self.last_action = "Dragging"
            return

        # ------------------------------------------------------------------
        # PINCH RELEASED -> Click or Drop
        # ------------------------------------------------------------------
        if self.state == self.STATE_PINCH_DOWN:
            elapsed = now - (self._pinch_start_time or now)
            if (elapsed < config.DRAG_HOLD_TIME
                    and now - self._last_click_time > config.CLICK_DEBOUNCE):
                self.mouse.click()
                self._last_click_time = now
                self.last_action = "Click"
            self.state = self.STATE_IDLE
            self._pinch_start_time = None
            return

        if self.state == self.STATE_DRAGGING:
            self.mouse.mouse_up()
            self.state = self.STATE_IDLE
            self.last_action = "Drop"
            return

        # ------------------------------------------------------------------
        # SCROLL
        # ------------------------------------------------------------------
        if is_scroll:
            if self.state != self.STATE_SCROLLING:
                self._scroll_anchor_y = index_tip[1]
                self.state = self.STATE_SCROLLING
                self.last_action = "Scroll Ready"
            else:
                delta_y = index_tip[1] - self._scroll_anchor_y
                if abs(delta_y) > config.SCROLL_DEAD_ZONE:
                    # Camera Y grows downward; scroll up when finger moves up.
                    self.mouse.scroll(int(-delta_y / config.SCROLL_SENSITIVITY))
                    self._scroll_anchor_y = index_tip[1]
                    self.last_action = (
                        "Scrolling Up" if delta_y < 0 else "Scrolling Down"
                    )
            return

        # We left scroll mode; clear the anchor.
        if self.state == self.STATE_SCROLLING:
            self._scroll_anchor_y = None

        # ------------------------------------------------------------------
        # RIGHT CLICK (thumb + middle pinch)
        # ------------------------------------------------------------------
        if is_right_click:
            if now - self._last_right_click_time > config.RIGHT_CLICK_DEBOUNCE:
                self.mouse.right_click()
                self._last_right_click_time = now
                self.last_action = "Right Click"
            self.state = self.STATE_IDLE
            return

        # ------------------------------------------------------------------
        # CURSOR MOVE (index only)
        # ------------------------------------------------------------------
        if is_cursor_only:
            sx, sy = self._map_to_screen(index_tip[0], index_tip[1])
            sx, sy = self._smooth(sx, sy)
            self.mouse.move(sx, sy)
            self.state = self.STATE_CURSOR
            self.last_action = "Move"
            return

        # ------------------------------------------------------------------
        # Default: idle
        # ------------------------------------------------------------------
        self.state = self.STATE_IDLE
        self.last_action = "Idle"
