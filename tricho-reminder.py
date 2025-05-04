#!/usr/bin/env python3
"""
Hair-pulling detection system - Prevents trichotillomania behaviors

This application uses computer vision to detect when a person is pulling their hair
and plays audio feedback to help interrupt the behavior, with a unified Tkinter UI
that scales with window size and includes a tab to monitor daily triggers.
"""

import os
import random
import time
import threading
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass
import json
import numpy as np
import pygame
import cv2
import mediapipe as mp
from gtts import gTTS
import tkinter as tk
from tkinter import ttk, font
import sv_ttk  # Sun Valley ttk theme
from PIL import Image, ImageTk
import queue
import logging
from tkcalendar import Calendar
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Type definitions
Frame = np.ndarray
Landmark = Any  # mp.solutions landmarks


@dataclass
class Config:
    """Application configuration settings."""
    detection: Dict[str, Any]
    audio: Dict[str, Any]
    camera: Dict[str, Any]


@dataclass
class TempSettings:
    """Temporary settings used during configuration."""
    trigger_cooldown: int
    required_duration: float
    pull_threshold: int


class ResourceManager:
    """Manages access to application resources."""
    
    @staticmethod
    def get_resource_path(relative_path: str) -> str:
        """Get absolute path to resource, works for dev and for PyInstaller."""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def ensure_directories(dirs: List[str]) -> None:
        """Ensure all directories in the list exist."""
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)


class DetectionMode:
    """Detection sensitivity modes."""
    STRICT = "strict"
    NORMAL = "normal"
    RELAXED = "relaxed"
    
    @staticmethod
    def apply_mode(mode: str, config: Config) -> None:
        """Apply detection mode settings to config."""
        if mode == DetectionMode.STRICT:
            config.detection['required_duration'] = 1.0
            config.detection['pull_threshold'] = 1
        elif mode == DetectionMode.RELAXED:
            config.detection['required_duration'] = 2.0
            config.detection['pull_threshold'] = 2


