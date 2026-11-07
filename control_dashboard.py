"""Integrated Gesture-Cursor desktop dashboard (Tkinter + OpenCV + MediaPipe)."""
import json
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from pathlib import Path
from urllib.parse import quote

import cv2
from PIL import Image, ImageSequence, ImageTk

import config
from gesture_controller import GestureController
from hand_tracker import HandTracker
from mouse_controller import MouseController
from utils import FPSCounter, draw_hud

APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / "gesture_settings.json"

DEFAULTS = {
    "smoothness": 5,
    "settings_version": 2,
    "cursor_sensitivity": 100,    # percentage
    "scroll_distance": 70,        # camera pixels
    "scroll_cooldown": 350,       # milliseconds
    "show_camera_panel": True,
    "smart_controls_enabled": True,
}

# Brighter charcoal with vivid red, gold and green accents.
BG, SIDEBAR, PANEL, PANEL2 = "#171416", "#211b1d", "#2b2325", "#382a2d"
TEXT, MUTED, ACCENT = "#fff8ed", "#d0c0b5", "#f1bd4d"
RED = "#e53946"
GOLD = "#f1bd4d"
GREEN = "#27ae60"
WHITE = "#ffffff"
RED_HOVER = "#bf2632"
GREEN_HOVER = "#1e8e4d"
PANEL_BORDER = "#76582f"
CREATOR_EMAIL = "antonynathish@gmail.com"


def load_settings():
    values = DEFAULTS.copy()
    try:
        if SETTINGS_FILE.exists():
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            legacy_smoothness = saved.get("smoothness")
            for key in values:
                if key in saved:
                    values[key] = saved[key]
            if legacy_smoothness is not None and saved.get("settings_version", 1) < 2:
                try:
                    old_percent = max(0, min(100, int(legacy_smoothness)))
                    values["smoothness"] = round(old_percent * 9 / 100) + 1
                except (TypeError, ValueError):
                    values["smoothness"] = DEFAULTS["smoothness"]
    except (OSError, json.JSONDecodeError):
        pass
    try:
        smoothness = int(values["smoothness"])
    except (TypeError, ValueError):
        smoothness = DEFAULTS["smoothness"]
    if smoothness < 1 or smoothness > 10:
        smoothness = round(max(0, min(100, smoothness)) * 9 / 100) + 1
    values["smoothness"] = smoothness
    if not isinstance(values["smart_controls_enabled"], bool):
        values["smart_controls_enabled"] = DEFAULTS["smart_controls_enabled"]
    return values


def save_settings(values):
    SETTINGS_FILE.write_text(json.dumps(values, indent=2), encoding="utf-8")


def apply_settings(values):
    """Apply UI values to the existing config module; changes take effect live."""
    smoothness = max(1, min(10, int(values["smoothness"])))
    config.SMOOTHING_FACTOR = 1.0 - ((smoothness - 1) / 9 * 0.88)
    config.CURSOR_SENSITIVITY = max(0.5, min(2.0, float(values["cursor_sensitivity"]) / 100.0))
    config.SCROLL_TRIGGER_DISTANCE = max(10, int(values["scroll_distance"]))
    config.SCROLL_COOLDOWN = max(0.1, int(values["scroll_cooldown"]) / 1000.0)


class GestureWorker(threading.Thread):
    """Owns camera/tracker/controller on a worker thread; publishes UI events via queue."""
    def __init__(self, events, stop_event, controls_enabled, controls_lock):
        super().__init__(daemon=False)
        self.events = events
        self.stop_event = stop_event
        self.controls_enabled = controls_enabled
        self.controls_lock = controls_lock

    def run(self):
        cap = None
        tracker = None
        mouse = None
        try:
            mouse = MouseController()
            cap = cv2.VideoCapture(config.CAMERA_INDEX)
            if not cap.isOpened():
                raise RuntimeError(
                    f"Cannot open webcam index {config.CAMERA_INDEX}. "
                    "Close other camera applications and check Windows camera permission."
                )
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            tracker = HandTracker()
            controller = GestureController(mouse, config.CAMERA_WIDTH, config.CAMERA_HEIGHT)
            fps = FPSCounter()
            last_telemetry = None
            self.events.put(("status", "RUNNING"))
            active_area = (
                config.FRAME_REDUCTION, config.FRAME_REDUCTION,
                config.CAMERA_WIDTH - config.FRAME_REDUCTION,
                config.CAMERA_HEIGHT - config.FRAME_REDUCTION,
            ) if config.SHOW_ACTIVE_AREA else None

            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.03)
                    continue
                frame = cv2.flip(frame, 1)
                landmarks, results = tracker.process(frame)
                with self.controls_lock:
                    controls_active = self.controls_enabled.is_set()
                    controller.update(landmarks if controls_active else None)
                action = controller.last_action if controls_active else "Controls OFF"

                if config.SHOW_LANDMARKS:
                    tracker.draw_landmarks(frame, results)
                draw_hud(
                    frame,
                    fps=fps.update() if config.SHOW_FPS else None,
                    action=action if config.SHOW_GESTURE_TEXT else None,
                    state=controller.state if config.SHOW_GESTURE_TEXT else None,
                    active_area=active_area,
                )
                self.events.put(("frame", frame.copy()))
                telemetry = {
                    "action": action,
                    "state": controller.state,
                    "hands": 1 if landmarks is not None else 0,
                }
                if telemetry != last_telemetry:
                    self.events.put(("telemetry", telemetry))
                    last_telemetry = telemetry
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            try:
                if mouse is not None:
                    try:
                        mouse.mouse_up()
                    except Exception as exc:
                        self.events.put(("error", f"Could not release mouse button: {exc}"))
                if tracker is not None:
                    try:
                        tracker.close()
                    except Exception as exc:
                        self.events.put(("error", f"Could not close hand tracker: {exc}"))
                if cap is not None:
                    try:
                        cap.release()
                    except Exception as exc:
                        self.events.put(("error", f"Could not release webcam: {exc}"))
            finally:
                self.events.put(("status", "STOPPED"))


class GestureDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gesture-Cursor | Dashboard")
        self.geometry("1160x790")
        self.minsize(760, 560)
        self.configure(bg=BG)
        self.settings = load_settings()
        apply_settings(self.settings)
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.controls_enabled = threading.Event()
        self.controls_lock = threading.Lock()
        self.smart_controls_enabled = self.settings["smart_controls_enabled"]
        if self.smart_controls_enabled:
            self.controls_enabled.set()
        self.worker = None
        self.photo = None
        self.camera_error = False
        self.camera_visible = bool(self.settings["show_camera_panel"])
        self.engine_status = "Stopped"
        self.current_gesture = "Waiting for a hand"
        self.closing = False
        self.current_page = "Dashboard"
        self.tutorial_active = False
        self.tutorial_after_id = None
        self.tutorial_frames = []
        self.tutorial_delays = []
        self.tutorial_frame_index = 0
        self.tutorial_photo = None
        self.tutorial_thumbnail_refs = []
        self.status_value = None
        self.camera_status_value = None
        self.controls_status_value = None
        self.gesture_value = None
        self._styles()
        self._build_shell()
        self.show_page("Dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60, self._poll_events)
        self.after_idle(self.start_engine)

    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", font=("Segoe UI", 10))
        s.configure("Nav.TButton", background=SIDEBAR, foreground=MUTED,
                    borderwidth=0, padding=(14, 12), anchor="w", focuscolor=SIDEBAR)
        s.map("Nav.TButton", background=[("active", PANEL2)],
              foreground=[("active", TEXT)])
        s.configure("Nav.Active.TButton", background=PANEL2, foreground=GOLD,
                    borderwidth=0, padding=(14, 12), anchor="w", focuscolor=PANEL2)
        s.map("Nav.Active.TButton", background=[("active", PANEL2)],
              foreground=[("active", GOLD)])
        s.configure(
            "Page.Vertical.TScrollbar", background=PANEL2, troughcolor=BG,
            bordercolor=BG, arrowcolor=GOLD,
        )

    def _build_shell(self):
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=218)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="◉  GESTURE", bg=SIDEBAR, fg=GOLD,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=20, pady=(25, 2))
        tk.Label(self.sidebar, text="CURSOR CONTROL", bg=SIDEBAR, fg=RED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22, pady=(0, 28))
        self.nav = {}
        self.nav_indicators = {}
        for page, glyph in [("Dashboard", "⌂"), ("Edit", "⚙"), ("Controls", "✋"),
                            ("Privacy & Policy", "▣"), ("About", "ⓘ")]:
            row = tk.Frame(self.sidebar, bg=SIDEBAR)
            row.pack(fill="x", padx=10, pady=3)
            indicator = tk.Frame(row, width=3, bg=SIDEBAR)
            indicator.pack(side="left", fill="y")
            b = ttk.Button(row, text=f"{glyph}   {page}", style="Nav.TButton",
                           command=lambda p=page: self.show_page(p))
            b.pack(side="left", fill="x", expand=True)
            self.nav[page] = b
            self.nav_indicators[page] = indicator

        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        head = tk.Frame(self.main, bg=BG)
        head.pack(fill="x", padx=28, pady=(24, 15))
        self.page_title = tk.Label(head, text="", bg=BG, fg=TEXT,
                                   font=("Segoe UI", 23, "bold"))
        self.page_title.pack(side="left", anchor="w")
        self.header_actions = tk.Frame(head, bg=BG)
        self.header_actions.pack(side="right")
        self.smart_controls_button = tk.Button(
            self.header_actions,
            command=self.toggle_smart_controls,
            relief="flat", borderwidth=0, padx=13, pady=9,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        self.smart_controls_button.pack(side="left", padx=(0, 9))
        self.close_button = self._action_button(
            self.header_actions, "✕  CLOSE SMART GESTURE",
            self._on_close, RED, RED_HOVER,
        )
        self.close_button.pack(side="left")
        self._refresh_smart_controls_button()
        self.camera_card = tk.Frame(
            self.main, bg=PANEL, highlightthickness=1, highlightbackground=GOLD
        )
        self.camera_card.pack(
            side="bottom", anchor="center", padx=28, pady=(0, 22)
        )
        self.camera_card.pack_propagate(False)

        camera_header = tk.Frame(self.camera_card, bg=PANEL)
        camera_header.pack(fill="x", padx=14, pady=(9, 6))
        tk.Label(
            camera_header, text="CAMERA PREVIEW", bg=PANEL, fg=GOLD,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")
        self.camera_toggle_button = tk.Button(
            camera_header,
            text="PREVIEW ON" if self.camera_visible else "PREVIEW OFF",
            command=self.toggle_camera,
            bg=GREEN if self.camera_visible else RED, fg=WHITE,
            activebackground=GREEN if self.camera_visible else RED_HOVER,
            activeforeground=WHITE,
            relief="flat", borderwidth=0, padx=10, pady=5,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        self.camera_toggle_button.bind("<Enter>", self._camera_toggle_hover)
        self.camera_toggle_button.bind("<Leave>", self._camera_toggle_hover)
        self.camera_toggle_button.pack(side="right")

        self.preview_frame = tk.Frame(self.camera_card, bg="#000000")
        self.preview_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.preview = tk.Label(
            self.preview_frame,
            text="Connecting to camera..." if self.camera_visible else "CAMERA PREVIEW OFF",
            bg="#000000", fg="#756a58",
            font=("Segoe UI", 11)
        )
        self.preview.pack(fill="both", expand=True)
        self.page_area = tk.Frame(self.main, bg=BG)
        self.page_area.pack(fill="both", expand=True, padx=28, pady=(0, 10))
        self.page_canvas = tk.Canvas(
            self.page_area, bg=BG, highlightthickness=0, borderwidth=0
        )
        self.page_scrollbar = ttk.Scrollbar(
            self.page_area, orient="vertical", command=self.page_canvas.yview,
            style="Page.Vertical.TScrollbar",
        )
        self.page_canvas.configure(yscrollcommand=self.page_scrollbar.set)
        self.page_canvas.pack(side="left", fill="both", expand=True)
        self.page_scrollbar.pack(side="right", fill="y")
        self.content = tk.Frame(self.page_canvas, bg=BG)
        self.content_window = self.page_canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self.content.bind("<Configure>", self._update_scroll_region)
        self.page_canvas.bind("<Configure>", self._resize_content)
        self.page_canvas.bind_all("<MouseWheel>", self._scroll_page)
        self.main.bind("<Configure>", self._resize_camera_container)
        self.after_idle(self._resize_camera_container)

    def _clear(self):
        for child in self.content.winfo_children():
            child.destroy()
        self.tutorial_thumbnail_refs.clear()
        self.wrap_labels = []
        self.status_value = None
        self.camera_status_value = None
        self.controls_status_value = None
        self.gesture_value = None

    def _card(self, parent, title=None):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=PANEL_BORDER)
        if title:
            tk.Label(f, text=title, bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(13, 8))
        return f

    def _body_label(self, parent, text, **kwargs):
        background = kwargs.pop("bg", BG)
        foreground = kwargs.pop("fg", TEXT)
        font = kwargs.pop("font", ("Segoe UI", 10))
        justify = kwargs.pop("justify", "left")
        anchor = kwargs.pop("anchor", "w")
        label = tk.Label(
            parent, text=text, bg=background, fg=foreground,
            justify=justify, anchor=anchor, font=font, **kwargs,
        )
        self.wrap_labels.append(label)
        return label

    def _section_title(self, parent, text, **pack_options):
        title = tk.Label(
            parent, text=text, bg=BG, fg=GOLD,
            font=("Segoe UI", 12, "bold"), anchor="w",
        )
        title.pack(fill="x", **pack_options)
        return title

    def _action_button(self, parent, text, command, background, hover, **options):
        button = tk.Button(
            parent, text=text, command=command, bg=background, fg=WHITE,
            activebackground=hover, activeforeground=WHITE,
            relief="flat", borderwidth=0, padx=14, pady=9,
            font=("Segoe UI", 10, "bold"), cursor="hand2", **options,
        )
        button.bind("<Enter>", lambda _event: button.configure(bg=hover))
        button.bind("<Leave>", lambda _event: button.configure(bg=background))
        return button

    def show_page(self, page):
        if page not in self.nav:
            raise ValueError(f"Unknown page: {page}")
        if self.tutorial_active:
            self._exit_tutorial(refresh_controls=False)
        self.current_page = page
        self.page_title.config(text=page)
        for name, button in self.nav.items():
            button.configure(
                style="Nav.Active.TButton" if name == page else "Nav.TButton"
            )
            self.nav_indicators[name].configure(
                bg=RED if name == page else SIDEBAR
            )
        self._clear()
        self.page_canvas.yview_moveto(0)
        {
            "Dashboard": self._dashboard,
            "Edit": self._edit,
            "Controls": self._controls,
            "Privacy & Policy": self._privacy,
            "About": self._about,
        }[page]()
        self._update_scroll_region()

    def _resize_content(self, event):
        self.page_canvas.itemconfigure(self.content_window, width=event.width)
        wraplength = max(300, event.width - 44)
        for label in self.wrap_labels:
            label.configure(wraplength=wraplength)
        self._update_scroll_region()

    def _update_scroll_region(self, _event=None):
        self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))

    def _scroll_page(self, event):
        if self.page_canvas.winfo_exists():
            self.page_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _dashboard(self):
        tk.Label(
            self.content, text="SMART GESTURE", bg=BG, fg=GOLD,
            font=("Segoe UI", 27, "bold"),
        ).pack(anchor="w", pady=(8, 3))
        self._body_label(
            self.content, "Control your computer using natural hand gestures.",
            fg=MUTED, font=("Segoe UI", 12),
        ).pack(anchor="w", pady=(0, 22))

        self._section_title(self.content, "APPLICATION STATUS", pady=(0, 6))
        self.status_value = tk.Label(
            self.content, text=self.engine_status, bg=BG, fg=RED,
            font=("Segoe UI", 11, "bold"),
        )
        self.status_value.pack(anchor="w", pady=(0, 16))

        self._section_title(self.content, "CAMERA PREVIEW STATUS", pady=(0, 6))
        self.camera_status_value = tk.Label(
            self.content, text="ON" if self.camera_visible else "OFF",
            bg=BG, fg=GREEN if self.camera_visible else RED,
            font=("Segoe UI", 11, "bold"),
        )
        self.camera_status_value.pack(anchor="w", pady=(0, 16))

        self._section_title(self.content, "SMART CONTROLS", pady=(0, 6))
        self.controls_status_value = tk.Label(
            self.content,
            text="ON" if self.smart_controls_enabled else "OFF",
            bg=BG, fg=GREEN if self.smart_controls_enabled else RED,
            font=("Segoe UI", 11, "bold"),
        )
        self.controls_status_value.pack(anchor="w", pady=(0, 16))

        self._section_title(self.content, "CURRENT GESTURE", pady=(0, 6))
        self.gesture_value = tk.Label(
            self.content, text=self.current_gesture, bg=BG, fg=TEXT,
            font=("Segoe UI", 11),
        )
        self.gesture_value.pack(anchor="w", pady=(0, 22))

    def _refresh_smart_controls_button(self):
        state = "ON" if self.smart_controls_enabled else "OFF"
        color = GREEN if self.smart_controls_enabled else RED
        hover = GREEN_HOVER if self.smart_controls_enabled else RED_HOVER
        self.smart_controls_button.configure(
            text=f"SMART CONTROLS: {state}",
            bg=color, fg=WHITE, activebackground=hover, activeforeground=WHITE,
        )
        self.smart_controls_button.bind(
            "<Enter>", lambda _event: self.smart_controls_button.configure(bg=hover)
        )
        self.smart_controls_button.bind(
            "<Leave>", lambda _event: self.smart_controls_button.configure(bg=color)
        )

    def toggle_smart_controls(self):
        with self.controls_lock:
            self.smart_controls_enabled = not self.smart_controls_enabled
            self.settings["smart_controls_enabled"] = self.smart_controls_enabled
            if self.smart_controls_enabled:
                self.controls_enabled.set()
            else:
                self.controls_enabled.clear()
        self._refresh_smart_controls_button()
        if self.controls_status_value is not None and self.controls_status_value.winfo_exists():
            self.controls_status_value.configure(
                text="ON" if self.smart_controls_enabled else "OFF",
                fg=GREEN if self.smart_controls_enabled else RED,
            )
        self._save()

    def _resize_camera_container(self, _event=None):
        main_width = self.main.winfo_width()
        if main_width < 1:
            return
        if self.tutorial_active:
            card_width = min(300, max(220, int(main_width * 0.28)))
            stage_width = card_width - 30
            stage_height = max(
                100,
                int(stage_width * config.CAMERA_HEIGHT / config.CAMERA_WIDTH),
            )
            card_height = stage_height + 66
            self.camera_card.configure(width=card_width, height=card_height)
            self.preview_frame.configure(height=stage_height)
            self.camera_card.place_configure(
                relx=1.0, rely=1.0, anchor="se", x=-18, y=-18,
                width=card_width, height=card_height,
            )
            self._resize_tutorial_image()
            return
        card_width = max(300, min(680, main_width - 56))
        stage_width = card_width - 30
        stage_height = min(
            350,
            int(stage_width * config.CAMERA_HEIGHT / config.CAMERA_WIDTH),
        )
        self.camera_card.configure(
            width=card_width, height=stage_height + 66
        )
        self.preview_frame.configure(height=stage_height)

    def _update_camera_status(self):
        background = GREEN if self.camera_visible else RED
        self.camera_toggle_button.configure(
            text="PREVIEW ON" if self.camera_visible else "PREVIEW OFF",
            bg=background, activebackground=background if self.camera_visible else RED_HOVER,
            fg=WHITE, activeforeground=WHITE,
        )

    def _camera_toggle_hover(self, event):
        self._update_camera_status()
        if event.type == tk.EventType.Enter:
            hover = GREEN_HOVER if self.camera_visible else RED_HOVER
            self.camera_toggle_button.configure(bg=hover)

    def _edit(self):
        self._section_title(self.content, "Cursor Smoothness", pady=(8, 8))
        self._body_label(
            self.content,
            "Adjust how smoothly the cursor follows your hand movement.",
            fg=MUTED, font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(0, 18))
        slider_row = tk.Frame(self.content, bg=BG)
        slider_row.pack(fill="x", pady=(0, 8))
        self.smoothness_value = tk.IntVar(value=self.settings["smoothness"])
        self.smoothness_slider = tk.Scale(
            slider_row, from_=1, to=10, orient="horizontal", resolution=1,
            showvalue=False, variable=self.smoothness_value,
            bg=BG, fg=TEXT,
            troughcolor=PANEL2, activebackground=GOLD,
            highlightthickness=0, bd=0, length=360,
        )
        self.smoothness_slider.pack(side="left", fill="x", expand=True)
        self.smoothness_label = tk.Label(
            slider_row, text=str(self.settings["smoothness"]),
            bg=BG, fg=GOLD, font=("Segoe UI", 14, "bold"), width=3,
        )
        self.smoothness_label.pack(side="left", padx=(12, 0))
        self.smoothness_value.trace_add("write", self._smoothness_changed)
        self._body_label(
            self.content,
            "Lower values respond faster but may produce more jitter. Higher values "
            "reduce cursor jitter but may add movement delay.",
            fg=MUTED,
        ).pack(anchor="w", pady=(4, 20))
        self._action_button(
            self.content, "Reset Default", self._reset_smoothness, PANEL2, RED,
        ).pack(anchor="w")

    def _set_smoothness(self, raw_value):
        value = max(1, min(10, int(round(float(raw_value)))))
        self.settings["smoothness"] = value
        if hasattr(self, "smoothness_label") and self.smoothness_label.winfo_exists():
            self.smoothness_label.configure(text=str(value))
        apply_settings(self.settings)
        self._save()

    def _smoothness_changed(self, *_args):
        self._set_smoothness(self.smoothness_value.get())

    def _reset_smoothness(self):
        self.smoothness_slider.set(DEFAULTS["smoothness"])
        self._set_smoothness(DEFAULTS["smoothness"])

    def _save(self):
        try:
            save_settings(self.settings)
        except OSError as exc:
            messagebox.showerror("Could not save settings", str(exc))

    def toggle_camera(self):
        self.camera_visible = not self.camera_visible
        self.settings["show_camera_panel"] = self.camera_visible
        self._save()
        self.photo = None
        if self.camera_visible:
            placeholder = "Camera unavailable" if self.camera_error else "Connecting to camera..."
        else:
            placeholder = "CAMERA PREVIEW OFF"
        self.preview.configure(image="", text=placeholder)
        self._update_camera_status()
        if self.camera_status_value is not None and self.camera_status_value.winfo_exists():
            self.camera_status_value.configure(
                text="ON" if self.camera_visible else "OFF",
                fg=GREEN if self.camera_visible else RED,
            )

    def _controls(self):
        self._section_title(self.content, "Gesture Tutorials", pady=(4, 5))
        self._body_label(
            self.content,
            "Choose a tutorial to watch an animated guide to each gesture.",
            fg=MUTED,
        ).pack(fill="x", pady=(0, 12))

        for item in self._discover_tutorials():
            card = self._card(self.content)
            card.pack(fill="x", pady=6)
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x", padx=12, pady=12)
            thumbnail_box = tk.Frame(
                row, bg="#080808", width=176, height=100,
                highlightthickness=1, highlightbackground=PANEL_BORDER,
            )
            thumbnail_box.pack(side="left", padx=(0, 14))
            thumbnail_box.pack_propagate(False)
            thumbnail = tk.Label(
                thumbnail_box, text="Tutorial GIF unavailable",
                bg="#080808", fg=MUTED, font=("Segoe UI", 9),
                wraplength=150, justify="center",
            )
            thumbnail.pack(fill="both", expand=True)
            if item["path"] is not None:
                preview_image = None
                try:
                    with Image.open(item["path"]) as gif:
                        preview_image = next(ImageSequence.Iterator(gif)).convert("RGBA")
                        preview_image.thumbnail((168, 92), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(preview_image)
                        thumbnail.configure(image=photo, text="")
                        thumbnail.image = photo
                        self.tutorial_thumbnail_refs.append(photo)
                except (OSError, EOFError, StopIteration):
                    item["path"] = None
                finally:
                    if preview_image is not None:
                        preview_image.close()

            details = tk.Frame(row, bg=PANEL)
            details.pack(side="left", fill="both", expand=True)
            tk.Label(
                details, text=item["title"], bg=PANEL, fg=GOLD,
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", pady=(4, 7))
            description = item["description"]
            if item["path"] is None:
                description += " The tutorial GIF is currently unavailable."
            tk.Label(
                details, text=description, bg=PANEL, fg=MUTED,
                font=("Segoe UI", 10), justify="left", anchor="w",
                wraplength=520,
            ).pack(anchor="w", fill="x", pady=(0, 8))
            self._action_button(
                details, "Watch Tutorial",
                lambda tutorial=item: self._open_tutorial(tutorial),
                RED, RED_HOVER,
            ).pack(anchor="w")

    def _discover_tutorials(self):
        definitions = [
            (
                "cursor", "Index Finger – Cursor Movement",
                "Extend the index finger while keeping the middle finger folded, then move your hand to guide the cursor.",
                ("cursormoveindex", "cursormovement", "indexfinger", "cursor"),
            ),
            (
                "left", "Left Click",
                "Quickly pinch the thumb and index fingertips together, then release.",
                ("leftclick",),
            ),
            (
                "right", "Right Click",
                "Pinch the thumb, index, and middle fingertips together.",
                ("rightclick",),
            ),
            (
                "scroll", "Scroll Up and Down",
                "Extend the index and middle fingers together, then move your hand vertically.",
                ("scroll",),
            ),
            (
                "drag", "Drag and Drop",
                "Hold a thumb-index pinch to drag, move your hand, and release to drop.",
                ("draganddrop", "drag"),
            ),
        ]
        controls_dir = next(
            (
                path for path in APP_DIR.iterdir()
                if path.is_dir() and path.name.casefold() == "controls"
            ),
            None,
        )
        gif_paths = (
            sorted(
                (path for path in controls_dir.iterdir()
                 if path.is_file() and path.suffix.casefold() == ".gif"),
                key=lambda path: path.name.casefold(),
            )
            if controls_dir is not None else []
        )
        unused_paths = set(gif_paths)
        items = []
        for key, title, description, aliases in definitions:
            path = next(
                (
                    candidate for candidate in gif_paths
                    if candidate in unused_paths
                    and any(alias in "".join(
                        character for character in candidate.stem.casefold()
                        if character.isalnum()
                    ) for alias in aliases)
                ),
                None,
            )
            if path is not None:
                unused_paths.remove(path)
            items.append({
                "key": key,
                "title": title,
                "description": description,
                "path": path,
            })
        for path in sorted(unused_paths, key=lambda candidate: candidate.name.casefold()):
            title = path.stem.replace("_", " ").replace("-", " ").title()
            items.append({
                "key": path.stem,
                "title": title,
                "description": "Watch the animation to learn this gesture.",
                "path": path,
            })
        return items

    def _open_tutorial(self, item):
        if self.tutorial_active:
            self._stop_tutorial_animation()
            if hasattr(self, "tutorial_view") and self.tutorial_view.winfo_exists():
                self.tutorial_view.destroy()
        self.tutorial_active = True
        self.page_title.configure(text=item["title"])
        self.sidebar.pack_forget()
        self.page_area.pack_forget()
        self.camera_card.pack_forget()
        self.tutorial_view = tk.Frame(self.main, bg=BG)
        self.tutorial_view.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.tutorial_column = tk.Frame(self.tutorial_view, bg=BG)
        self.tutorial_column.pack(side="left", fill="both", expand=True)
        camera_space = tk.Frame(self.tutorial_view, bg=BG, width=300)
        camera_space.pack(side="right", fill="y")
        camera_space.pack_propagate(False)
        self.tutorial_card = tk.Frame(
            self.tutorial_column, bg=PANEL, highlightthickness=1,
            highlightbackground=PANEL_BORDER,
        )
        self.tutorial_card.pack(fill="both", expand=True, pady=(0, 12))
        self.tutorial_image_label = tk.Label(
            self.tutorial_card, text="Loading tutorial...",
            bg="#080808", fg=MUTED, font=("Segoe UI", 12),
        )
        self.tutorial_image_label.pack(fill="both", expand=True, padx=14, pady=(14, 8))
        self.tutorial_image_label.bind("<Configure>", self._resize_tutorial_image)
        tk.Label(
            self.tutorial_card, text=item["description"], bg=PANEL,
            fg=TEXT, justify="left", anchor="w",
            font=("Segoe UI", 11), wraplength=760,
        ).pack(fill="x", padx=18, pady=(4, 16))
        close_button = tk.Button(
            self.tutorial_column, text="✕", command=self.close_tutorial,
            bg=RED, fg=WHITE, activebackground=RED_HOVER,
            activeforeground=WHITE, relief="flat", borderwidth=0,
            width=3, height=1, padx=8, pady=5,
            font=("Segoe UI", 16, "bold"), cursor="hand2",
        )
        close_button.pack(pady=(0, 4))
        close_button.bind("<Enter>", lambda _event: close_button.configure(bg=RED_HOVER))
        close_button.bind("<Leave>", lambda _event: close_button.configure(bg=RED))
        self.camera_card.place(
            relx=1.0, rely=1.0, anchor="se", x=-18, y=-18,
            width=280, height=224,
        )
        self.main.bind("<Configure>", self._resize_camera_container)
        self._resize_camera_container()
        self._load_tutorial_animation(item["path"])

    def _load_tutorial_animation(self, path):
        if path is None:
            self.tutorial_image_label.configure(
                text="This tutorial GIF is unavailable.", image="",
            )
            return
        frames = []
        delays = []
        try:
            with Image.open(path) as gif:
                default_delay = gif.info.get("duration", 100)
                for frame in ImageSequence.Iterator(gif):
                    frames.append(frame.convert("RGBA"))
                    delays.append(max(20, int(frame.info.get("duration", default_delay))))
        except (OSError, EOFError) as exc:
            self.tutorial_image_label.configure(
                text=f"Could not load this tutorial GIF:\n{exc}", image="",
            )
            return
        if not frames:
            self.tutorial_image_label.configure(
                text="This tutorial GIF contains no frames.", image="",
            )
            return
        self.tutorial_frames = frames
        self.tutorial_delays = delays
        self.tutorial_frame_index = 0
        self._show_tutorial_frame()

    def _resize_tutorial_image(self, _event=None):
        if self.tutorial_active and self.tutorial_frames:
            self._show_tutorial_frame(schedule=False)

    def _show_tutorial_frame(self, schedule=True):
        if not self.tutorial_active or not self.tutorial_frames:
            return
        frame = self.tutorial_frames[self.tutorial_frame_index]
        max_width = max(1, self.tutorial_image_label.winfo_width() - 8)
        max_height = max(1, self.tutorial_image_label.winfo_height() - 8)
        display_frame = frame.copy()
        display_frame.thumbnail(
            (max_width, max_height), Image.Resampling.LANCZOS
        )
        self.tutorial_photo = ImageTk.PhotoImage(display_frame)
        display_frame.close()
        self.tutorial_image_label.configure(image=self.tutorial_photo, text="")
        if schedule:
            delay = self.tutorial_delays[self.tutorial_frame_index]
            self.tutorial_frame_index = (
                self.tutorial_frame_index + 1
            ) % len(self.tutorial_frames)
            self.tutorial_after_id = self.after(
                delay, self._show_tutorial_frame
            )

    def _stop_tutorial_animation(self):
        if self.tutorial_after_id is not None:
            try:
                self.after_cancel(self.tutorial_after_id)
            except tk.TclError:
                pass
            self.tutorial_after_id = None
        for frame in self.tutorial_frames:
            frame.close()
        self.tutorial_frames.clear()
        self.tutorial_delays.clear()
        self.tutorial_photo = None

    def close_tutorial(self):
        self._exit_tutorial(refresh_controls=True)

    def _exit_tutorial(self, refresh_controls):
        self._stop_tutorial_animation()
        self.tutorial_active = False
        self.main.unbind("<Configure>")
        if hasattr(self, "tutorial_view") and self.tutorial_view.winfo_exists():
            self.tutorial_view.destroy()
        self.camera_card.place_forget()
        self.sidebar.pack(side="left", fill="y", before=self.main)
        self.camera_card.pack(
            side="bottom", anchor="center", padx=28, pady=(0, 22)
        )
        self.page_area.pack(fill="both", expand=True, padx=28, pady=(0, 10))
        self.main.bind("<Configure>", self._resize_camera_container)
        self._resize_camera_container()
        if refresh_controls:
            self.show_page("Controls")

    def _privacy(self):
        self._section_title(self.content, "Privacy Policy – Smart Gesture", pady=(8, 10))
        sections = [
            ("1. Introduction", [
                "Smart Gesture is a desktop application that allows users to control their computer using hand gestures captured through a webcam.",
            ]),
            ("2. Camera Access", [
                "The application uses the webcam for real-time hand detection and gesture recognition.",
                "Camera access is required for gesture-control functionality.",
                "Users can turn the camera preview ON or OFF using the application controls. Turning the preview OFF hides the image; tracking continues until the application is closed.",
                "The camera can be stopped by closing the application.",
            ]),
            ("3. Image and Video Processing", [
                "Webcam frames are processed locally on the user's computer.",
                "The application is designed to perform gesture recognition without uploading webcam footage to an external server.",
                "The application does not implement cloud image processing or external video transmission.",
            ]),
            ("4. Data Collection", [
                "Smart Gesture does not intentionally collect personal information.",
                "It does not require user registration or an account.",
                "The application does not include analytics or tracking services.",
            ]),
            ("5. Data Storage", [
                "Only application configuration and settings required for functionality may be stored locally.",
                "The application does not store webcam recordings or captured images.",
            ]),
            ("6. Third-Party Libraries", [
                "The application uses third-party open-source libraries such as Python, OpenCV, MediaPipe, and PyAutoGUI. Their respective licenses and privacy practices apply.",
            ]),
            ("7. User Control", [
                "Users can disable the camera preview or close Smart Gesture whenever they want. Disabling the preview does not stop camera capture or gesture tracking.",
            ]),
            ("8. Contact", [
                "For privacy-related questions, contact:",
            ]),
            ("9. Policy Updates", [
                "The privacy policy may be updated when application features or functionality change.",
            ]),
        ]
        for heading, paragraphs in sections:
            self._section_title(self.content, heading, pady=(12, 4))
            for paragraph in paragraphs:
                self._body_label(self.content, "• " + paragraph, fg=MUTED).pack(
                    fill="x", pady=(0, 4)
                )
            if heading == "8. Contact":
                self._email_link(self.content, pady=(0, 4))

    def _about(self):
        tk.Label(
            self.content, text="SMART GESTURE", bg=BG, fg=GOLD,
            font=("Segoe UI", 23, "bold"),
        ).pack(anchor="w", pady=(8, 3))
        self._body_label(
            self.content, "Control Your Computer with Hand Gestures",
            fg=TEXT, font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        self._body_label(
            self.content,
            "Smart Gesture is a Python-based desktop application that uses computer "
            "vision and hand tracking to control mouse operations through natural "
            "hand movements.",
            fg=MUTED,
        ).pack(fill="x", pady=(0, 16))

        self._section_title(self.content, "Key Features", pady=(4, 5))
        for feature in (
            "Hand tracking using a webcam.",
            "Gesture-based cursor movement.",
            "Gesture-based left and right clicks.",
            "Drag-and-drop interaction.",
            "Gesture-based scrolling.",
            "Adjustable cursor smoothness.",
            "Real-time camera preview.",
        ):
            self._body_label(self.content, "• " + feature, fg=MUTED).pack(
                fill="x", pady=2
            )

        self._section_title(self.content, "Technologies Used", pady=(16, 5))
        self._body_label(
            self.content, "Python · OpenCV · MediaPipe · PyAutoGUI · Tkinter",
            fg=MUTED,
        ).pack(fill="x", pady=(0, 14))

        self._section_title(self.content, "Project Creators", pady=(4, 5))
        team = self._card(self.content)
        team.pack(fill="x", pady=(0, 14))
        for name in (
            "Antony Arokia Nathish",
            "Mahendra Prasad",
            "Sanjay",
            "Pon Malar Selavan",
        ):
            tk.Label(
                team, text=name, bg=PANEL, fg=TEXT,
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=14, pady=5)

        self._section_title(self.content, "Project Information", pady=(4, 5))
        for detail in (
            "Project Name: Smart Gesture",
            "Project Type: Desktop Application",
            "Category: Computer Vision / Human-Computer Interaction",
            "Main Language: Python",
        ):
            self._body_label(self.content, detail, fg=MUTED).pack(
                fill="x", pady=2
            )

        self._section_title(self.content, "Further Information and Support", pady=(16, 5))
        self._body_label(self.content, "Documentation", fg=TEXT).pack(
            anchor="w", pady=(2, 4)
        )
        self._action_button(
            self.content, "Download README.md", self._open_readme, PANEL2, RED,
        ).pack(anchor="w", pady=(0, 10))
        self._action_button(
            self.content, "Report a Bug", self._report_bug, RED, RED_HOVER,
        ).pack(anchor="w", pady=(0, 10))
        self._email_link(self.content)

    def _email_link(self, parent, **pack_options):
        link = tk.Label(
            parent, text=f"Email: {CREATOR_EMAIL}", bg=BG, fg=GOLD,
            font=("Segoe UI", 10, "underline"), cursor="hand2",
        )
        link.bind("<Button-1>", lambda _event: self._open_email())
        link.pack(anchor="w", **pack_options)
        return link

    def _open_email(self, subject="", body=""):
        uri = f"mailto:{CREATOR_EMAIL}?subject={quote(subject, safe='')}&body={quote(body, safe='')}"
        try:
            opened = webbrowser.open(uri)
        except webbrowser.Error as exc:
            messagebox.showerror("Could not open email application", str(exc))
            return
        if not opened:
            messagebox.showerror(
                "Could not open email application",
                "No default email application could open the email draft.",
            )

    def _report_bug(self):
        body = (
            "Application Version:\n"
            "Operating System:\n"
            "Description of the Bug:\n"
            "Steps to Reproduce:\n"
            "Expected Result:\n"
            "Actual Result:\n"
        )
        self._open_email("Smart Gesture – Bug Report", body)

    def _readme_path(self):
        candidates = [APP_DIR / "README.md"]
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(Path(bundle_dir) / "README.md")
        candidates.append(Path(sys.executable).resolve().parent / "README.md")
        return next((path.resolve() for path in candidates if path.is_file()), None)

    def _open_readme(self):
        readme = self._readme_path()
        if readme is None:
            messagebox.showerror(
                "README not found",
                "README.md was not found beside the application or in its packaged files.",
            )
            return
        try:
            opened = webbrowser.open(readme.as_uri())
        except webbrowser.Error as exc:
            messagebox.showerror("Could not open README.md", str(exc))
            return
        if not opened:
            messagebox.showerror(
                "Could not open README.md",
                f"Open this file manually:\n{readme}",
            )

    def start_engine(self):
        if self.closing:
            return
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        self.camera_error = False
        self.engine_status = "Stopped"
        self._refresh_dashboard_status()
        apply_settings(self.settings)
        self.worker = GestureWorker(
            self.events, self.stop_event, self.controls_enabled,
            self.controls_lock,
        )
        self.worker.start()

    def stop_engine(self):
        self.stop_event.set()

    def _refresh_dashboard_status(self):
        if self.status_value is not None and self.status_value.winfo_exists():
            self.status_value.configure(
                text=self.engine_status,
                fg=GREEN if self.engine_status == "Running" else RED,
            )
        if self.camera_status_value is not None and self.camera_status_value.winfo_exists():
            self.camera_status_value.configure(
                text="ON" if self.camera_visible else "OFF",
                fg=GREEN if self.camera_visible else RED,
            )
        if self.controls_status_value is not None and self.controls_status_value.winfo_exists():
            self.controls_status_value.configure(
                text="ON" if self.smart_controls_enabled else "OFF",
                fg=GREEN if self.smart_controls_enabled else RED,
            )

    def _poll_events(self):
        if self.closing:
            return
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "status":
                    if data == "RUNNING":
                        self.engine_status = "Running"
                        self.camera_error = False
                        if self.camera_visible and self.photo is None:
                            self.preview.configure(text="Connecting to camera...")
                    else:
                        self.engine_status = "Stopped"
                        if self.camera_visible and self.photo is None:
                            self.preview.configure(text="Camera unavailable" if self.camera_error else "Camera stopped")
                    self._refresh_dashboard_status()
                elif kind == "error":
                    self.camera_error = True
                    if self.camera_visible:
                        self.preview.configure(image="", text="Camera unavailable")
                    self.engine_status = "Stopped"
                    self._refresh_dashboard_status()
                    messagebox.showerror("Gesture engine error", data)
                elif kind == "telemetry":
                    self.current_gesture = data.get("action") or "Unknown"
                    if self.gesture_value is not None and self.gesture_value.winfo_exists():
                        self.gesture_value.configure(text=self.current_gesture)
                elif (kind == "frame" and self.camera_visible and self.preview is not None
                      and self.preview.winfo_exists()):
                    frame = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(frame)
                    max_w = max(1, self.preview.winfo_width())
                    max_h = max(1, self.preview.winfo_height())
                    image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                    self.photo = ImageTk.PhotoImage(image)
                    self.preview.configure(image=self.photo, text="")
        except queue.Empty:
            pass
        if not self.closing:
            self.after(60, self._poll_events)

    def _on_close(self):
        if self.closing:
            return
        if not messagebox.askyesno(
            "Close Smart Gesture",
            "Are you sure you want to close Smart Gesture?",
            parent=self,
        ):
            return
        self._stop_tutorial_animation()
        self.closing = True
        self.engine_status = "Stopped"
        self.stop_event.set()
        self._wait_for_worker_shutdown()

    def _wait_for_worker_shutdown(self):
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=0)
            if self.worker.is_alive():
                self.after(50, self._wait_for_worker_shutdown)
                return
        self.destroy()


if __name__ == "__main__":
    GestureDashboard().mainloop()
