# SMART GESTURE 🤚
### Hand Gesture Controlled Desktop Application

Control your computer using natural hand movements with real-time computer vision and hand tracking.

Smart Gesture is a Python-based desktop application that transforms webcam hand movements into mouse operations. It provides cursor movement, clicking, dragging, and scrolling through intuitive hand gestures.

---

## 1. Project Overview

Smart Gesture aims to provide a touch-free and natural way to interact with a computer.

The application uses a webcam to detect hand landmarks and recognize predefined gestures. Recognized gestures are translated into mouse actions using Python.

### Key Features

- Real-time hand tracking using a webcam.
- Gesture-controlled mouse cursor movement.
- Left-click and right-click operations.
- Drag-and-drop functionality.
- Vertical scrolling.
- Adjustable cursor smoothness.
- Live camera preview.
- Interactive desktop dashboard.
- Animated gesture tutorials using GIF files.
- Privacy and application information pages.

---

## 2. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| OpenCV | Webcam capture and image processing |
| MediaPipe | Hand landmark detection |
| PyAutoGUI | Mouse movement and actions |
| Tkinter | Desktop application interface |
| Pillow | GIF animation and image rendering |

---

## 3. Gesture Controls

The following gestures are used to operate the computer.

### 3.1 Cursor Movement

**Gesture:** Index finger extended.

- Keep the index finger extended.
- Fold the remaining fingers naturally.
- Move the index fingertip in the desired direction.
- The mouse cursor follows the finger movement.

### 3.2 Left Click

**Gesture:** Thumb + Index finger pinch.

- Bring the thumb and index fingertips together.
- The application recognizes the pinch.
- A left mouse click is performed.
- Separate the fingers to return to the neutral position.

### 3.3 Right Click

**Gesture:** Thumb + Index finger + Middle finger pinch.

- Extend the thumb, index finger, and middle finger.
- Bring all three fingertips together simultaneously.
- Keep the ring finger and little finger folded.
- The application recognizes the three-finger pinch.
- A right mouse click is performed.
- Release the pinch to return to the neutral position.

**Important:** Right-click uses all three fingertips together. A thumb-and-middle-finger-only pinch must not trigger right-click.

### 3.4 Drag and Drop

**Gesture:** Hold Thumb + Index finger pinch.

- Bring the thumb and index fingertips together.
- Keep the pinch held to select an item.
- Move the hand while maintaining the pinch.
- Separate the fingers to release the selected item.

### 3.5 Scrolling

**Gesture:** Use the existing configured scroll gesture.

- Move the hand upwards to scroll in one direction.
- Move the hand downwards to scroll in the opposite direction.
- Keep the movement smooth and controlled.

The exact finger configuration and scroll direction must match the gesture implementation in `gesture_controller.py`.

---

## 4. Desktop Application Interface

The application provides a graphical desktop interface with five main navigation sections.

### Dashboard

The Dashboard provides the main application controls.

Features:
- Application name and description.
- Application running status.
- Camera status.
- Camera preview ON/OFF control.
- Close Smart Gesture button.

**Camera Preview:**
- Green indicates ON.
- Red indicates OFF.
- When OFF, the camera display shows a black placeholder.
- When ON, the existing camera preview is restored.

**Close Smart Gesture:**
- Displays a confirmation dialog.
- Stops camera processing.
- Releases webcam resources.
- Shuts down background threads safely.
- Closes the application.

### Edit

The Edit page provides cursor smoothness adjustment.

**Smoothness Slider:**
- Minimum: 1
- Maximum: 10
- Default: 5

Higher smoothness reduces cursor jitter but may increase response delay.

Lower smoothness provides faster response but may increase cursor shaking.

**Reset Default:**

Restores the smoothness value to 5 and applies the default configuration.

### Controls

The Controls page contains interactive gesture tutorials.

Available tutorials:

1. Index Finger – Cursor Movement
2. Left Click
3. Right Click
4. Scroll Up and Down
5. Drag and Drop

**Tutorial Features:**
- Animated GIF demonstrations.
- Tutorial titles and descriptions.
- Watch Tutorial option.
- Continuous GIF playback.
- Expanded tutorial viewing mode.

**Expanded Tutorial Mode:**

When a tutorial is opened:
- The left navigation sidebar is minimized.
- The selected animation is displayed in a larger area.
- The camera preview moves to the bottom-right corner.
- A close (X) button appears at the bottom.