class PullingStats:
    """Tracks statistics on hair-pulling incidents."""
    
    def __init__(self):
        self.triggers: List[float] = []
        self.daily_stats: Dict[str, int] = {}
        self.load_stats()
    
    def add_trigger(self) -> None:
        """Record a new hair-pulling trigger event."""
        now = time.time()
        self.triggers.append(now)
        self.update_daily_stats()
        self.save_stats()
    
    def update_daily_stats(self) -> None:
        """Update daily statistics based on triggers."""
        today = time.strftime("%Y-%m-%d")
        if today not in self.daily_stats:
            self.daily_stats[today] = 0
        self.daily_stats[today] += 1
    
    def get_daily_report(self) -> str:
        """Get a report of today's triggers."""
        today = time.strftime("%Y-%m-%d")
        return f"Today's triggers: {self.daily_stats.get(today, 0)}"
    
    def load_stats(self) -> None:
        """Load stats from storage."""
        try:
            with open('hair_stats.json', 'r') as f:
                data = json.load(f)
                self.daily_stats = data.get('daily_stats', {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def save_stats(self) -> None:
        """Save stats to storage."""
        data = {'daily_stats': self.daily_stats}
        with open('hair_stats.json', 'w') as f:
            json.dump(data, f)


class AudioManager:
    """Manages audio playback and TTS generation."""
    
    MOTIVATIONAL_PHRASES = [
        "You're stronger than this urge. You've got this!",
        "Your hands are capable of great things - let them stay free.",
        "Every moment you resist makes you stronger.",
        "You're in control. Take a deep breath and release the tension.",
        "Your hair grows beautiful when you let it be.",
        "This temporary urge will pass. Stay strong!",
        "You're worth more than a moment of compulsion.",
        "Picture yourself proud for resisting. You can do it!",
        "Take a deep breath. You can do this.",
        "Keep your hands busy. Maybe try a stress ball.",
        "Remember, you're in control. Let's stay strong.",
        "One moment at a time. You've got this.",
        "Notice the urge, but don't act on it.",
        "Your hair thanks you for your strength.",
        "Let's redirect your focus to something else.",
        "You're stronger than the urge. Stay calm.",
        "Gentle reminder: Keep those hands away.",
        "Every moment you resist makes you stronger.",
        "You're doing great! Keep up the good work.",
        "Let's practice some mindfulness together.",
        "Maybe try massaging your scalp gently instead.",
        "Remember how proud you'll feel for resisting.",
        "This moment will pass. Stay resilient."
    ]
    
    def __init__(self, audio_folder: str, stock_audio_folder: str, use_tts: bool = False):
        self.audio_folder = audio_folder
        self.stock_audio_folder = stock_audio_folder
        self.use_tts = use_tts
        self.control_event = threading.Event()
        pygame.mixer.init()
        self._audio_files_cache = None
    
    def get_audio_files(self) -> List[str]:
        if self._audio_files_cache is None:
            self._audio_files_cache = [
                f for f in os.listdir(self.stock_audio_folder)
                if f.endswith(('.mp3', '.wav'))
            ]
        return self._audio_files_cache
    
    def generate_tts(self, phrase: str, filename: str) -> Optional[str]:
        filepath = os.path.join(self.audio_folder, filename)
        if os.path.exists(filepath):
            return filepath
        def _generate_in_thread():
            try:
                tts = gTTS(text=phrase, lang='en')
                tts.save(filepath)
                self.play_audio(filepath)
            except Exception as e:
                print(f"Error generating TTS: {e}")
        tts_thread = threading.Thread(target=_generate_in_thread)
        tts_thread.daemon = True
        tts_thread.start()
        return None
    
    def play_audio(self, audio_file: str) -> None:
        def _play_in_thread():
            try:
                pygame.mixer.music.unload()
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and not self.control_event.is_set():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception as e:
                print(f"Audio playback error: {e}")
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init()
                except Exception:
                    pass
        audio_thread = threading.Thread(target=_play_in_thread)
        audio_thread.daemon = True
        audio_thread.start()
    
    def play_message(self) -> None:
        if self.use_tts:
            phrase = random.choice(self.MOTIVATIONAL_PHRASES)
            filename = f"hair_touch_{int(time.time())}.mp3"
            file_path = self.generate_tts(phrase, filename)
            if file_path:
                self.play_audio(file_path)
        else:
            stock_audio_files = self.get_audio_files()
            if stock_audio_files:
                audio_file = os.path.join(self.stock_audio_folder, random.choice(stock_audio_files))
                self.play_audio(audio_file)
            else:
                print("\nWarning: Stock audio folder is empty, falling back to TTS")
                self.use_tts = True
                self.play_message()
    
    def cleanup(self) -> None:
        self.control_event.set()
        pygame.mixer.quit()


class ConfigManager:
    DEFAULT_CONFIG = {
        "detection": {
            "hand_confidence": 0.7,
            "face_confidence": 0.5,
            "trigger_cooldown": 3,
            "required_duration": 0.75,
            "pull_threshold": 1,
            "max_head_distance": 150
        },
        "audio": {"volume": 1.0, "language": "en"},
        "camera": {"device": 0, "flip": True}
    }
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Config:
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                return Config(**config_data)
        except (FileNotFoundError, json.JSONDecodeError):
            return Config(**self.DEFAULT_CONFIG)
    
    def save_config(self) -> None:
        with open(self.config_file, 'w') as f:
            json.dump(self.config.__dict__, f, indent=4)
    
    def reset_to_default(self) -> None:
        self.config = Config(**self.DEFAULT_CONFIG)
        self.save_config()


class GestureDetector:
    RIGHT_EYE = 159
    LEFT_EYE = 386
    FOREHEAD = 10
    CROWN = 152
    TEMPLES = [447, 227]
    
    def __init__(self, config: Config):
        self.config = config
        self.mp_hands = mp.solutions.hands
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=config.detection['hand_confidence'],
            max_num_hands=1,
            model_complexity=0,
            static_image_mode=False
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            min_detection_confidence=config.detection['face_confidence'],
            max_num_faces=1,
            refine_landmarks=False,
            static_image_mode=False,
            min_tracking_confidence=0.5
        )
        self.drawing_spec_hands = self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
        self.drawing_spec_face = self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=1, circle_radius=1)
    
    def process_frame(self, frame: Frame) -> Tuple[Any, Any]:
        hand_results = self.hands.process(frame)
        face_results = self.face_mesh.process(frame)
        return hand_results, face_results
    
    def draw_landmarks(self, frame: Frame, hand_results: Any, face_results: Any) -> Frame:
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.drawing_spec_hands
                )
        if face_results and face_results.multi_face_landmarks:
            for face_landmarks in face_results.multi_face_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame, face_landmarks, self.mp_face_mesh.FACEMESH_CONTOURS,
                    self.drawing_spec_face
                )
        return frame
    
    @staticmethod
    def get_hand_size(hand_landmarks: Landmark, frame_width: int, frame_height: int) -> float:
        landmarks_np = np.array([
            (lm.x * frame_width, lm.y * frame_height) 
            for lm in hand_landmarks.landmark
        ])
        x_coords = landmarks_np[:, 0]
        y_coords = landmarks_np[:, 1]
        return (np.max(x_coords) - np.min(x_coords)) * (np.max(y_coords) - np.min(y_coords))
    
    @staticmethod
    def get_head_size(face_landmarks: Landmark, frame_width: int, frame_height: int) -> float:
        landmarks_np = np.array([
            (lm.x * frame_width, lm.y * frame_height) 
            for lm in face_landmarks.landmark
        ])
        x_coords = landmarks_np[:, 0]
        y_coords = landmarks_np[:, 1]
        return (np.max(x_coords) - np.min(x_coords)) * (np.max(y_coords) - np.min(y_coords))
    
    def cleanup(self) -> None:
        self.hands.close()
        self.face_mesh.close()


