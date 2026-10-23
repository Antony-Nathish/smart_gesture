"""
main.py — Entry point for the Gesture Mouse application.

Orchestrates:
  1. Camera capture (OpenCV)
  2. Hand tracking (MediaPipe via HandTracker)
  3. Gesture classification (GestureDetector)
  4. Cursor filtering (CursorController)
  5. Mouse actions (MouseController + ScrollController)
  6. Debug overlay rendering
  7. Keyboard shortcuts (F8 toggle, ESC quit)
  8. Tkinter control panel (background thread)
  9. Beep notifications
"""

import logging
import math
import sys
import time
import threading
from typing import Optional

import cv2
import numpy as np
import pyautogui

import config
from hand_tracker      import HandTracker, INDEX_TIP, THUMB_TIP, MIDDLE_TIP
from gesture_detector  import GestureDetector, Gesture
from cursor_controller import CursorController
from mouse_controller  import MouseController
from scroll_controller import ScrollController
from ui                import ControlPanel, SharedState

# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────────────────
# Platform beep helper (Windows only, silent on other OS)
# ─────────────────────────────────────────────────────────────────────────────
def _beep(freq: int, duration_ms: int) -> None:
    try:
        import winsound
        threading.Thread(
            target=winsound.Beep,
            args=(freq, duration_ms),
            daemon=True
        ).start()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Debug overlay helpers
# ─────────────────────────────────────────────────────────────────────────────
_FONT       = cv2.FONT_HERSHEY_SIMPLEX
_GREEN      = (0, 220, 0)
_RED        = (0, 0, 220)
_YELLOW     = (0, 220, 220)
_CYAN       = (220, 220, 0)
_WHITE      = (255, 255, 255)
_DARK       = (30, 30, 30)
_ORANGE     = (0, 165, 255)