When the tutorial is closed:
- The normal navigation sidebar is restored.
- The camera returns to its original bottom position.
- The normal Controls page is displayed.

### Privacy & Policy

The Privacy & Policy page explains:
- Webcam access.
- Local image processing.
- Data collection practices.
- Data storage.
- Third-party libraries.
- User control over camera access.
- Contact information.

### About

The About page provides project information, technologies, creator details, documentation, and support information.

**Project Creators:**
1. Antony Arokia Nathish
2. Mahendra Prasndth
3. Sanjay
4. Pon Malar Selavan

**Contact Email:** antonynathish@gmail.com

---

## 5. Animated Tutorial Files

Gesture tutorial GIF files are stored in the `controls` directory.

Example structure:

```text
controls/
    cursor_movement.gif
    left_click.gif
    right_click.gif
    scroll.gif
    drag_drop.gif
```

The application loads the available GIF files and displays them in the Controls page.

Requirements:
- Preserve original GIF aspect ratios.
- Support continuous animation playback.
- Handle missing GIF files gracefully.
- Avoid blocking the main UI thread.
- Stop animation updates when leaving the tutorial.
- Avoid duplicate animation loops.

The filenames above are suggested names. The application should use the actual filenames available in the project.

---

## 6. Project Structure

Example project structure:

```text
Smart-Gesture/
│
├── controls/
│   ├── cursor_movement.gif
│   ├── left_click.gif
│   ├── right_click.gif
│   ├── scroll.gif
│   └── drag_drop.gif
│
├── main.py
├── control_dashboard.py
├── config.py
├── hand_tracker.py
├── gesture_controller.py
├── mouse_controller.py
├── utils.py
│
├── requirements.txt
├── README.md
├── run.bat
└── setup.ps1
```

The actual project may contain additional modules and configuration files.

---

## 7. Installation

### Prerequisites

- Windows 10 or Windows 11.
- Python 3.12 recommended.
- A working webcam.
- Internet connection for initial dependency installation.

### Step 1: Clone the Repository

```bash
git clone YOUR_REPOSITORY_URL
```

### Step 2: Open the Project

```bash
cd Smart-Gesture
```

### Step 3: Create a Virtual Environment

```bash
python -m venv .venv
```

### Step 4: Activate the Environment

```bash
.venv\Scripts\activate
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Run the Application

```bash
python main.py
```

Alternatively, use the provided `run.bat` file if available.

---

## 8. Privacy and Security

Smart Gesture uses webcam access to detect hand movements.

- Webcam frames are processed locally as designed.
- The application does not require user registration.
- Webcam recordings should not be stored.
- Application settings may be stored locally.
- Users can disable the camera preview or close the application.

Third-party libraries retain their respective licenses and privacy policies.

---

## 9. Troubleshooting

| Problem | Possible Solution |
|---|---|
| Camera not detected | Check webcam permissions and connections |
| Cursor movement is shaky | Increase smoothness |
| Hand not detected | Improve lighting and camera positioning |
| Click not recognized | Check fingertip detection and gesture thresholds |
| Right-click not recognized | Ensure thumb, index, and middle fingertips meet together |
| GIF not displaying | Check the controls folder and GIF path |
| Application closes unexpectedly | Check the terminal error output |
| Dependencies missing | Run `pip install -r requirements.txt` |

---

## 10. Future Improvements

- Customizable gesture mappings.
- Improved hand tracking accuracy.
- Gesture sensitivity configuration.
- Additional gesture tutorials.
- Multi-hand gesture support.
- Improved cursor stabilization.
- User-defined gesture profiles.
- Cross-platform support.

---

## 11. Project Information

| Detail | Information |
|---|---|
| Project Name | Smart Gesture |
| Project Category | Computer Vision |
| Application Type | Desktop Application |
| Programming Language | Python |
| Interface | Tkinter / Existing UI Framework |
| Hand Tracking | MediaPipe |
| Image Processing | OpenCV |
| Mouse Automation | PyAutoGUI |

---

## 12. Bug Reports and Support

Found a bug or have a suggestion?

Contact the development team:

**Email:** antonynathish@gmail.com

### Report a Bug

When reporting an issue, include:

- Operating System
- Python Version
- Application Version
- Description of the issue
- Steps to reproduce
- Expected result
- Actual result

---

## 13. Project Creators

Developed by:

- Antony Arokia Nathish
- Mahendra Prasad
- Sanjay
- Pon Malar Selavan

**SMART GESTURE – Making Computer Interaction Natural Through Hand Gestures.**
