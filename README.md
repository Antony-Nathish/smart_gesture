# Gesture-Cursor — Hand Gesture Controlled Virtual Mouse

Control your computer's mouse using hand gestures captured by a webcam. Gesture-Cursor uses **Python, OpenCV, MediaPipe and PyAutoGUI** to detect hand landmarks, recognize gestures and translate them into mouse actions.

This project is based on the [Gesture-Cursor repository by harrynoble](https://github.com/harrynoble/Gesture-Cursor). If you fork or redistribute the project, retain the original attribution and check the upstream repository for its current license and terms.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Gesture Controls](#gesture-controls)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [System Requirements](#system-requirements)
- [Installation on Windows](#installation-on-windows)
- [Run the Application](#run-the-application)
- [Using the Application](#using-the-application)
- [Configuration](#configuration)
- [Performance Optimization](#performance-optimization)
- [Testing Checklist](#testing-checklist)
- [Troubleshooting](#troubleshooting)
- [Safety and Privacy](#safety-and-privacy)
- [Customizing and Extending](#customizing-and-extending)
- [Limitations](#limitations)
- [Credits](#credits)

---

## Overview

Gesture-Cursor is a real-time, webcam-based virtual mouse. It tracks the hand in the camera frame and uses the detected fingertip positions and hand pose to determine the intended action.

The application is organized into separate Python modules:

- **Hand tracking** detects hand landmarks.
- **Gesture recognition** interprets the landmarks as mouse commands.
- **Mouse control** sends the commands to the operating system.
- **Main application** connects the camera, tracking, recognition and control loop.

The project is designed for learning, experimentation and hands-free mouse interaction.

## Features

- Real-time hand tracking using MediaPipe.
- 21 hand landmarks detected for a tracked hand.
- Cursor movement using the index finger.
- Left-click using a quick thumb-and-index-finger pinch.
- Drag-and-drop by holding the pinch.
- Right-click using a thumb-and-middle-finger pinch.
- Vertical scrolling using the index and middle fingers.
- Cursor smoothing to reduce unwanted movement.
- Click debouncing to reduce repeated accidental clicks.
- On-screen camera preview and gesture/status information (HUD).
- Adjustable thresholds and camera settings in `config.py`.
- Separate modules for tracking, gesture logic and mouse actions.
- Keyboard and window-based exit handling.

> The upstream implementation is designed around one tracked hand. Multi-hand control is not included as a default feature.

## Gesture Controls

Use the following gesture reference when testing:

| Hand gesture | Mouse action | How to perform it |
|---|---|---|
| Index finger extended | Move cursor | Keep the index finger extended and move it within the camera's active area. |
| Quick thumb + index pinch | Left-click | Bring the thumb tip and index fingertip together, then release quickly. |
| Hold thumb + index pinch | Drag and drop | Pinch and keep holding while moving the hand; release to drop. |
| Thumb + middle-finger pinch | Right-click | Bring the thumb tip and middle fingertip together. |
| Index + middle fingers extended | Scroll | Keep both fingers extended and move the hand vertically. |

The detected action/state is shown in the application's preview HUD when available. Gesture recognition depends on lighting, camera angle, hand visibility and the configured thresholds.

## How It Works

The application follows this processing flow:

```text
Webcam
  |
  v
OpenCV captures a frame
  |
  v
MediaPipe detects hand landmarks
  |
  v
Hand Tracker returns landmark coordinates
  |
  v
Gesture Controller interprets the hand pose
  |
  +-------------------------------+
  |                               |
  v                               v
Cursor movement              Click / drag / scroll
  |                               |
  +---------------+---------------+
                  |
                  v
          Mouse Controller
                  |
                  v
        Operating-system mouse
```

### Main processing stages

1. **Frame capture:** OpenCV reads frames from the selected webcam.
2. **Hand detection:** MediaPipe identifies the hand and its 21 landmarks.
3. **Gesture interpretation:** The gesture controller evaluates fingertip positions, distances, finger states and timing.
4. **Action selection:** The controller determines whether the user intends to move, click, drag, right-click or scroll.
5. **Mouse execution:** PyAutoGUI sends the corresponding mouse action to the operating system.
6. **Visual feedback:** The preview displays the camera image, landmarks and status information.

## Project Structure

The repository uses a flat project layout. The Python files are located directly in the project root.

```text
Gesture-Cursor/
│
├── .venv/                    # Project virtual environment (created locally)
│
├── main.py                   # Application entry point and processing loop
├── config.py                 # Camera, gesture and cursor configuration
├── hand_tracker.py           # MediaPipe hand detection and landmark extraction
├── gesture_controller.py     # Gesture classification and state management
├── mouse_controller.py       # Operating-system mouse actions via PyAutoGUI
├── utils.py                  # Helper functions and visual/FPS utilities
│
├── requirements.txt          # Python package dependencies
├── README.md                 # Project documentation
├── run.bat                   # Windows setup and launch script (optional)
└── .gitignore                # Files excluded from Git
```

### Module responsibilities

| File | Responsibility |
|---|---|
| `main.py` | Initializes the camera and application components, runs the frame-processing loop and handles application exit. |
| `config.py` | Stores tunable values such as camera resolution, cursor smoothing, sensitivity and gesture thresholds. |
| `hand_tracker.py` | Wraps MediaPipe hand tracking and provides hand landmark coordinates. |
| `gesture_controller.py` | Interprets landmarks, manages gesture states and selects mouse actions. |
| `mouse_controller.py` | Executes cursor movement, clicks, dragging and scrolling through PyAutoGUI. |
| `utils.py` | Provides helper functions such as FPS calculation, HUD drawing and coordinate/math utilities. |
| `requirements.txt` | Lists the Python packages required by the project. |
| `run.bat` | Creates/reuses the virtual environment, installs dependencies and starts the application on Windows. |

## System Requirements

### Hardware

- Windows laptop or desktop.
- Working webcam.
- Physical mouse or touchpad for fallback control.
- 4 GB RAM minimum recommended; 8 GB or more is preferable.
- Intel integrated graphics is sufficient; a dedicated GPU is not required for the standard configuration.

### Software

| Component | Version / requirement |
|---|---|
| Operating system | Windows 10 or Windows 11 |
| Python | Python 3.12 recommended; Python 3.9–3.12 supported by the upstream dependency setup |
| MediaPipe | `0.10.21` |
| OpenCV | Installed from `requirements.txt` |
| NumPy | Installed from `requirements.txt` |
| PyAutoGUI | Installed from `requirements.txt` |
| Webcam permission | Required |
| Internet | Required for initial package installation |

**Python 3.13 note:** The upstream project specifies Python 3.13 is not supported by its pinned MediaPipe setup. Python 3.13 can remain installed on the computer; use a separate Python 3.12 virtual environment for this project.

## Installation on Windows

### Method 1: Use `run.bat` (recommended)

1. Download or clone the repository.
2. Make sure `run.bat` is in the same folder as `main.py` and `requirements.txt`.
3. Double-click `run.bat`, or open Command Prompt in the project folder and run:

   ```cmd
   run.bat
   ```

The launcher is intended to:

- Reuse the existing `.venv` if available.
- Find Python 3.12 and create `.venv` if needed.
- Check pip availability.
- Install or verify dependencies from `requirements.txt`.
- Run `pip check`.
- Start `main.py`.

The first run needs an internet connection and may take several minutes.

### Method 2: Manual installation

#### 1. Clone the repository

Install Git for Windows if it is not already installed. Then run:

```cmd
cd /d D:\Projects
git clone https://github.com/harrynoble/Gesture-Cursor.git
cd Gesture-Cursor
```

Alternatively, use **Code → Download ZIP** on GitHub and extract the ZIP.

#### 2. Confirm Python 3.12

```cmd
python --version
```

If the command points to Python 3.13, use the Python 3.12 executable directly or install Python 3.12 alongside it. The Windows Python Launcher can also be used if installed:

```cmd
py -3.12 --version
```

If `py` is not recognized, that does not mean Python itself is missing. Use the full path to the Python 3.12 executable.

#### 3. Create a virtual environment

From the project root:

```cmd
py -3.12 -m venv .venv
```

If the launcher is unavailable, use the full Python 3.12 path. For example:

```cmd
"%LocalAppData%\Programs\Python\Python312\python.exe" -m venv .venv
```

#### 4. Activate the virtual environment

```cmd
.venv\Scripts\activate
```

The command prompt should begin with:

```text
(.venv)
```

#### 5. Upgrade pip and install dependencies

```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt --prefer-binary --timeout 120 --retries 10
```

#### 6. Verify the installation

```cmd
python -m pip check
```

Expected result:

```text
No broken requirements found.
```

Test the main imports:

```cmd
python -c "import cv2, mediapipe, numpy, pyautogui; print('All imports successful'); print('OpenCV:', cv2.__version__); print('MediaPipe:', mediapipe.__version__)"
```

## Run the Application

Make sure the terminal is in the project root and the virtual environment is active.

```cmd
python main.py
```

A webcam preview window titled **Gesture Mouse Control** should appear. Place your hand inside the camera frame and try the gestures listed above.

### Exit

Use one of the supported exit methods:

- Press `q` in the preview window.
- Press `Esc` in the preview window.
- Close the preview window.
- Press `Ctrl+C` in the terminal.

The application should release the webcam and safely finish any active mouse action when it exits.

## Using the Application

1. Sit where your hand is clearly visible to the webcam.
2. Ensure the room has even lighting.
3. Keep the complete hand inside the camera frame.
4. Wait for the hand landmarks to appear.
5. Begin with index-finger cursor movement.
6. Test each click and scroll gesture separately.
7. Keep your hand relaxed when you are not issuing a command.
8. Exit the application when testing is complete.

### Recommended first test

Start with a blank desktop or a harmless test window. Verify cursor movement before testing clicks, dragging or scrolling.

## Configuration

The main tunable values are stored in `config.py`. Open the file in VS Code or another text editor and inspect the actual values before changing them.

Common settings documented by the upstream project include:

| Setting | Purpose | Tuning guidance |
|---|---|---|
| `FRAME_REDUCTION` | Defines the inactive border around the camera frame and the active cursor region. | Adjust if the cursor reaches screen edges too easily or cannot reach them. |
| `SMOOTHING_FACTOR` | Controls cursor smoothing. | Around `0.3–0.5` is a useful starting range; lower values are smoother but may feel slower. |
| `CURSOR_SENSITIVITY` | Controls cursor movement sensitivity. | `1.0` is the neutral reference. |
| `PINCH_THRESHOLD` | Distance threshold for thumb-index pinch detection. | Adjust carefully to prevent missed or accidental clicks. |
| `RIGHT_CLICK_THRESHOLD` | Distance threshold for thumb-middle pinch detection. | Adjust for your camera framing and hand size in the image. |
| `DRAG_HOLD_TIME` | Time a pinch must be held before it becomes a drag. | Increase if a normal click is accidentally treated as a drag. |
| `CLICK_DEBOUNCE` | Minimum interval used to prevent repeated click triggers. | Increase if clicks fire repeatedly. |
| `SCROLL_SENSITIVITY` | Controls scroll response. | Tune in small increments. |
| `CAMERA_WIDTH` / `CAMERA_HEIGHT` | Webcam frame resolution. | Lower values can improve performance on slower systems. |
| `MODEL_COMPLEXITY` | MediaPipe model complexity. | `0` can improve speed on weaker hardware. |
| `CAMERA_INDEX` | Selects the camera device. | Try `1` or `2` if camera index `0` does not work. |

> Setting names and defaults should be checked in the checked-out `config.py`. Do not paste settings into the file unless the corresponding variable is supported by your version.

After editing configuration values, save the file and restart the application.

## Performance Optimization

For a laptop using an Intel integrated GPU:

- Use the CPU configuration; a dedicated GPU is not required.
- Set `MODEL_COMPLEXITY = 0` if the setting exists and frame processing is slow.
- Reduce camera resolution, for example to `480 × 360`, if supported by the current configuration.
- Close video-call applications and browser tabs that may be using the webcam.
- Use good, even lighting.
- Keep the hand at a comfortable distance from the camera.
- Avoid placing the hand against a visually cluttered background.
- Tune smoothing gradually. Excessive smoothing can make the cursor feel delayed.

## Testing Checklist

Use this checklist to evaluate the application:

- [ ] Python 3.12 virtual environment activates.
- [ ] All dependencies install successfully.
- [ ] `pip check` reports no broken requirements.
- [ ] OpenCV opens the webcam.
- [ ] MediaPipe detects the hand.
- [ ] Hand landmarks remain visible during movement.
- [ ] Index-finger cursor movement works.
- [ ] Quick pinch performs a left-click.
- [ ] Held pinch performs drag-and-drop.
- [ ] Thumb-middle pinch performs a right-click.
- [ ] Two-finger vertical movement scrolls.
- [ ] Cursor movement is stable.
- [ ] Clicks do not trigger repeatedly.
- [ ] The application exits and releases the camera correctly.

Record any missed gestures, accidental clicks, cursor jitter, FPS drops or camera failures so configuration changes can be evaluated systematically.

## Troubleshooting

### 1. `py` is not recognized

The Python Launcher may not be installed or added to PATH. Check:

```cmd
where python
python --version
```

If Python 3.12 is installed, create the virtual environment using its full executable path:

```cmd
"%LocalAppData%\Programs\Python\Python312\python.exe" -m venv .venv
```

### 2. `mediapipe` has no attribute `solutions`

The project uses the legacy `mp.solutions` API and pins MediaPipe `0.10.21`. Check the active environment:

```cmd
python -c "import mediapipe as mp; print(mp.__version__); print(hasattr(mp, 'solutions'))"
```

Reinstall the pinned dependencies inside the project's Python 3.12 virtual environment if necessary:

```cmd
python -m pip install --force-reinstall -r requirements.txt
```

Do not install a newer MediaPipe version without checking compatibility with this code.

### 3. MediaPipe installation fails

Confirm that the virtual environment uses Python 3.12:

```cmd
python --version
```

Then update pip and retry:

```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt --prefer-binary --timeout 120 --retries 10
```

### 4. PyPI read timeout or network error

Check the internet connection and retry:

```cmd
python -m pip install -r requirements.txt --prefer-binary --timeout 120 --retries 10
```

A timeout is generally a network/download issue; it does not automatically mean the package is incompatible.

### 5. Camera cannot be opened

- Close applications that may already be using the webcam.
- Allow desktop applications to access the camera in Windows Privacy settings.
- Check `CAMERA_INDEX` in `config.py`.
- Try camera index `1` or `2` if index `0` is unavailable.
- Check the webcam in the Windows Camera application.

### 6. Hand is not detected

- Improve lighting.
- Keep the full hand visible.
- Avoid extreme hand rotation.
- Keep the hand within a reasonable distance of the camera.
- Avoid backgrounds that blend with the hand.

### 7. Cursor is shaky or jumps

- Try a lower `SMOOTHING_FACTOR`, such as `0.3`, if supported by the configuration.
- Improve lighting and keep the hand fully visible.
- Adjust the active-region setting (`FRAME_REDUCTION`) gradually.
- Avoid changing several thresholds at once.

### 8. Clicks trigger accidentally

- Adjust `PINCH_THRESHOLD` and `RIGHT_CLICK_THRESHOLD` carefully.
- Increase `CLICK_DEBOUNCE` if repeated clicks occur.
- Review `DRAG_HOLD_TIME` if clicks are being interpreted as drags.
- Test each change separately.

### 9. PyAutoGUI failsafe activates

PyAutoGUI's failsafe can abort automation when the cursor reaches a screen corner. Keep the cursor away from the corners while testing. Do not disable the failsafe unless you understand the safety implications.

### 10. `pip check` reports dependency conflicts

Run:

```cmd
python -m pip check
```

Keep the full output and inspect the conflicting package versions before changing dependencies. Avoid random upgrades or downgrades.

## Safety and Privacy

- The application uses the webcam to detect hand movements.
- Keep the camera preview visible while testing.
- Use a physical mouse or touchpad as a fallback.
- Test on a blank desktop or harmless window before using gestures in other applications.
- Avoid testing near destructive actions, unsaved documents or confirmation dialogs.
- Do not disable PyAutoGUI's failsafe without a clear reason.
- Close the application when it is not in use.
- Review the source code before running it, especially before granting camera or system-control permissions.

## Customizing and Extending

The project is modular, so new behavior can be added without placing all logic in `main.py`.

A general extension workflow is:

1. Add new configuration values to `config.py`.
2. Add gesture classification logic in `gesture_controller.py`.
3. Add or reuse a mouse/system action in `mouse_controller.py`.
4. Connect the new behavior to the application loop in `main.py` if required.
5. Test the gesture independently and check for conflicts with existing gestures.

Possible future enhancements:

- Two-hand tracking and independent hand roles.
- Drawing mode with an on-screen canvas.
- User-configurable gesture mappings.
- Gesture calibration for different users and camera positions.
- Improved cursor filtering and adaptive smoothing.
- A settings interface for thresholds and sensitivity.
- Gesture recording and dataset collection.
- Additional accessibility controls.

These are potential extensions, not features included in the default upstream implementation.

## Limitations

- Detection quality depends on webcam resolution, lighting, hand visibility and camera placement.
- Fast movement can reduce landmark accuracy.
- The default implementation is designed around one hand.
- Gesture thresholds may need adjustment for different users and cameras.
- Cursor control can feel delayed if smoothing is set too high.
- The application requires a running desktop session and camera access.
- This is an experimental computer-vision project, not a replacement for a dedicated accessibility device.

## Credits

- **Original project:** [Gesture-Cursor](https://github.com/harrynoble/Gesture-Cursor)
- **Computer vision:** [MediaPipe](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
- **Image processing:** [OpenCV](https://opencv.org/)
- **Mouse automation:** [PyAutoGUI](https://pyautogui.readthedocs.io/)

Thanks to the original repository author and the maintainers of the open-source libraries used by this project.

---

**Project:** Gesture-Cursor — Hand Gesture Controlled Virtual Mouse  
**Primary language:** Python  
**Primary interface:** Webcam preview  
**Platform covered by this guide:** Windows 10 / Windows 11
