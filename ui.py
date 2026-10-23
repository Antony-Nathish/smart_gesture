"""
ui.py — Tkinter control panel that runs in a background thread alongside the
        OpenCV camera loop which runs in the main thread.

Responsibilities:
  - Display live status: hand detected, gesture control ON/OFF, current gesture.
  - Show and allow editing of sensitivity, smoothing, and scroll settings.
  - Restore defaults button.
  - Communicate with the main loop through a thread-safe SharedState object.
  - The OpenCV preview window is owned by the main thread; Tkinter only shows
    the control panel.
"""

import logging
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

import config

log = logging.getLogger(__name__)


class SharedState:
    """
    Thread-safe bridge between the main processing loop and the Tkinter UI.
    The main loop writes status; Tkinter reads it.
    The UI writes settings; the main loop reads them.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Status (written by main loop)
        self.hand_detected   = False
        self.control_enabled = True
        self.current_gesture = "—"
        self.confidence      = 0.0
        self.cursor_pos      = (0, 0)

        # Settings (written by UI, read by main loop)
        self.smoothing           = config.CURSOR_SMOOTHING
        self.dead_zone           = config.CURSOR_DEAD_ZONE
        self.scroll_sensitivity  = config.SCROLL_SENSITIVITY
        self.active_x1           = config.ACTIVE_REGION_X1
        self.active_x2           = config.ACTIVE_REGION_X2
        self.active_y1           = config.ACTIVE_REGION_Y1
        self.active_y2           = config.ACTIVE_REGION_Y2

        # Shutdown flag
        self.shutdown_requested = False

    # ── Thread-safe helpers ───────────────────────────────────────────────────
    def update_status(self, hand_detected: bool, control_enabled: bool,
                      gesture: str, confidence: float, cursor_pos: tuple):
        with self._lock:
            self.hand_detected   = hand_detected
            self.control_enabled = control_enabled
            self.current_gesture = gesture
            self.confidence      = confidence
            self.cursor_pos      = cursor_pos

    def get_settings(self):
        with self._lock:
            return {
                "smoothing":          self.smoothing,
                "dead_zone":          self.dead_zone,
                "scroll_sensitivity": self.scroll_sensitivity,
                "active_x1":          self.active_x1,
                "active_x2":          self.active_x2,
                "active_y1":          self.active_y1,
                "active_y2":          self.active_y2,
            }

    def request_shutdown(self):
        with self._lock:
            self.shutdown_requested = True


# ─────────────────────────────────────────────────────────────────────────────
class ControlPanel:
    """
    Tkinter control panel window.

    Run via start() which spawns a daemon thread so it does not block the
    main OpenCV loop.
    """

    def __init__(self, state: SharedState):
        self._state  = state
        self._thread: Optional[threading.Thread] = None
        self._root:   Optional[tk.Tk]            = None

    # ─────────────────────────────────────────────────────────────────────────
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="TkUI")
        self._thread.start()

    # ─────────────────────────────────────────────────────────────────────────
    def _run(self) -> None:
        try:
            self._root = tk.Tk()
            self._root.title(config.UI_WINDOW_TITLE)
            self._root.resizable(False, False)
            self._root.protocol("WM_DELETE_WINDOW", self._on_close)
            self._build_ui()
            self._poll_status()
            self._root.mainloop()
        except Exception as exc:
            log.error("Tkinter UI error: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = self._root
        root.configure(bg="#1e1e2e")
        pad = {"padx": 10, "pady": 4}

        # ── Title ─────────────────────────────────────────────────────────
        tk.Label(root, text="🖐  Gesture Mouse", font=("Segoe UI", 14, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=(12, 4))

        # ── Status frame ──────────────────────────────────────────────────
        sf = tk.LabelFrame(root, text="Status", bg="#1e1e2e", fg="#a6adc8",
                           font=("Segoe UI", 9))
        sf.pack(fill="x", **pad)

        self._var_hand    = tk.StringVar(value="—")
        self._var_ctrl    = tk.StringVar(value="—")
        self._var_gesture = tk.StringVar(value="—")
        self._var_conf    = tk.StringVar(value="—")
        self._var_cursor  = tk.StringVar(value="—")

        rows = [
            ("Hand Detected",    self._var_hand),
            ("Control Active",   self._var_ctrl),
            ("Current Gesture",  self._var_gesture),
            ("Confidence",       self._var_conf),
            ("Cursor Position",  self._var_cursor),
        ]
        for label, var in rows:
            row = tk.Frame(sf, bg="#1e1e2e")
            row.pack(fill="x", padx=6, pady=1)
            tk.Label(row, text=label + ":", width=18, anchor="w",
                     bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 9)).pack(side="left")
            tk.Label(row, textvariable=var, anchor="w",
                     bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 9, "bold")).pack(side="left")

        # ── Settings frame ────────────────────────────────────────────────
        cf = tk.LabelFrame(root, text="Settings", bg="#1e1e2e", fg="#a6adc8",
                           font=("Segoe UI", 9))
        cf.pack(fill="x", **pad)

        self._sliders = {}

        slider_defs = [
            # (label,           attr,               from_, to_,  resolution)
            ("Smoothing",       "smoothing",         0.0,  0.95, 0.01),
            ("Dead Zone (px)",  "dead_zone",         0,    20,   1),
            ("Scroll Sens.",    "scroll_sensitivity",0.1,  5.0,  0.1),
            ("Active X1",       "active_x1",         0.0,  0.49, 0.01),
            ("Active X2",       "active_x2",         0.51, 1.0,  0.01),
            ("Active Y1",       "active_y1",         0.0,  0.49, 0.01),
            ("Active Y2",       "active_y2",         0.51, 1.0,  0.01),
        ]

        for label, attr, from_, to_, res in slider_defs:
            row = tk.Frame(cf, bg="#1e1e2e")
            row.pack(fill="x", padx=6, pady=2)
            tk.Label(row, text=label + ":", width=18, anchor="w",
                     bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 9)).pack(side="left")
            var = tk.DoubleVar(value=getattr(self._state, attr))
            sl = ttk.Scale(row, from_=from_, to=to_, orient="horizontal",
                           variable=var, length=160)
            sl.pack(side="left")
            val_lbl = tk.Label(row, textvariable=var, width=5, anchor="w",
                               bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 9))
            val_lbl.pack(side="left", padx=4)
            # Bind change → write to shared state
            def _on_change(val, a=attr, v=var):
                with self._state._lock:
                    setattr(self._state, a, float(v.get()))
            var.trace_add("write", lambda *args, a=attr, v=var: _on_change(None, a, v))
            self._sliders[attr] = var

        # ── Buttons ───────────────────────────────────────────────────────
        bf = tk.Frame(root, bg="#1e1e2e")
        bf.pack(pady=8)

        tk.Button(bf, text="Restore Defaults", command=self._restore_defaults,
                  bg="#313244", fg="#cdd6f4", relief="flat",
                  font=("Segoe UI", 9), padx=8, pady=4).pack(side="left", padx=4)

        tk.Button(bf, text="Quit", command=self._on_close,
                  bg="#f38ba8", fg="#1e1e2e", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=8, pady=4).pack(side="left", padx=4)

        # ── Keyboard shortcuts hint ───────────────────────────────────────
        tk.Label(root, text=f"F8 = toggle control   ESC = quit",
                 bg="#1e1e2e", fg="#585b70", font=("Segoe UI", 8)).pack(pady=(0, 10))

    # ─────────────────────────────────────────────────────────────────────────
    def _poll_status(self) -> None:
        """Refresh status labels every 200 ms."""
        if self._root is None:
            return
        try:
            s = self._state
            with s._lock:
                hand    = "✅ Yes" if s.hand_detected   else "❌ No"
                ctrl    = "✅ ON"  if s.control_enabled  else "⏸ OFF"
                gesture = s.current_gesture
                conf    = f"{s.confidence:.0%}"
                cursor  = f"{s.cursor_pos[0]}, {s.cursor_pos[1]}"

            self._var_hand.set(hand)
            self._var_ctrl.set(ctrl)
            self._var_gesture.set(gesture)
            self._var_conf.set(conf)
            self._var_cursor.set(cursor)

            if s.shutdown_requested:
                self._root.destroy()
                return
        except Exception:
            pass

        self._root.after(200, self._poll_status)

    # ─────────────────────────────────────────────────────────────────────────
    def _restore_defaults(self) -> None:
        defaults = {
            "smoothing":          config.CURSOR_SMOOTHING,
            "dead_zone":          config.CURSOR_DEAD_ZONE,
            "scroll_sensitivity": config.SCROLL_SENSITIVITY,
            "active_x1":          config.ACTIVE_REGION_X1,
            "active_x2":          config.ACTIVE_REGION_X2,
            "active_y1":          config.ACTIVE_REGION_Y1,
            "active_y2":          config.ACTIVE_REGION_Y2,
        }
        with self._state._lock:
            for attr, val in defaults.items():
                setattr(self._state, attr, val)
                if attr in self._sliders:
                    self._sliders[attr].set(val)
        log.info("Settings restored to defaults.")

    def _on_close(self) -> None:
        self._state.request_shutdown()
        if self._root:
            self._root.destroy()
