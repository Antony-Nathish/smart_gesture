"""
config.py
---------
Central configuration for the gesture-controlled virtual mouse.

Tweak the values below to tune sensitivity, smoothing, gesture thresholds,
camera settings and UI behaviour without touching the rest of the code.
"""

# ---------------------------------------------------------------------------
# Camera Settings
# ---------------------------------------------------------------------------
CAMERA_INDEX = 0          # 0 = default webcam, 1+ = additional cameras
CAMERA_WIDTH = 640        # Lower = faster processing, higher = more precision
CAMERA_HEIGHT = 480
CAMERA_FPS = 30           # Requested FPS from the camera driver

# Pixels of "dead zone" around the camera frame that are ignored.
# A larger reduction means a smaller hand-movement area maps to the full
# screen, increasing effective sensitivity.
FRAME_REDUCTION = 100

# ---------------------------------------------------------------------------
# MediaPipe Hand Detection
# ---------------------------------------------------------------------------
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5
MODEL_COMPLEXITY = 1      # 0 = fastest, 1 = balanced

# ---------------------------------------------------------------------------
# Cursor Control
# ---------------------------------------------------------------------------
# Smoothing factor for cursor movement (exponential smoothing).
#   1.0 -> no smoothing (instant, jittery)
#   0.0 -> infinite smoothing (frozen)
# 0.3 - 0.6 is usually the sweet spot.
SMOOTHING_FACTOR = 0.4

# Sensitivity multiplier applied around the screen centre. Use values > 1
# to amplify hand motion, < 1 to dampen it.
CURSOR_SENSITIVITY = 1.0

# ---------------------------------------------------------------------------
# Gesture Thresholds (in pixels, measured in the camera frame)
# ---------------------------------------------------------------------------
PINCH_THRESHOLD = 40            # Thumb-index distance below this -> pinch
RIGHT_CLICK_THRESHOLD = 40      # Thumb-middle distance below this -> r-click
SCROLL_DEAD_ZONE = 6            # Min vertical pixels of movement to scroll
SCROLL_SENSITIVITY = 8          # Higher = slower scroll

# Distance from index-finger MCP that the thumb tip must exceed for the
# thumb to be considered "extended" (used in finger-up detection).
THUMB_EXTENDED_DISTANCE = 60

# ---------------------------------------------------------------------------
# Debounce / Timing (seconds)
# ---------------------------------------------------------------------------
CLICK_DEBOUNCE = 0.30           # Min interval between clicks
RIGHT_CLICK_DEBOUNCE = 0.45     # Min interval between right-clicks
DRAG_HOLD_TIME = 0.30           # Pinch held longer than this -> drag

# ---------------------------------------------------------------------------
# UI Settings
# ---------------------------------------------------------------------------
SHOW_FPS = True
SHOW_LANDMARKS = True
SHOW_ACTIVE_AREA = True
SHOW_GESTURE_TEXT = True
WINDOW_NAME = "Gesture Mouse Control"
EXIT_KEY = "q"

# Distance-based page scrolling
SCROLL_TRIGGER_DISTANCE = 70  # Camera pixels
SCROLL_COOLDOWN = 0.35        # Seconds between page actions