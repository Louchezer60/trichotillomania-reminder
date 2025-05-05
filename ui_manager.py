import tkinter as tk
from tkinter import ttk, font, messagebox
import sv_ttk
from PIL import Image, ImageTk
import queue
import logging
from tkcalendar import Calendar
from typing import Callable
import numpy as np
from config_manager import Config, TempSettings
from stats_manager import PullingStats, StatsGraphManager
from resource_manager import ResourceManager
import os
import cv2

class UIManager:
    """Manages the application's unified Tkinter UI with scalable elements."""
    
    def __init__(self, config: Config, stats: PullingStats, on_quit: Callable, on_reset: Callable, audio_manager=None):
        self.config = config
        self.stats = stats
        self.on_quit = on_quit
        self.on_reset = on_reset
        self.audio_manager = audio_manager
        self.root = None
        self.video_frame = None
        self.video_label = None
        self.placeholder_label = None
        self.video_container = None
        self.video_area = None
        self.tabs_frame = None
        self.photo = None
        self.temp_settings = TempSettings(
            trigger_cooldown=config.detection['trigger_cooldown'],
            required_duration=config.detection['required_duration'],
            pull_threshold=config.detection['pull_threshold'],
            full_head_detection=config.detection.get('full_head_detection', False),
            show_meshes=config.detection.get('show_meshes', True)
        )
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = False
        self.video_width = 640
        self.video_height = 480
        self.title_font = None
        self.label_font = None
        self.status_label = None
        self.fps_label = None
        self.depth_label = None
        self.calendar = None
        self.trigger_label = None
        self.full_head_var = None
        self.show_meshes_var = None
        self.detection_mode_label = None
        self.current_theme = "dark"
        self.stats_graph_manager = None
        self.camera_initialized = False
        self.camera_error_label = None
        self.retry_button = None
        self._resize_after_id = None  # For debouncing resize events
    
    def initialize_ui(self) -> None:
        self.root = tk.Tk()
        self.root.title("Trichotillomania-Reminder : Hair-Pulling Detection System")
        self.root.geometry("1280x720")
        self.root.resizable(True, True)
        
        try:
            icon_path = ResourceManager.get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                logging.warning(f"Icon file not found at: {icon_path}")
        except Exception as e:
            logging.error(f"Error setting window icon: {e}")
        
        sv_ttk.set_theme(self.current_theme)
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.video_area = ttk.Frame(main_frame)
        self.video_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.video_container = ttk.LabelFrame(self.video_area, text="Live Feed", padding="5")
        self.video_container.pack(anchor=tk.CENTER)
        
        self.video_frame = ttk.Frame(self.video_container, style="Overlay.TFrame")
        self.video_frame.pack(padx=5, pady=5)
        
        self.placeholder_label = ttk.Label(
            self.video_frame,
            text="Camera not ready yet",
            foreground="white",
            background="black",
            font=("Segoe UI", 12),
            anchor=tk.CENTER,
            width=64
        )
        self.placeholder_label.pack()
        
        self.camera_error_label = ttk.Label(
            self.video_frame,
            text="Camera failed to initialize. Please check connection and retry.",
            foreground="red",
            background="black",
            font=("Segoe UI", 12),
            anchor=tk.CENTER,
            width=64
        )
        
        self.retry_button = ttk.Button(
            self.video_frame,
            text="Retry Camera",
            command=self._retry_camera,
            style="Accent.TButton"
        )
        
        self.video_label = ttk.Label(self.video_frame)
        
        style = ttk.Style()
        style.configure("Overlay.TFrame", background="#2e2e2e" if self.current_theme == "dark" else "#f0f0f0")
        
        self.video_container.configure(width=self.video_width + 20, height=self.video_height + 30)
        
        self.tabs_frame = ttk.Frame(main_frame)
        self.tabs_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        notebook = ttk.Notebook(self.tabs_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        settings_frame = ttk.Frame(notebook, padding="10")
        notebook.add(settings_frame, text="Settings")
        
        triggers_frame = ttk.Frame(notebook, padding="10")
        notebook.add(triggers_frame, text="Triggers")
        
        stats_tab = ttk.Frame(notebook, padding="10")
        notebook.add(stats_tab, text="Statistics")
        
        phrases_frame = ttk.Frame(notebook, padding="10")
        notebook.add(phrases_frame, text="Phrases")
        
        self.title_font = font.Font(family="Segoe UI", size=14, weight="bold")
        self.label_font = font.Font(family="Segoe UI", size=10)
        
        # Settings Tab
        self.title_label = ttk.Label(settings_frame, text="Settings", font=self.title_font)
        self.title_label.pack(pady=10)
        
        cooldown_var = tk.StringVar(value=str(self.temp_settings.trigger_cooldown))
        duration_var = tk.StringVar(value=f"{self.temp_settings.required_duration:.1f}")
        threshold_var = tk.StringVar(value=str(self.temp_settings.pull_threshold))
        
        cooldown_label = ttk.Label(settings_frame, text="Trigger Cooldown (s): Time between alerts", font=self.label_font)
        cooldown_label.pack(anchor=tk.W)
        cooldown_frame = ttk.Frame(settings_frame)
        cooldown_frame.pack(fill=tk.X, pady=5)
        cooldown_scale = ttk.Scale(cooldown_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                                 command=lambda x: [setattr(self.temp_settings, 'trigger_cooldown', int(float(x))),
                                                  cooldown_var.set(str(int(float(x))))])
        cooldown_scale.set(self.temp_settings.trigger_cooldown)
        cooldown_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(cooldown_frame, textvariable=cooldown_var, width=5, font=self.label_font).pack(side=tk.RIGHT, padx=5)
        
        duration_label = ttk.Label(settings_frame, text="Required Duration (s): Detection time", font=self.label_font)
        duration_label.pack(anchor=tk.W, pady=5)
        duration_frame = ttk.Frame(settings_frame)
        duration_frame.pack(fill=tk.X, pady=5)
        duration_scale = ttk.Scale(duration_frame, from_=0, to=5, orient=tk.HORIZONTAL,
                                  command=lambda x: [setattr(self.temp_settings, 'required_duration', float(x)),
                                                   duration_var.set(f"{float(x):.1f}")])
        duration_scale.set(self.temp_settings.required_duration)
        duration_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(duration_frame, textvariable=duration_var, width=5, font=self.label_font).pack(side=tk.RIGHT, padx=5)
        
        threshold_label = ttk.Label(settings_frame, text="Pull Threshold: Sensitivity", font=self.label_font)
        threshold_label.pack(anchor=tk.W, pady=5)
        threshold_frame = ttk.Frame(settings_frame)
        threshold_frame.pack(fill=tk.X, pady=5)
        threshold_scale = ttk.Scale(threshold_frame, from_=0, to=30, orient=tk.HORIZONTAL,
                                   command=lambda x: [setattr(self.temp_settings, 'pull_threshold', int(float(x))),
                                                    threshold_var.set(str(int(float(x))))])
        threshold_scale.set(self.temp_settings.pull_threshold)
        threshold_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(threshold_frame, textvariable=threshold_var, width=5, font=self.label_font).pack(side=tk.RIGHT, padx=5)
        
        checkbox_frame = ttk.Frame(settings_frame)
        checkbox_frame.pack(fill=tk.X, pady=10)

        self.full_head_var = tk.BooleanVar(value=self.temp_settings.full_head_detection)
        full_head_check = ttk.Checkbutton(
            checkbox_frame, 
            text="Full head detection (beard, eyebrows, etc.)", 
            variable=self.full_head_var,
            command=lambda: [
                setattr(self.temp_settings, 'full_head_detection', self.full_head_var.get()),
                self._update_detection_mode_label()
            ]
        )
        full_head_check.pack(anchor=tk.W, padx=5)

        self.show_meshes_var = tk.BooleanVar(value=self.temp_settings.show_meshes)
        show_meshes_check = ttk.Checkbutton(
            checkbox_frame,
            text="Show MediaPipe meshes",
            variable=self.show_meshes_var,
            command=lambda: [
                setattr(self.temp_settings, 'show_meshes', self.show_meshes_var.get()),
                self._update_detection_mode_label()
            ]
        )
        show_meshes_check.pack(anchor=tk.W, padx=5)

        action_buttons_frame = ttk.Frame(settings_frame)
        action_buttons_frame.pack(fill=tk.X, pady=10)

        save_button = ttk.Button(action_buttons_frame, text="Save Settings", 
                                command=self._save_settings, style="Accent.TButton")
        save_button.pack(side=tk.LEFT, padx=5)

        reset_button = ttk.Button(action_buttons_frame, text="Reset to Default", 
                                command=self._reset_settings)
        reset_button.pack(side=tk.LEFT, padx=5)

        app_controls_frame = ttk.Frame(settings_frame)
        app_controls_frame.pack(fill=tk.X, pady=10)

        theme_button = ttk.Button(app_controls_frame, text="Toggle Dark-Light Mode", 
                                command=self._toggle_theme, style="Accent.TButton")
        theme_button.pack(side=tk.LEFT, padx=5)

        quit_btn = ttk.Button(app_controls_frame, text="Quit", command=self.on_quit)
        quit_btn.pack(side=tk.RIGHT, padx=5)

        status_frame = ttk.Frame(settings_frame)
        status_frame.pack(fill=tk.X, pady=10)

        self.status_label = ttk.Label(status_frame, text="Ready", font=self.label_font)
        self.status_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.fps_label = ttk.Label(status_frame, text="FPS: --", font=self.label_font)
        self.fps_label.pack(side=tk.RIGHT, padx=5, pady=5)

        self.detection_mode_label = ttk.Label(settings_frame, text="", font=self.label_font)
        self.detection_mode_label.pack(pady=5)
        self._update_detection_mode_label()

        # Triggers Tab
        triggers_title = ttk.Label(triggers_frame, text="Triggers calendar", font=self.title_font)
        triggers_title.pack(pady=10)
        
        cal_frame = ttk.Frame(triggers_frame)
        cal_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.calendar = Calendar(
            cal_frame, 
            selectmode='day', 
            date_pattern='yyyy-mm-dd',
            locale='en_US', 
            cursor="hand1", 
            background='white',
            foreground='black',
            disabledbackground="#f0f0f0", 
            bordercolor="#d9d9d9",
            headersbackground="#f0f0f0", 
            normalbackground="#ffffff",
            headersforeground="black",
            normalforeground="black",
            selectbackground="black",
            font=("Segoe UI", 10)
        )
        self.calendar.pack(fill=tk.BOTH, expand=True)
        
        self.trigger_label = ttk.Label(triggers_frame, text="Select a date to see triggers", font=self.label_font)
        self.trigger_label.pack(pady=10)
        
        today_stats = ttk.Label(triggers_frame, text=self.stats.get_daily_report(), font=self.label_font)
        today_stats.pack(pady=5)
        
        self.calendar.bind("<<CalendarSelected>>", self._update_trigger_display)
        
        # Statistics Tab
        stats_title = ttk.Label(stats_tab, text="Statistics", font=self.title_font)
        stats_title.pack(pady=10)
        
        stats_content_frame = ttk.Frame(stats_tab, padding="10")
        stats_content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.stats_graph_manager = StatsGraphManager(self.stats, stats_content_frame)
        
        # Phrases Tab
        phrases_title = ttk.Label(phrases_frame, text="Motivational Phrases", font=self.title_font)
        phrases_title.pack(pady=10)
        
        phrases_list_frame = ttk.Frame(phrases_frame)
        phrases_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.phrases_listbox = tk.Listbox(phrases_list_frame, height=10, font=self.label_font)
        self.phrases_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        scrollbar = ttk.Scrollbar(phrases_list_frame, orient=tk.VERTICAL, command=self.phrases_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.phrases_listbox.config(yscrollcommand=scrollbar.set)
        
        if self.audio_manager:
            for phrase in self.audio_manager.phrases:
                self.phrases_listbox.insert(tk.END, phrase)
        
        phrase_entry_frame = ttk.Frame(phrases_frame)
        phrase_entry_frame.pack(fill=tk.X, pady=5)
        
        self.phrase_entry = ttk.Entry(phrase_entry_frame, font=self.label_font)
        self.phrase_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        phrases_buttons_frame = ttk.Frame(phrases_frame)
        phrases_buttons_frame.pack(fill=tk.X, pady=5)
        
        add_button = ttk.Button(phrases_buttons_frame, text="Add Phrase", command=self._add_phrase, style="Accent.TButton")
        add_button.pack(side=tk.LEFT, padx=5)
        
        edit_button = ttk.Button(phrases_buttons_frame, text="Edit Phrase", command=self._edit_phrase)
        edit_button.pack(side=tk.LEFT, padx=5)
        
        delete_button = ttk.Button(phrases_buttons_frame, text="Delete Phrase", command=self._delete_phrase)
        delete_button.pack(side=tk.LEFT, padx=5)
        
        save_phrases_button = ttk.Button(phrases_buttons_frame, text="Save Phrases", command=self._save_phrases, style="Accent.TButton")
        save_phrases_button.pack(side=tk.LEFT, padx=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Configure>", self._on_resize)
        self._update_detection_mode_label()
        self._update_layout()
    
    def _add_phrase(self) -> None:
        phrase = self.phrase_entry.get().strip()
        if not phrase:
            messagebox.showwarning("Invalid Input", "Please enter a non-empty phrase.")
            return
        self.phrases_listbox.insert(tk.END, phrase)
        self.phrase_entry.delete(0, tk.END)
        self.status_label.config(text="Phrase added")
    
    def _edit_phrase(self) -> None:
        selection = self.phrases_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a phrase to edit.")
            return
        new_phrase = self.phrase_entry.get().strip()
        if not new_phrase:
            messagebox.showwarning("Invalid Input", "Please enter a non-empty phrase.")
            return
        index = selection[0]
        self.phrases_listbox.delete(index)
        self.phrases_listbox.insert(index, new_phrase)
        self.phrase_entry.delete(0, tk.END)
        self.status_label.config(text="Phrase edited")
    
    def _delete_phrase(self) -> None:
        selection = self.phrases_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a phrase to delete.")
            return
        index = selection[0]
        self.phrases_listbox.delete(index)
        self.phrase_entry.delete(0, tk.END)
        self.status_label.config(text="Phrase deleted")
    
    def _save_phrases(self) -> None:
        phrases = list(self.phrases_listbox.get(0, tk.END))
        if not phrases:
            messagebox.showwarning("No Phrases", "At least one phrase is required.")
            return
        if self.audio_manager:
            self.audio_manager.save_phrases(phrases)
            self.status_label.config(text="Phrases saved")
        else:
            self.status_label.config(text="Error: AudioManager not available")
    
    def _toggle_theme(self) -> None:
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        sv_ttk.set_theme(self.current_theme)
        style = ttk.Style()
        style.configure("Overlay.TFrame", background="#2e2e2e" if self.current_theme == "dark" else "#f0f0f0")
        self.status_label.config(text=f"Switched to {self.current_theme} mode")
    
    def _update_detection_mode_label(self) -> None:
        mode_text = "Detection Mode: "
        if self.full_head_var.get():
            mode_text += "\n -Full head detection active (beard, eyebrows, etc.)"
        else:
            mode_text += "\n -Above eyes detection only"
        mode_text += "\n -MediaPipe meshes " + ("visible" if self.show_meshes_var.get() else "hidden")
        self.detection_mode_label.config(text=mode_text)
    
    def _save_settings(self) -> None:
        self.config.detection['trigger_cooldown'] = self.temp_settings.trigger_cooldown
        self.config.detection['required_duration'] = self.temp_settings.required_duration
        self.config.detection['pull_threshold'] = self.temp_settings.pull_threshold
        self.config.detection['full_head_detection'] = self.full_head_var.get()
        self.config.detection['show_meshes'] = self.show_meshes_var.get()
        self.status_label.config(text="Settings saved")
    
    def _reset_settings(self) -> None:
        self.on_reset()
        self.status_label.config(text="Settings reset to default")
    
    def _update_trigger_display(self, event=None) -> None:
        selected_date = self.calendar.get_date()
        if selected_date in self.stats.daily_stats:
            self.trigger_label.config(text=f"Triggers on {selected_date}: {self.stats.daily_stats[selected_date]}")
        else:
            self.trigger_label.config(text=f"No triggers recorded for {selected_date}")
    
    def _update_layout(self) -> None:
        window_width = self.root.winfo_width()
        tabs_width = max(int(window_width / 3), 200)
        self.tabs_frame.configure(width=tabs_width)
    
    def _on_resize(self, event=None) -> None:
        """Handle resize events with debouncing."""
        if event.widget == self.root:
            # Cancel any previously scheduled resize
            if self._resize_after_id is not None:
                self.root.after_cancel(self._resize_after_id)
            # Schedule new resize after 100ms delay
            self._resize_after_id = self.root.after(100, self._perform_resize, event)
    
    def _perform_resize(self, event=None) -> None:
        """Perform the actual resize operations."""
        if event.widget == self.root:
            width, height = self.root.winfo_width(), self.root.winfo_height()
            title_size = max(int(height / 60), 12)
            label_size = max(int(height / 80), 10)
            self.title_font.config(size=title_size)
            self.label_font.config(size=label_size)
            self.video_width = max(int(width * 0.6), 320)
            self.video_height = max(int(height * 0.8), 240)
            if not self.camera_initialized:
                self.placeholder_label.configure(width=self.video_width // 10)
            if self.photo:
                container_width = self.photo.width() + 20
                container_height = self.photo.height() + 30
            else:
                container_width = self.video_width + 20
                container_height = self.video_height + 30
            self.video_container.configure(width=container_width, height=container_height)
            self._update_layout()
            self._resize_after_id = None  # Clear the ID after execution
    
    def show_camera_error(self) -> None:
        self.placeholder_label.pack_forget()
        self.video_label.pack_forget()
        self.camera_error_label.pack(pady=5)
        self.retry_button.pack(pady=5)
        self.status_label.config(text="Camera initialization failed")
    
    def _retry_camera(self) -> None:
        self.camera_error_label.pack_forget()
        self.retry_button.pack_forget()
        self.placeholder_label.pack()
        self.status_label.config(text="Attempting to reconnect camera...")
        if hasattr(self, '_on_retry_camera'):
            self._on_retry_camera()
    
    def update_frame(self, frame: np.ndarray, fps: float, status: str) -> None:
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width = frame.shape[:2]
            ratio = min(self.video_width / width, self.video_height / height)
            new_size = (int(width * ratio), int(height * ratio))
            resized_frame = cv2.resize(frame, new_size)
            pil_img = Image.fromarray(resized_frame)
            photo = ImageTk.PhotoImage(image=pil_img)
            self.frame_queue.put((photo, fps, status))
            if self.stats_graph_manager:
                self.stats_graph_manager.update_graphs()
            if not self.camera_initialized and photo:
                self.camera_initialized = True
                self.placeholder_label.pack_forget()
                self.camera_error_label.pack_forget()
                self.retry_button.pack_forget()
                self.video_label.pack()
                self.video_container.configure(width=photo.width() + 20, height=photo.height() + 30)
        except Exception as e:
            logging.error(f"Error updating frame: {e}")
    
    def process_frame_queue(self) -> None:
        try:
            if not self.frame_queue.empty():
                photo, fps, status = self.frame_queue.get_nowait()
                self.photo = photo
                self.video_label.config(image=self.photo)
                self.status_label.config(text=status)
                self.fps_label.config(text=f"FPS: {fps:.1f}")
        except Exception as e:
            logging.error(f"Error processing frame queue: {e}")
        if self.running:
            self.root.after(15, self.process_frame_queue)
    
    def start(self) -> None:
        self.running = True
        self.process_frame_queue()
        self.root.mainloop()
    
    def close(self) -> None:
        self.running = False
        self.on_quit()
        try:
            self.root.destroy()
        except Exception:
            pass