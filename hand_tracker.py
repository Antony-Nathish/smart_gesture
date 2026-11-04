"""
hand_tracker.py
---------------
Thin wrapper around MediaPipe Hands that returns landmarks already converted
to pixel coordinates and exposes a draw helper.

Uses the legacy `mediapipe.solutions.hands` API. This requires:
    * Python 3.9 - 3.12
    * mediapipe == 0.10.21 (pinned in requirements.txt)
See README "Installation" / "Troubleshooting" for the rationale.
"""

import cv2
import mediapipe as mp

import config


class HandTracker:
    """Detects a single hand (by default) and returns 21 pixel landmarks."""

    # MediaPipe landmark indices (subset useful elsewhere in the project)
    THUMB_TIP = 4
    INDEX_TIP = 8
    INDEX_PIP = 6
    INDEX_MCP = 5
    MIDDLE_TIP = 12
    MIDDLE_PIP = 10
    RING_TIP = 16
    RING_PIP = 14
    PINKY_TIP = 20
    PINKY_PIP = 18
    WRIST = 0

    def __init__(self,
                 max_hands=config.MAX_NUM_HANDS,
                 detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                 tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
                 model_complexity=config.MODEL_COMPLEXITY):
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=model_complexity,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

    # ---------------------------------------------------------------- API ---
    def process(self, frame_bgr):
        """Run hand detection on a BGR frame.

        Returns
        -------
        landmarks : list[tuple[int, int]] | None
            List of 21 (x, y) pixel coordinates for the first detected hand,
            or None if no hand was detected.
        results : mediapipe NamedTuple
            Raw MediaPipe results (kept so callers can draw via draw_landmarks).
        """
        # MediaPipe expects RGB. Marking the array as non-writeable allows
        # the underlying C++ code to skip a copy -> small perf win.
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)

        landmarks = None
        if results.multi_hand_landmarks:
            h, w = frame_bgr.shape[:2]
            hand = results.multi_hand_landmarks[0]
            landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in hand.landmark]
        return landmarks, results

    def draw_landmarks(self, frame, results):
        """Draw the MediaPipe landmark skeleton onto the given BGR frame."""
        if not results.multi_hand_landmarks:
            return
        for hand_landmarks in results.multi_hand_landmarks:
            self._mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_styles.get_default_hand_landmarks_style(),
                self._mp_styles.get_default_hand_connections_style(),
            )

    def close(self):
        """Release the MediaPipe graph - call on shutdown."""
        self._hands.close()