def _draw_status_bar(frame: np.ndarray, enabled: bool, gesture: str,
                     conf: float, hand_found: bool, scroll_active: bool,
                     drag_active: bool, cursor_pos: tuple) -> None:
    h, w = frame.shape[:2]

    # Semi-transparent dark bar at the top
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 50), _DARK, -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # Status text
    ctrl_color = _GREEN if enabled else _RED
    ctrl_txt   = "CTRL: ON" if enabled else "CTRL: OFF"
    cv2.putText(frame, ctrl_txt, (8, 20), _FONT, 0.55, ctrl_color, 2, cv2.LINE_AA)

    if hand_found:
        cv2.putText(frame, f"Hand: OK  Conf:{conf:.0%}", (8, 40),
                    _FONT, 0.45, _GREEN, 1, cv2.LINE_AA)
    else:
        cv2.putText(frame, "Hand: --", (8, 40), _FONT, 0.45, _RED, 1, cv2.LINE_AA)

    # Gesture label centre
    g_color = _YELLOW if enabled else _WHITE
    cv2.putText(frame, gesture, (w // 2 - 60, 22),
                _FONT, 0.55, g_color, 2, cv2.LINE_AA)

    # Cursor position
    cx, cy = cursor_pos
    cv2.putText(frame, f"({cx},{cy})", (w - 100, 22),
                _FONT, 0.42, _CYAN, 1, cv2.LINE_AA)

    # Mode indicators
    if scroll_active:
        cv2.putText(frame, "SCROLL", (w - 100, 40), _FONT, 0.42, _ORANGE, 1, cv2.LINE_AA)
    if drag_active:
        cv2.putText(frame, "DRAG", (w - 55, 40), _FONT, 0.42, _YELLOW, 1, cv2.LINE_AA)


def _draw_active_region(frame: np.ndarray) -> None:
    h, w = frame.shape[:2]
    x1 = int(config.ACTIVE_REGION_X1 * w)
    x2 = int(config.ACTIVE_REGION_X2 * w)
    y1 = int(config.ACTIVE_REGION_Y1 * h)
    y2 = int(config.ACTIVE_REGION_Y2 * h)
    cv2.rectangle(frame, (x1, y1), (x2, y2), _CYAN, 1, cv2.LINE_AA)


def _draw_cursor_target(frame: np.ndarray, norm_x: float, norm_y: float) -> None:
    """Draw a crosshair on the frame at the index fingertip camera position."""
    h, w = frame.shape[:2]
    # Show the mirrored position as a crosshair (the frame is already mirrored)
    px = int(norm_x * w)
    py = int(norm_y * h)
    cv2.drawMarker(frame, (px, py), _GREEN, cv2.MARKER_CROSS, 18, 2, cv2.LINE_AA)


def _draw_pinch_distances(frame: np.ndarray, left_dist: float,
                           right_dist: float) -> None:
    h, w = frame.shape[:2]
    bar_y = h - 14
    # Left pinch indicator
    ratio_l = min(left_dist / 0.12, 1.0)
    bar_w   = int(100 * (1.0 - ratio_l))
    color_l = _GREEN if left_dist < config.PINCH_LEFT_ACTIVATE else _RED
    cv2.rectangle(frame, (8, bar_y - 8), (8 + bar_w, bar_y), color_l, -1)
    cv2.putText(frame, "L", (6, bar_y - 10), _FONT, 0.35, color_l, 1)

    # Right pinch indicator
    ratio_r = min(right_dist / 0.12, 1.0)
    bar_w_r = int(100 * (1.0 - ratio_r))
    color_r = _GREEN if right_dist < config.PINCH_RIGHT_ACTIVATE else _RED
    cv2.rectangle(frame, (116, bar_y - 8), (116 + bar_w_r, bar_y), color_r, -1)
    cv2.putText(frame, "R", (114, bar_y - 10), _FONT, 0.35, color_r, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Main application class
# ─────────────────────────────────────────────────────────────────────────────
class GestureMouseApp:

    def __init__(self):
        log.info("=== Gesture Mouse starting ===")

        # ── Subsystems ────────────────────────────────────────────────────
        self.tracker     = HandTracker()
        self.detector    = GestureDetector()
        self.cursor_ctrl = CursorController()
        self.mouse_ctrl  = MouseController()
        self.scroll_ctrl = ScrollController(self.mouse_ctrl)
        self.state       = SharedState()
        self.panel       = ControlPanel(self.state)

        # ── App state ─────────────────────────────────────────────────────
        self._enabled    = True    # gesture control on/off
        self._running    = True

        # Keyboard listener (keyboard module not required — use cv2.waitKey)
        # F8 is ASCII 0 with key code detection via cv2 flag; see loop below.
        self._key_map = {
            27:  self._quit,        # ESC
        }

    # ─────────────────────────────────────────────────────────────────────────
    def run(self) -> None:
        # ── Start UI ──────────────────────────────────────────────────────
        self.panel.start()

        # ── Open camera ───────────────────────────────────────────────────
        cap = self._open_camera()
        if cap is None:
            log.error("Cannot open camera. Exiting.")
            sys.exit(1)

        window_name = "Gesture Mouse — Preview (F8: toggle, ESC: quit)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name,
                         int(config.CAMERA_WIDTH  * config.PREVIEW_SCALE),
                         int(config.CAMERA_HEIGHT * config.PREVIEW_SCALE))

        frame_delay_ms = max(1, int(1000 / config.TARGET_FPS))

        log.info("Camera open. Press F8 to toggle gesture control, ESC to quit.")

        try:
            while self._running:
                # ── Check UI shutdown request ─────────────────────────────
                if self.state.shutdown_requested:
                    self._quit()
                    break

                # ── Capture frame ─────────────────────────────────────────
                ok, frame = cap.read()
                if not ok or frame is None:
                    log.warning("Frame capture failed — retrying.")
                    time.sleep(0.05)
                    continue

                # Mirror frame so movement feels natural
                frame = cv2.flip(frame, 1)

                # ── Hand tracking ─────────────────────────────────────────
                hand = self.tracker.process(frame)

                # ── Gesture detection ─────────────────────────────────────
                gr = self.detector.detect(hand)

                # ── Apply live settings from UI ───────────────────────────
                self._apply_settings()

                # ── Cursor + mouse control ────────────────────────────────
                cursor_pos = (0, 0)
                if hand and self._enabled:
                    cursor_pos = self._handle_gesture(gr)
                elif self.mouse_ctrl.is_dragging:
                    # Hand lost during drag — force release
                    self.mouse_ctrl.force_release()

                # ── Debug overlay ─────────────────────────────────────────
                if config.DEBUG_MODE:
                    _draw_active_region(frame)
                    if hand:
                        _draw_cursor_target(frame, gr.cursor_x, gr.cursor_y)
                        _draw_pinch_distances(frame,
                                              gr.pinch_left_dist,
                                              gr.pinch_right_dist)
                    _draw_status_bar(frame,
                                     self._enabled,
                                     gr.gesture.name,
                                     gr.confidence,
                                     hand is not None,
                                     self.scroll_ctrl.is_active,
                                     self.mouse_ctrl.is_dragging,
                                     cursor_pos)

                # ── Show frame ────────────────────────────────────────────
                cv2.imshow(window_name, frame)

                # ── Update shared state for UI ────────────────────────────
                self.state.update_status(
                    hand_detected=hand is not None,
                    control_enabled=self._enabled,
                    gesture=gr.gesture.name,
                    confidence=gr.confidence,
                    cursor_pos=cursor_pos,
                )

                # ── Key handling ──────────────────────────────────────────
                # waitKeyEx gives us extended key codes (needed for F8 on Win)
                ext_key = cv2.waitKeyEx(frame_delay_ms)
                key8 = ext_key & 0xFF

                # Check regular keys first
                if key8 in self._key_map:
                    self._key_map[key8]()
                # F8 extended key code on Windows: 0x770000
                elif ext_key == 0x770000:
                    self._toggle_control()

        finally:
            self._cleanup(cap)

    # ─────────────────────────────────────────────────────────────────────────
    def _handle_gesture(self, gr) -> tuple:
        """
        Execute mouse actions based on the current GestureResult.
        Returns the current cursor screen position.
        """
        cursor_pos = (0, 0)

        if gr.gesture == Gesture.SCROLL:
            self.scroll_ctrl.enter_scroll_mode()
            self.scroll_ctrl.update(gr.scroll_velocity)
            # Do not move cursor while scrolling
            if self.cursor_ctrl.current_position:
                cursor_pos = self.cursor_ctrl.current_position
            return cursor_pos

        # Exit scroll mode when gesture is no longer scroll
        if self.scroll_ctrl.is_active:
            self.scroll_ctrl.exit_scroll_mode()

        # ── Cursor update ─────────────────────────────────────────────────
        sx, sy = self.cursor_ctrl.update(gr.cursor_x, gr.cursor_y)
        cursor_pos = (sx, sy)

        if gr.gesture in (Gesture.CURSOR_MOVE, Gesture.IDLE):
            self.mouse_ctrl.move(sx, sy)

        elif gr.gesture == Gesture.LEFT_CLICK:
            self.mouse_ctrl.move(sx, sy)
            self.mouse_ctrl.left_click()

        elif gr.gesture == Gesture.RIGHT_CLICK:
            self.mouse_ctrl.move(sx, sy)
            self.mouse_ctrl.right_click()

        elif gr.gesture == Gesture.DOUBLE_CLICK:
            self.mouse_ctrl.move(sx, sy)
            self.mouse_ctrl.double_click()

        elif gr.gesture == Gesture.DRAG_START:
            self.mouse_ctrl.move(sx, sy)
            self.mouse_ctrl.start_drag()

        elif gr.gesture == Gesture.DRAG_MOVE:
            self.mouse_ctrl.move(sx, sy)

        elif gr.gesture == Gesture.DRAG_END:
            self.mouse_ctrl.move(sx, sy)
            self.mouse_ctrl.end_drag()

        return cursor_pos

    # ─────────────────────────────────────────────────────────────────────────
    def _apply_settings(self) -> None:
        """Pull live settings from shared state and push to subsystems."""
        s = self.state
        with s._lock:
            config.CURSOR_SMOOTHING      = s.smoothing
            config.CURSOR_DEAD_ZONE      = s.dead_zone
            config.SCROLL_SENSITIVITY    = s.scroll_sensitivity
            config.ACTIVE_REGION_X1      = s.active_x1
            config.ACTIVE_REGION_X2      = s.active_x2
            config.ACTIVE_REGION_Y1      = s.active_y1
            config.ACTIVE_REGION_Y2      = s.active_y2

    # ─────────────────────────────────────────────────────────────────────────
    def _toggle_control(self) -> None:
        self._enabled = not self._enabled
        if self._enabled:
            log.info("Gesture control ENABLED")
            _beep(*config.BEEP_ON)
        else:
            log.info("Gesture control DISABLED")
            _beep(*config.BEEP_OFF)
            # Release mouse if held
            self.mouse_ctrl.force_release()
            self.scroll_ctrl.exit_scroll_mode()
        with self.state._lock:
            self.state.control_enabled = self._enabled

    def _quit(self) -> None:
        log.info("Quit requested.")
        self._running = False
        self.state.request_shutdown()

    # ─────────────────────────────────────────────────────────────────────────
    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        log.info("Opening camera index %d (%dx%d @ %dfps) …",
                 config.CAMERA_INDEX, config.CAMERA_WIDTH,
                 config.CAMERA_HEIGHT, config.TARGET_FPS)
        cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Try without backend hint
            cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not cap.isOpened():
            return None

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)
        # Reduce internal buffer to minimise latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        log.info("Camera opened successfully.")
        return cap

    # ─────────────────────────────────────────────────────────────────────────
    def _cleanup(self, cap: cv2.VideoCapture) -> None:
        log.info("Cleaning up …")
        self.mouse_ctrl.force_release()
        self.scroll_ctrl.exit_scroll_mode()
        self.tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        log.info("=== Gesture Mouse stopped ===")


