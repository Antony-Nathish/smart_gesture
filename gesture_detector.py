"""
gesture_detector.py — Stateless gesture recognition from HandData.

Responsibilities:
  - Compute normalised pinch distances.
  - Classify the current gesture (idle, left-pinch, right-pinch, scroll, drag).
  - Track gesture state and timings to distinguish click / double-click / drag.
  - Expose a clean GestureResult dataclass to all callers.

This module contains NO mouse-control logic — it only classifies what the
hand is doing.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple

import math
import config
from hand_tracker import (
    HandData,
    THUMB_TIP, INDEX_TIP, MIDDLE_TIP,
    WRIST, INDEX_MCP,
    FINGER_MCP_IDS,
)

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
class Gesture(Enum):
    IDLE         = auto()   # No recognised gesture
    CURSOR_MOVE  = auto()   # Index finger extended — move cursor
    LEFT_CLICK   = auto()   # Thumb ↔ index pinch activated
    RIGHT_CLICK  = auto()   # Thumb ↔ middle pinch activated
    DOUBLE_CLICK = auto()   # Two rapid left-pinch actions
    DRAG_START   = auto()   # Left-pinch held → start drag
    DRAG_MOVE    = auto()   # Currently dragging
    DRAG_END     = auto()   # Drag released
    SCROLL       = auto()   # 4/5 fingers extended → scroll mode


@dataclass
class GestureResult:
    gesture: Gesture = Gesture.IDLE
    # Normalised (0-1) index fingertip position for cursor movement
    cursor_x: float = 0.5
    cursor_y: float = 0.5
    # Vertical velocity for scroll (positive = scroll down, negative = scroll up)
    scroll_velocity: float = 0.0
    # Pinch distances (debug display)
    pinch_left_dist:  float = 1.0
    pinch_right_dist: float = 1.0
    # Extended finger flags [index, middle, ring, pinky]
    extended: list = field(default_factory=lambda: [False]*4)
    # Confidence from MediaPipe
    confidence: float = 0.0


def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _hand_size(hand: HandData) -> float:
    """
    Approximate hand size as the distance from WRIST to INDEX_MCP.
    Used to normalise pinch distances so they are scale-invariant.
    """
    w = hand.tip(WRIST)
    m = hand.tip(INDEX_MCP)
    size = _distance(w, m)
    return max(size, 0.001)   # prevent division by zero


class GestureDetector:
    """
    Stateful gesture classifier.

    Call detect(hand_data) every frame.  Returns a GestureResult.
    Pass hand_data=None when the hand is not visible.
    """

    def __init__(self):
        # ── Left-pinch state ──────────────────────────────────────────────
        self._left_pinch_active   = False
        self._left_pinch_start_t  = 0.0   # when the pinch began
        self._last_left_click_t   = 0.0   # time of the most recent click event
        self._pending_double      = False  # first click registered, waiting for second

        # ── Right-pinch state ─────────────────────────────────────────────
        self._right_pinch_active  = False

        # ── Drag state ────────────────────────────────────────────────────
        self._drag_active         = False

        # ── Scroll state ─────────────────────────────────────────────────
        self._scroll_active       = False
        self._prev_index_y        = None   # previous normalised y for velocity
        self._prev_frame_t        = time.monotonic()

        # ── Cooldown ─────────────────────────────────────────────────────
        self._last_click_time     = 0.0

        log.info("GestureDetector initialised.")

    # ─────────────────────────────────────────────────────────────────────────
    def detect(self, hand: Optional[HandData]) -> GestureResult:
        now = time.monotonic()
        dt  = max(now - self._prev_frame_t, 1e-6)
        self._prev_frame_t = now

        if hand is None:
            self._reset_on_loss()
            return GestureResult()

        result = GestureResult(confidence=hand.confidence)

        # ── Cursor position (always from index tip) ───────────────────────
        result.cursor_x, result.cursor_y = hand.tip(INDEX_TIP)

        # ── Extended fingers ──────────────────────────────────────────────
        result.extended = hand.extended_fingers()   # [index, middle, ring, pinky]
        n_extended = sum(result.extended)

        # ── Normalised pinch distances ────────────────────────────────────
        size = _hand_size(hand)
        raw_left  = _distance(hand.tip(THUMB_TIP), hand.tip(INDEX_TIP))  / size
        raw_right = _distance(hand.tip(THUMB_TIP), hand.tip(MIDDLE_TIP)) / size
        result.pinch_left_dist  = raw_left
        result.pinch_right_dist = raw_right

        # ── Scroll mode: 4 or 5 fingers extended ─────────────────────────
        # Count thumb separately (tip above wrist y)
        thumb_up = hand.tip(THUMB_TIP)[1] < hand.tip(WRIST)[1]
        total_extended = n_extended + (1 if thumb_up else 0)

        if total_extended >= config.SCROLL_FINGER_COUNT:
            self._scroll_active = True
            # Vertical velocity
            cur_y = result.cursor_y
            if self._prev_index_y is not None:
                dy = cur_y - self._prev_index_y   # positive = moving down in image
                velocity = dy / dt
                if abs(dy) < config.SCROLL_DEAD_ZONE:
                    velocity = 0.0
            else:
                velocity = 0.0
            self._prev_index_y = cur_y
            result.scroll_velocity = velocity
            result.gesture = Gesture.SCROLL
            return result
        else:
            self._scroll_active = False
            self._prev_index_y  = None

        # ── Drag handling ─────────────────────────────────────────────────
        if self._drag_active:
            if raw_left > config.PINCH_LEFT_RELEASE:
                self._drag_active = False
                self._left_pinch_active = False
                result.gesture = Gesture.DRAG_END
                log.debug("Drag END")
                return result
            else:
                result.gesture = Gesture.DRAG_MOVE
                return result

        # ── Left pinch (thumb ↔ index) ────────────────────────────────────
        if not self._left_pinch_active:
            if raw_left < config.PINCH_LEFT_ACTIVATE:
                cooldown_ok = (now - self._last_click_time) > config.CLICK_COOLDOWN
                if cooldown_ok:
                    self._left_pinch_active  = True
                    self._left_pinch_start_t = now
                    log.debug("Left pinch START (dist=%.3f)", raw_left)
        else:
            if raw_left > config.PINCH_LEFT_RELEASE:
                # Pinch released — classify as click or drag-start
                pinch_duration = now - self._left_pinch_start_t
                self._left_pinch_active = False

                if pinch_duration >= config.DRAG_HOLD_DELAY:
                    # Long hold → drag (but drag_active wasn't set yet;
                    # handle below in the drag-start branch)
                    pass
                else:
                    # Short pinch → click / double-click
                    if self._pending_double and (now - self._last_left_click_t) < config.DOUBLE_CLICK_WINDOW:
                        result.gesture = Gesture.DOUBLE_CLICK
                        self._pending_double   = False
                        self._last_click_time  = now
                        log.debug("DOUBLE CLICK")
                    else:
                        result.gesture = Gesture.LEFT_CLICK
                        self._pending_double   = True
                        self._last_left_click_t = now
                        self._last_click_time   = now
                        log.debug("LEFT CLICK")
                return result
            else:
                # Pinch still held — check for drag threshold
                if (now - self._left_pinch_start_t) >= config.DRAG_HOLD_DELAY:
                    self._drag_active = True
                    result.gesture = Gesture.DRAG_START
                    log.debug("Drag START")
                    return result

        # ── Right pinch (thumb ↔ middle) ──────────────────────────────────
        if not self._right_pinch_active:
            if raw_right < config.PINCH_RIGHT_ACTIVATE:
                cooldown_ok = (now - self._last_click_time) > config.CLICK_COOLDOWN
                if cooldown_ok:
                    self._right_pinch_active = True
                    log.debug("Right pinch START (dist=%.3f)", raw_right)
        else:
            if raw_right > config.PINCH_RIGHT_RELEASE:
                self._right_pinch_active = False
                result.gesture = Gesture.RIGHT_CLICK
                self._last_click_time = now
                log.debug("RIGHT CLICK")
                return result

        # ── Default: cursor move ──────────────────────────────────────────
        result.gesture = Gesture.CURSOR_MOVE
        return result

    # ─────────────────────────────────────────────────────────────────────────
    def _reset_on_loss(self):
        """Called when hand tracking is lost to avoid stuck states."""
        if self._drag_active:
            log.warning("Hand lost during drag — forcing drag release.")
        self._left_pinch_active  = False
        self._right_pinch_active = False
        self._drag_active        = False
        self._scroll_active      = False
        self._prev_index_y       = None
