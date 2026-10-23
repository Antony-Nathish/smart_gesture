"""
hand_tracker.py — MediaPipe hand-detection wrapper.

Responsibilities:
  - Initialise MediaPipe Hands.
  - Accept an BGR frame from OpenCV and return structured landmark data.
  - Normalise landmark coordinates to [0, 1] (relative to frame dimensions).
  - Annotate the frame with landmark overlay when debug mode is active.
  - Handle detection loss gracefully (returns None instead of crashing).
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

import config

log = logging.getLogger(__name__)

# ── MediaPipe landmark indices ───────────────────────────────────────────────
WRIST            = 0
THUMB_TIP        = 4
INDEX_TIP        = 8
INDEX_MCP        = 5
MIDDLE_TIP       = 12
MIDDLE_MCP       = 9
RING_TIP         = 16
RING_MCP         = 13
PINKY_TIP        = 20
PINKY_MCP        = 17

FINGERTIP_IDS  = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_MCP_IDS = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
FINGER_PIP_IDS = [6, 10, 14, 18]   # PIP joints for fingers 1-4


@dataclass
class HandData:
    """Structured result returned per detected hand."""
    # Raw normalised landmarks: list of (x, y, z) tuples, len == 21
    landmarks: List[Tuple[float, float, float]] = field(default_factory=list)
    # Pixel-space landmarks for drawing: list of (px, py) ints, len == 21
    px_landmarks: List[Tuple[int, int]] = field(default_factory=list)
    # Tracking confidence score [0, 1]
    confidence: float = 0.0
    # "Left" or "Right" as labelled by MediaPipe (from the subject's perspective)
    handedness: str = "Unknown"

    # ── Convenience accessors ────────────────────────────────────────────────
    def tip(self, landmark_id: int) -> Tuple[float, float]:
        """Return (x, y) normalised coords for a landmark."""
        lm = self.landmarks[landmark_id]
        return lm[0], lm[1]

    def tip_px(self, landmark_id: int) -> Tuple[int, int]:
        """Return pixel (x, y) for a landmark."""
        return self.px_landmarks[landmark_id]

    def extended_fingers(self) -> List[bool]:
        """
        Return [index, middle, ring, pinky] booleans: True = finger extended.
        A finger is considered extended when its tip is above its MCP joint
        (lower y value in image coords = higher on screen).
        """
        result = []
        for tip_id, mcp_id in zip(FINGER_MCP_IDS, [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]):
            tip_y  = self.landmarks[tip_id][1]
            mcp_y  = self.landmarks[mcp_id][1]
            result.append(tip_y < mcp_y)
        return result


class HandTracker:
    """
    Thin wrapper around MediaPipe Hands.

    Usage:
        tracker = HandTracker()
        hand_data = tracker.process(bgr_frame)
        # hand_data is None if no hand is detected
    """

    def __init__(self):
        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_drawing_styles = mp.solutions.drawing_styles
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_HANDS,
            min_detection_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )
        log.info("HandTracker initialised (max_hands=%d, det=%.2f, trk=%.2f)",
                 config.MAX_HANDS, config.DETECTION_CONFIDENCE, config.TRACKING_CONFIDENCE)

    # ─────────────────────────────────────────────────────────────────────────
    def process(self, bgr_frame: np.ndarray) -> Optional[HandData]:
        """
        Process a single BGR frame.

        Returns the first detected HandData, or None if no hand is found.
        The frame is annotated in-place when config.DEBUG_MODE is True.
        """
        h, w = bgr_frame.shape[:2]

        # MediaPipe expects RGB
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            return None

        # Use only the first detected hand
        hand_landmarks = results.multi_hand_landmarks[0]

        # Handedness label
        handedness = "Unknown"
        if results.multi_handedness:
            handedness = results.multi_handedness[0].classification[0].label
            confidence = results.multi_handedness[0].classification[0].score
        else:
            confidence = 0.0

        # Build landmark lists
        lm_list = []
        px_list = []
        for lm in hand_landmarks.landmark:
            lm_list.append((lm.x, lm.y, lm.z))
            px_list.append((int(lm.x * w), int(lm.y * h)))

        # Draw overlay
        if config.DEBUG_MODE:
            self._mp_drawing.draw_landmarks(
                bgr_frame,
                hand_landmarks,
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_drawing_styles.get_default_hand_landmarks_style(),
                self._mp_drawing_styles.get_default_hand_connections_style(),
            )

        return HandData(
            landmarks=lm_list,
            px_landmarks=px_list,
            confidence=confidence,
            handedness=handedness,
        )

    def close(self):
        self._hands.close()
        log.info("HandTracker closed.")