class ImageProcessor:
    @staticmethod
    def adjust_exposure(frame: Frame) -> Frame:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        processed_lab = cv2.merge((l, a, b))
        return cv2.cvtColor(processed_lab, cv2.COLOR_LAB2BGR)
    
    @staticmethod
    def is_overexposed(frame: Frame, threshold: int = 220) -> bool:
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) > threshold


class CameraManager:
    def __init__(self, device_id: int = 0, flip_horizontal: bool = True):
        self.device_id = device_id
        self.flip_horizontal = flip_horizontal
        self.cap = None
    
    def open(self) -> bool:
        logging.debug(f"Attempting to open camera at index {self.device_id}")
        self.cap = cv2.VideoCapture(self.device_id)
        camera_index = self.device_id
        while not self.cap.isOpened() and camera_index < 10:
            logging.debug(f"Trying camera index {camera_index}...")
            camera_index += 1
            self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            logging.error("Error: Could not open camera")
            print("Error: Could not open camera")
            return False
        logging.info(f"Camera found at index {camera_index}")
        print(f"Camera found at index {camera_index}")
        self._configure_camera()
        return True
    
    def _configure_camera(self) -> None:
        logging.debug("Configuring camera settings")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 15)
        try:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            self.cap.set(cv2.CAP_PROP_EXPOSURE, -4)
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)
            logging.debug("Camera exposure settings applied")
        except Exception as e:
            logging.warning(f"Could not set camera exposure settings: {e}")
            print("Warning: Could not set camera exposure settings")
    
    def read_frame(self) -> Tuple[bool, Optional[Frame]]:
        if not self.cap or not self.cap.isOpened():
            logging.error("Camera not initialized or not opened")
            return False, None
        try:
            success, frame = self.cap.read()
            if not success:
                logging.error("Failed to read frame from camera")
                return False, None
            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)
            return True, frame
        except Exception as e:
            logging.error(f"Error reading frame: {e}")
            return False, None
    
    def adjust_exposure(self, is_overexposed: bool) -> None:
        if is_overexposed:
            try:
                current_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                self.cap.set(cv2.CAP_PROP_EXPOSURE, current_exposure * 0.9)
                logging.debug("Exposure adjusted due to overexposure")
            except Exception as e:
                logging.warning(f"Failed to adjust exposure: {e}")
    
    def close(self) -> None:
        if self.cap:
            try:
                self.cap.release()
                logging.debug("Camera released")
            except Exception as e:
                logging.error(f"Error releasing camera: {e}")
            self.cap = None


