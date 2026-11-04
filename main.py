"""
main.py
-------
Entry point for the gesture-controlled virtual mouse.

Runs the webcam capture loop, feeds each frame to the HandTracker,
forwards the resulting landmarks to the GestureController, and renders the
debug HUD until the user presses the configured exit key.
"""

import sys
import time

import cv2

import config
from gesture_controller import GestureController
from hand_tracker import HandTracker
from mouse_controller import MouseController
from utils import FPSCounter, draw_hud


def open_camera():
    """Open the webcam and apply requested resolution/FPS.

    Raises RuntimeError if the camera cannot be opened.
    """
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera at index {config.CAMERA_INDEX}. "
            "Check that no other application is using the webcam."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

    # Some cameras buffer many frames; this minimises latency where supported.
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    return cap


def print_intro(mouse):
    """Friendly banner so the user knows what gestures to use."""
    banner = f"""
==============================================================
                Gesture Mouse Control
==============================================================
 Screen resolution : {mouse.screen_w} x {mouse.screen_h}
 Camera resolution : {config.CAMERA_WIDTH} x {config.CAMERA_HEIGHT}

 Gestures:
   * Index finger up only ............ Move cursor
   * Pinch (thumb + index, quick) .... Left click
   * Pinch and HOLD .................. Drag (release to drop)
   * Thumb + middle finger pinch ..... Right click
   * Index + middle up (move up/dn) .. Scroll

 Press '{config.EXIT_KEY}' in the preview window to quit.
 Safety: jerk the mouse to a screen corner to abort (PyAutoGUI failsafe).
==============================================================
"""
    print(banner)


def main():
    # ---- Initialise components ------------------------------------------
    try:
        mouse = MouseController()
    except Exception as exc:
        print(f"[Fatal] Could not initialise mouse controller: {exc}")
        sys.exit(1)

    try:
        cap = open_camera()
    except RuntimeError as exc:
        print(f"[Fatal] {exc}")
        sys.exit(1)

    tracker = HandTracker()
    controller = GestureController(mouse, config.CAMERA_WIDTH,
                                   config.CAMERA_HEIGHT)
    fps_counter = FPSCounter()

    print_intro(mouse)

    active_area = (
        config.FRAME_REDUCTION,
        config.FRAME_REDUCTION,
        config.CAMERA_WIDTH - config.FRAME_REDUCTION,
        config.CAMERA_HEIGHT - config.FRAME_REDUCTION,
    ) if config.SHOW_ACTIVE_AREA else None

    # ---- Main loop -------------------------------------------------------
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                # Transient read failures happen on some webcams; back off briefly.
                print("[Warn] Empty frame from camera, retrying...")
                time.sleep(0.05)
                continue

            # Mirror so user movement matches their reflection.
            frame = cv2.flip(frame, 1)

            # Hand detection
            landmarks, results = tracker.process(frame)

            # Gesture interpretation -> mouse actions
            controller.update(landmarks)

            # Render overlays
            if config.SHOW_LANDMARKS:
                tracker.draw_landmarks(frame, results)

            draw_hud(
                frame,
                fps=fps_counter.update() if config.SHOW_FPS else None,
                action=controller.last_action if config.SHOW_GESTURE_TEXT else None,
                state=controller.state if config.SHOW_GESTURE_TEXT else None,
                active_area=active_area,
            )

            cv2.imshow(config.WINDOW_NAME, frame)

            # waitKey(1) keeps the OpenCV event loop responsive.
            key = cv2.waitKey(1) & 0xFF
            if key == ord(config.EXIT_KEY) or key == 27:  # q or ESC
                break

            # If the user closes the window, exit cleanly too.
            try:
                if cv2.getWindowProperty(config.WINDOW_NAME,
                                         cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break

    except KeyboardInterrupt:
        print("\n[Info] Interrupted by user.")
    finally:
        # Always make sure the mouse button is released, even if we crashed
        # mid-drag.
        try:
            mouse.mouse_up()
        except Exception:
            pass
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[Info] Gesture Mouse exited cleanly.")


if __name__ == "__main__":
    main()