# ─────────────────────────────────────────────────────────────────────────────
# Keyboard listener thread — monitors F8 using the 'keyboard' module if
# available, otherwise falls back to polling cv2.waitKeyEx in the main loop.
# ─────────────────────────────────────────────────────────────────────────────
def _start_keyboard_listener(app: GestureMouseApp) -> None:
    """
    Try to use the 'keyboard' module for reliable F8 detection.
    If not installed, falls back gracefully.
    """
    try:
        import keyboard as kb
        kb.add_hotkey(config.TOGGLE_KEY, app._toggle_control, suppress=False)
        kb.add_hotkey(config.EXIT_KEY,   app._quit,           suppress=False)
        log.info("Keyboard hotkeys registered via 'keyboard' module (F8=toggle, ESC=quit).")
    except ImportError:
        log.warning("'keyboard' module not found — F8 toggle via 'keyboard' module unavailable. "
                    "Press ESC in the camera window to quit. "
                    "Install with:  pip install keyboard")
    except Exception as exc:
        log.warning("Keyboard module error: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = GestureMouseApp()
    _start_keyboard_listener(app)

    # Override waitKey ESC check — also check for 'q' as an alternative quit key
    original_key_map = app._key_map.copy()
    original_key_map[ord('q')] = app._quit
    original_key_map[ord('Q')] = app._quit
    # Toggle via 't' key in the OpenCV window as fallback for F8
    original_key_map[ord('t')] = app._toggle_control
    original_key_map[ord('T')] = app._toggle_control
    app._key_map = original_key_map

    app.run()