class UIManager:
    """Manages the application's unified Tkinter UI with scalable elements."""
    
    def __init__(self, config: Config, stats: PullingStats, on_quit: Callable, on_reset: Callable):
        """Initialize UI manager with Tkinter window."""
        self.config = config
        self.stats = stats
        self.on_quit = on_quit
        self.on_reset = on_reset
        self.root = None
        self.video_frame = None
        self.video_label = None
        self.photo = None
        self.temp_settings = TempSettings(
            trigger_cooldown=config.detection['trigger_cooldown'],
            required_duration=config.detection['required_duration'],
            pull_threshold=config.detection['pull_threshold']
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
    
    def initialize_ui(self) -> None:
        """Initialize Tkinter window with video feed, settings, and triggers tabs."""
        self.root = tk.Tk()
        self.root.title("Trichotillomania-Reminder : Hair-Pulling Detection System")
        self.root.geometry("1280x720")
        self.root.resizable(True, True)
        
        # Set custom window icon
        try:
            icon_path = ResourceManager.get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                logging.warning(f"Icon file not found at: {icon_path}")
        except Exception as e:
            logging.error(f"Error setting window icon: {e}")
        
        sv_ttk.set_theme("light")
        
        # Main frame with two sections
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Video feed section
        self.video_frame = ttk.Frame(main_frame)
        self.video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Tabs for settings and triggers
        tabs_frame = ttk.Frame(main_frame, padding="10")
        tabs_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        notebook = ttk.Notebook(tabs_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Settings tab
        settings_frame = ttk.Frame(notebook, padding="10")
        notebook.add(settings_frame, text="Settings")
        
        # Triggers tab
        triggers_frame = ttk.Frame(notebook, padding="10")
        notebook.add(triggers_frame, text="Triggers")
        
        # Dynamic fonts (will be updated in resize handler)
        self.title_font = font.Font(family="Segoe UI", size=14, weight="bold")
        self.label_font = font.Font(family="Segoe UI", size=10)
        
        # --- Settings Tab ---
        # Settings title
        self.title_label = ttk.Label(settings_frame, text="Settings", font=self.title_font)
        self.title_label.pack(pady=10)
        
        # StringVars for dynamic value display
        cooldown_var = tk.StringVar(value=str(self.temp_settings.trigger_cooldown))
        duration_var = tk.StringVar(value=f"{self.temp_settings.required_duration:.1f}")
        threshold_var = tk.StringVar(value=str(self.temp_settings.pull_threshold))
        
        # Trigger Cooldown
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
        
        # Required Duration
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
        
        # Pull Threshold
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
        
        # Buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Apply", command=self.apply_settings_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset", command=self.on_reset).pack(side=tk.LEFT, padx=5)
        
        # Status labels
        self.status_label = ttk.Label(settings_frame, text="Controls: Q to quit, R to reset", font=self.label_font)
        self.status_label.pack(anchor=tk.W, pady=5)
        self.fps_label = ttk.Label(settings_frame, text="FPS: 0", font=self.label_font)
        self.fps_label.pack(anchor=tk.W)
        self.depth_label = ttk.Label(settings_frame, text="Depth ratio: 0.00", font=self.label_font)
        self.depth_label.pack(anchor=tk.W)
        
        # --- Triggers Tab ---
        # Triggers title
        triggers_title = ttk.Label(triggers_frame, text="Daily Triggers", font=self.title_font)
        triggers_title.pack(pady=10)
        
        # Calendar widget
        self.calendar = Calendar(triggers_frame, selectmode="day", font=self.label_font,
                                date_pattern="yyyy-mm-dd")
        self.calendar.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Label to display trigger count for selected date
        self.trigger_label = ttk.Label(triggers_frame, text="Select a date to view triggers", font=self.label_font)
        self.trigger_label.pack(pady=5)
        
        # Bind calendar selection to update trigger count
        self.calendar.bind("<<CalendarSelected>>", self.update_trigger_count)
        
        # Highlight days with triggers
        self.update_calendar_highlights()
        
        # Keyboard bindings
        self.root.bind('q', lambda e: self.on_quit())
        self.root.bind('r', lambda e: self.on_reset())
        
        # Resize event binding
        self.root.bind('<Configure>', self.handle_resize)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.running = True
        
        self.root.after(100, self.check_queue)
    
    def update_trigger_count(self, event=None) -> None:
        """Update the trigger count label based on selected calendar date."""
        selected_date = self.calendar.get_date()
        count = self.stats.daily_stats.get(selected_date, 0)
        self.trigger_label.configure(text=f"Triggers on {selected_date}: {count}")
    
    def update_calendar_highlights(self) -> None:
        """Highlight days in the calendar that have triggers."""
        for date, count in self.stats.daily_stats.items():
            if count > 0:
                try:
                    # Highlight days with triggers using a red background
                    self.calendar.calevent_create(datetime.strptime(date, "%Y-%m-%d"), f"{count} triggers", "trigger")
                    self.calendar.tag_config("trigger", background="red", foreground="white")
                except ValueError:
                    logging.warning(f"Invalid date format in daily_stats: {date}")
    
    def handle_resize(self, event: tk.Event) -> None:
        """Handle window resize to scale UI elements."""
        if not self.running or self.root is None:
            return
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Calculate video frame size (maintain 4:3 aspect ratio)
        video_frame_width = window_width * 0.7  # 70% of window width for video
        video_frame_height = window_height - 20  # Account for padding
        aspect_ratio = 4 / 3
        if video_frame_width / video_frame_height > aspect_ratio:
            self.video_width = int(video_frame_height * aspect_ratio)
            self.video_height = int(video_frame_height)
        else:
            self.video_width = int(video_frame_width)
            self.video_height = int(video_frame_width / aspect_ratio)
        
        # Update font sizes
        title_font_size = max(12, window_height // 40)
        label_font_size = max(8, window_height // 50)
        self.title_font.configure(size=title_font_size)
        self.label_font.configure(size=label_font_size)
        
        # Update video frame size
        self.video_frame.configure(width=self.video_width, height=self.video_height)
    
    def update_frame(self, frame: Frame, fps: float, size_ratio: float, is_at_same_depth: bool) -> None:
        """Update video feed and UI elements with new frame."""
        if not self.running or self.root is None:
            return
        try:
            # Convert OpenCV frame (BGR) to PIL Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            # Resize to fit video frame
            pil_image = pil_image.resize((self.video_width, self.video_height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(pil_image)
            self.video_label.configure(image=self.photo)
            self.video_label.image = self.photo  # Keep reference to prevent GC
            
            # Update status labels
            self.fps_label.configure(text=f"FPS: {int(fps)}")
            self.depth_label.configure(text=f"Depth ratio: {size_ratio:.2f}", 
                                    foreground="green" if is_at_same_depth else "red")
        except tk.TclError as e:
            logging.error(f"Tkinter error in update_frame: {e}")
            self.running = False
        except Exception as e:
            logging.error(f"Error in update_frame: {e}")
    
    def check_queue(self) -> None:
        """Check frame queue for new frames."""
        if not self.running:
            return
        try:
            if not self.frame_queue.empty():
                frame, fps, size_ratio, is_at_same_depth = self.frame_queue.get_nowait()
                self.update_frame(frame, fps, size_ratio, is_at_same_depth)
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Error in check_queue: {e}")
        if self.running:
            self.root.after(50, self.check_queue)  # ~20 FPS
    
    def add_config_interface(self, frame: Frame, config: Config) -> Frame:
        """Add configuration overlays to the video frame."""
        h, w, _ = frame.shape
        font_scale = max(0.5, w / 640)  # Scale font with frame width
        cv2.putText(frame, f"Detection time: {config.detection['required_duration']:.1f}s", 
                    (20, 60), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), 2)
        return frame
    
    def draw_detection_progress(self, frame: Frame, start_time: float, required_duration: float) -> Frame:
        if start_time is None:
            return frame
        h, w, _ = frame.shape
        current_time = time.time()
        duration = max(required_duration, 0.001)
        elapsed = current_time - start_time
        progress = int((elapsed / duration) * w)
        progress = min(max(progress, 0), w)
        cv2.line(frame, (0, 30), (progress, 30), (0, 255, 0), 5)
        return frame
    
    def draw_eye_level(self, frame: Frame, eye_level: int) -> Frame:
        h, w, _ = frame.shape
        cv2.line(frame, (0, int(eye_level)), (w, int(eye_level)), (0, 255, 255), 2)
        return frame
    
    def draw_overexposure_warning(self, frame: Frame) -> Frame:
        h, w, _ = frame.shape
        font_scale = max(0.5, w / 640)
        cv2.putText(frame, "Overexposure detected!", (20, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), 2)
        return frame
    
    def apply_settings_changes(self) -> None:
        """Apply settings changes and update config."""
        self.config.detection['trigger_cooldown'] = self.temp_settings.trigger_cooldown
        self.config.detection['required_duration'] = self.temp_settings.required_duration
        self.config.detection['pull_threshold'] = self.temp_settings.pull_threshold
        print(f"Settings updated: Cooldown={self.config.detection['trigger_cooldown']}s, " 
              f"Duration={self.config.detection['required_duration']:.1f}s, "
              f"Threshold={self.config.detection['pull_threshold']}")
    
    def cleanup(self) -> None:
        """Close Tkinter window."""
        self.running = False
        if self.root is None:
            return
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self.root = None
        logging.info("UI cleaned up")


class TrichotillomaniaDetector:
    def __init__(self):
        self.audio_folder = "audio"
        self.stock_audio_folder = "stock_audio"
        ResourceManager.ensure_directories([self.audio_folder, self.stock_audio_folder])
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        self.camera = CameraManager(
            device_id=self.config.camera['device'],
            flip_horizontal=self.config.camera['flip']
        )
        self.detector = GestureDetector(self.config)
        self.audio_manager = AudioManager(
            self.audio_folder, self.stock_audio_folder, use_tts=True
        )
        self.image_processor = ImageProcessor()
        self.stats = PullingStats()
        
        self.ui = UIManager(
            self.config,
            self.stats,
            on_quit=self.quit,
            on_reset=self.reset_config
        )
        
        self.running = False
        self.last_trigger_time = 0
        self.detection_start_time = None
        self.prev_frame_time = 0
        self.new_frame_time = 0
        self.camera_thread = None
    
    def run(self) -> None:
        if not self.camera.open():
            print("Failed to open camera. Exiting.")
            logging.error("Camera failed to open")
            self.quit()
            return
        
        self.ui.initialize_ui()
        self.running = True
        
        print("\nHair-pulling detection system is running...")
        print("Press 'Q' to quit, 'R' to reset detection parameters\n")
        logging.info("Application started")
        
        # Start camera thread
        self.camera_thread = threading.Thread(target=self.camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        logging.info("Camera thread started")
        
        # Start Tkinter main loop
        try:
            self.ui.root.mainloop()
        except KeyboardInterrupt:
            self.quit()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            self.quit()
    
    def camera_loop(self) -> None:
        """Run camera capture and processing in a separate thread."""
        while self.running:
            self.process_one_frame()
            time.sleep(0.01)  # Prevent tight loop
    
    def process_one_frame(self) -> None:
        try:
            self.new_frame_time = time.time()
            fps = 1 / (self.new_frame_time - self.prev_frame_time) if self.prev_frame_time > 0 else 30
            self.prev_frame_time = self.new_frame_time
            
            success, frame = self.camera.read_frame()
            if not success:
                logging.error("Failed to read frame, stopping")
                print("Failed to read frame.")
                self.quit()
                return
            
            is_overexposed = self.image_processor.is_overexposed(frame)
            if is_overexposed:
                self.camera.adjust_exposure(is_overexposed)
                frame = self.ui.draw_overexposure_warning(frame)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hand_results, face_results = self.detector.process_frame(rgb_frame)
            
            frame = self.detector.draw_landmarks(frame, hand_results, face_results)
            frame = self.ui.add_config_interface(frame, self.config)
            
            size_ratio = 0.0
            is_at_same_depth = False
            
            if hand_results.multi_hand_landmarks and face_results and face_results.multi_face_landmarks:
                hand_landmarks = hand_results.multi_hand_landmarks[0]
                face_landmarks = face_results.multi_face_landmarks[0]
                
                h, w, _ = frame.shape
                
                left_eye_y = face_landmarks.landmark[self.detector.LEFT_EYE].y * h
                right_eye_y = face_landmarks.landmark[self.detector.RIGHT_EYE].y * h
                eye_level = (left_eye_y + right_eye_y) / 2
                
                frame = self.ui.draw_eye_level(frame, eye_level)
                
                hand_size = self.detector.get_hand_size(hand_landmarks, w, h)
                head_size = self.detector.get_head_size(face_landmarks, w, h)
                size_ratio = hand_size / head_size if head_size > 0 else 0
                
                is_at_same_depth = 0.1 < size_ratio < 3.0
                
                hand_y = hand_landmarks.landmark[9].y * h
                
                is_above_eyes = hand_y < eye_level
                is_near_head = abs(hand_y - eye_level) < self.config.detection['max_head_distance']
                
                is_pulling = is_at_same_depth and is_near_head and is_above_eyes
                
                if is_pulling:
                    if self.detection_start_time is None:
                        self.detection_start_time = time.time()
                    
                    elapsed_time = time.time() - self.detection_start_time
                    frame = self.ui.draw_detection_progress(frame, self.detection_start_time, 
                                                        self.config.detection['required_duration'])
                    
                    if elapsed_time >= self.config.detection['required_duration']:
                        current_time = time.time()
                        cooldown_time = self.config.detection['trigger_cooldown']
                        
                        if current_time - self.last_trigger_time > cooldown_time:
                            print(f"Pulling gesture detected at {time.strftime('%H:%M:%S')}")
                            self.audio_manager.play_message()
                            self.last_trigger_time = current_time
                            self.stats.add_trigger()
                            print(self.stats.get_daily_report())
                            # Update calendar highlights
                            self.ui.update_calendar_highlights()
                            self.ui.update_trigger_count()
                        self.detection_start_time = None
                else:
                    self.detection_start_time = None
            else:
                self.detection_start_time = None
            
            # Add frame to queue for UI update
            if self.ui.running:
                try:
                    if self.ui.frame_queue.full():
                        self.ui.frame_queue.get_nowait()
                    self.ui.frame_queue.put((frame, fps, size_ratio, is_at_same_depth))
                except queue.Full:
                    pass
                except Exception as e:
                    logging.error(f"Error adding frame to queue: {e}")
        except Exception as e:
            logging.error(f"Error in process_one_frame: {e}")
            self.quit()
    
    def quit(self) -> None:
        """Quit the application."""
        self.running = False
        self.cleanup()
        logging.info("Application quit")
    
    def reset_config(self) -> None:
        """Reset configuration to default."""
        self.config_manager.reset_to_default()
        self.config = self.config_manager.config
        self.ui.temp_settings = TempSettings(
            trigger_cooldown=self.config.detection['trigger_cooldown'],
            required_duration=self.config.detection['required_duration'],
            pull_threshold=self.config.detection['pull_threshold']
        )
        print("Settings reset to default values")
        logging.info("Configuration reset to default")
    
    def cleanup(self) -> None:
        print("\nShutting down... please wait")
        self.running = False
        self.camera.close()
        self.detector.cleanup()
        self.audio_manager.cleanup()
        self.ui.cleanup()
        print("Application terminated")
        logging.info("Application cleanup completed")


def main() -> None:
    try:
        detector = TrichotillomaniaDetector()
        detector.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        logging.info("Application interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        print("Application terminated due to error")
        logging.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
