# Gesture Mouse 🖐

A real-time, gesture-controlled mouse system for Windows, using your built-in laptop webcam, MediaPipe hand tracking, and PyAutoGUI.

---

## Features

| Gesture | Action |
|---|---|
| Index finger extended | Move cursor |
| Thumb ↔ Index pinch | Left click |
| Thumb ↔ Middle pinch | Right click |
| Two rapid left-pinches | Double click |
| Left-pinch held ≥ 0.6 s | Start drag |
| Release pinch after drag | Drop |
| 4–5 fingers open, move hand up/down | Scroll |

**Keyboard shortcuts** (global, via `keyboard` module):

| Key | Action |
|---|---|
| **F8** | Toggle gesture control ON / OFF |
| **ESC** | Quit application |

Inside the OpenCV preview window you can also press:

| Key | Action |
|---|---|
| `t` / `T` | Toggle gesture control |
| `q` / `Q` | Quit |

---

## Project Structure

```
gesture_mouse/
├── main.py              ← Entry point; orchestrates all subsystems
├── config.py            ← All tunable parameters
├── hand_tracker.py      ← MediaPipe Hands wrapper
├── gesture_detector.py  ← Stateful gesture classification
├── cursor_controller.py ← Coordinate mapping + smoothing filter
├── mouse_controller.py  ← PyAutoGUI mouse actions
├── scroll_controller.py ← Velocity-based scroll accumulation
├── ui.py                ← Tkinter control panel (background thread)
├── requirements.txt
└── README.md
```

---

## Installation (Windows CMD)

### 1. Prerequisites
- Python 3.9 – 3.11 (64-bit) — [python.org](https://www.python.org/downloads/)
- A working webcam

### 2. Create and activate a virtual environment (recommended)

```cmd
cd gesture_mouse
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** `keyboard` requires running the terminal **as Administrator** on Windows to register global hotkeys.

---

## Running the Application

```cmd
python main.py
```

Two windows open:
1. **Gesture Mouse — Preview** — live camera feed with landmark overlay and status bar.
2. **Gesture Mouse — Control Panel** — Tkinter panel for real-time settings.

---

## Calibration Guide

### Camera Region (`ACTIVE_REGION_*` in `config.py` or the Control Panel sliders)

The active region is the part of the camera frame that maps to the full screen.  
Defaults: X1=0.10, X2=0.90, Y1=0.10, Y2=0.90 (80% of the frame).

- **Smaller region** (e.g. X1=0.25, X2=0.75) → less hand movement needed to reach screen edges (higher effective sensitivity).
- **Larger region** → more precise, smaller jumps.

A cyan rectangle in the preview window shows the active region.

### Cursor Smoothing (`CURSOR_SMOOTHING`)

Range: 0.0 – 0.95.  Default: 0.65.

- **0.0** = raw, no smoothing — jittery but instantly responsive.  
- **0.95** = very heavy smoothing — silky but laggy.  
- Start at 0.65 and decrease if you feel lag, increase if the cursor vibrates.

### Dead Zone (`CURSOR_DEAD_ZONE`)

Minimum screen-pixel movement required to update the cursor.  Default: 4 px.

- Increase (8–12) if the cursor drifts when your hand is stationary.
- Decrease (1–2) if small intentional movements are ignored.

### Pinch Thresholds

In `config.py`:

```python
PINCH_LEFT_ACTIVATE  = 0.045   # lower = pinch must be tighter to trigger
PINCH_LEFT_RELEASE   = 0.065   # hysteresis gap prevents repeated clicks
```

If clicks trigger accidentally: increase `ACTIVATE`.  
If clicks are hard to trigger: decrease `ACTIVATE`.

### Drag Hold Delay (`DRAG_HOLD_DELAY`)

Default: 0.60 s.  Hold a left-pinch for this long to start dragging.  
Reduce to 0.35 for quicker drag activation; increase to 0.9 to prevent accidental drags.

### Scroll Sensitivity (`SCROLL_SENSITIVITY`)

Default: 1.2.  Higher = faster scroll per hand movement.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Camera not opening | Change `CAMERA_INDEX = 1` in `config.py` |
| F8 not working | Run CMD as Administrator |
| Cursor jitters | Increase `CURSOR_SMOOTHING` or `CURSOR_DEAD_ZONE` |
| Clicks trigger accidentally | Increase `PINCH_LEFT_ACTIVATE` threshold |
| Drag never starts | Decrease `DRAG_HOLD_DELAY` |
| Scroll too fast/slow | Adjust `SCROLL_SENSITIVITY` |
| `mediapipe` install fails | Ensure Python 3.9–3.11 (64-bit) is used |

---

## Architecture Notes

- **`main.py`** runs the capture loop in the **main thread** (required by OpenCV on Windows).
- **`ui.py`** runs Tkinter in a **daemon thread**.  Settings are exchanged via `SharedState` which uses a `threading.Lock`.
- **`GestureDetector`** is purely stateful classification — it emits `GestureResult` objects but never calls PyAutoGUI.
- **`CursorController`** performs coordinate mapping and filtering with no side-effects.
- **`MouseController`** wraps PyAutoGUI and tracks drag state to guarantee `mouseUp` is always called.

---

## Dependencies

| Package | Purpose |
|---|---|
| `mediapipe` | Hand landmark detection |
| `opencv-python` | Camera capture, frame rendering |
| `pyautogui` | Mouse movement and clicks |
| `numpy` | Array operations |
| `keyboard` | Global F8 / ESC hotkeys |
