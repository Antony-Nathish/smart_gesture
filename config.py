"""
config.py — Central configuration for the Gesture Mouse system.
All tunable parameters live here. Edit this file to calibrate the system.
"""

# ─────────────────────────────────────────────
# Camera
# ─────────────────────────────────────────────
CAMERA_INDEX = 0          # Webcam index (0 = built-in, 1 = external)
CAMERA_WIDTH = 640        # Capture width in pixels
CAMERA_HEIGHT = 480       # Capture height in pixels
TARGET_FPS = 30           # Desired capture frame rate

# ─────────────────────────────────────────────
# Hand Tracking (MediaPipe)
# ─────────────────────────────────────────────
MAX_HANDS = 1                       # Track only the first hand for simplicity
DETECTION_CONFIDENCE = 0.7          # Minimum detection confidence [0-1]
TRACKING_CONFIDENCE = 0.5           # Minimum tracking confidence [0-1]

# ─────────────────────────────────────────────
# Active Region (fraction of frame)
# The system maps only this sub-region of the camera frame to the full screen.
# Values are fractions: 0.0 = left/top edge, 1.0 = right/bottom edge.
# Shrinking this region means smaller hand movement → larger cursor travel.
# ─────────────────────────────────────────────
ACTIVE_REGION_X1 = 0.10   # Left boundary   (fraction of frame width)
ACTIVE_REGION_X2 = 0.90   # Right boundary
ACTIVE_REGION_Y1 = 0.10   # Top boundary    (fraction of frame height)
ACTIVE_REGION_Y2 = 0.90   # Bottom boundary

# ─────────────────────────────────────────────
# Cursor Movement
# ─────────────────────────────────────────────
# Smoothing: 0 = raw (jittery), 1 = frozen. Recommended: 0.55–0.75
CURSOR_SMOOTHING = 0.65

# Dead zone: ignore movements smaller than this many pixels (screen coords).
# Increase to reduce micro-jitter when the hand is still.
CURSOR_DEAD_ZONE = 4

# Adaptive filter: if the raw jump exceeds this distance (screen pixels)
# in one frame, the smoothing factor is temporarily reduced so the cursor
# can catch up quickly without a "rubber-band" lag.
CURSOR_JUMP_THRESHOLD = 120
CURSOR_JUMP_SMOOTHING = 0.20   # Smoothing used during fast movements

# ─────────────────────────────────────────────
# Gesture Thresholds
# All distances are normalised (relative to hand size / image diagonal).
# ─────────────────────────────────────────────

# Pinch: thumb ↔ index  →  LEFT CLICK
PINCH_LEFT_ACTIVATE   = 0.045   # Distance to trigger click
PINCH_LEFT_RELEASE    = 0.065   # Distance to release click state

# Pinch: thumb ↔ middle →  RIGHT CLICK
PINCH_RIGHT_ACTIVATE  = 0.045
PINCH_RIGHT_RELEASE   = 0.065

# Double-click: two left-pinch actions within this time window (seconds)
DOUBLE_CLICK_WINDOW   = 0.40

# Drag: activate when left-pinch is held longer than this (seconds)
DRAG_HOLD_DELAY       = 0.60    # Hold left-pinch for 0.6 s to enter drag mode

# Scroll: four or five fingers extended trigger scroll mode
# Number of extended fingers required  (4 or 5)
SCROLL_FINGER_COUNT   = 4

# Scroll sensitivity: multiplier applied to vertical hand velocity
SCROLL_SENSITIVITY    = 1.2

# Minimum vertical delta (normalised) to register a scroll step
SCROLL_DEAD_ZONE      = 0.008

# Click / drag cooldown (seconds) – prevents repeated triggers
CLICK_COOLDOWN        = 0.25

# ─────────────────────────────────────────────
# Keyboard Shortcuts
# ─────────────────────────────────────────────
TOGGLE_KEY   = "f8"    # Toggle gesture control ON/OFF
EXIT_KEY     = "esc"   # Exit application

# ─────────────────────────────────────────────
# Debug / Logging
# ─────────────────────────────────────────────
DEBUG_MODE = True          # Show landmark overlay and status text in preview
LOG_LEVEL  = "INFO"        # "DEBUG", "INFO", "WARNING", "ERROR"

# ─────────────────────────────────────────────
# Beep notifications (Windows only)
# ─────────────────────────────────────────────
BEEP_ON  = (880, 120)   # (frequency Hz, duration ms) when gesture control enabled
BEEP_OFF = (440, 120)   # when gesture control disabled

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
UI_WINDOW_TITLE = "Gesture Mouse — Control Panel"
PREVIEW_SCALE   = 1.0     # Scale factor for the OpenCV debug window (1.0 = native)
