import time
import threading
import logging
import os
import numpy as np
from typing import Any, Callable
from config_manager import Config
from stats_manager import PullingStats
from camera_manager import CameraManager
from gesture_detector import GestureDetector
from audio_manager import AudioManager
from ui_manager import UIManager
from resource_manager import ResourceManager
from config_manager import ConfigManager
import cv2

class HairPullingDetector:
    """Main detector class handling hair-pulling detection logic."""
    
    STATES = {
        'IDLE': 'Monitoring',
        'DETECTING': 'Detecting possible hair-pulling',
        'PULLING': 'Hair-pulling detected!'
    }
    
    def __init__(self, config: Config):
        self.audio_folder = 'audio'
        self.stock_audio_folder = 'stock_audio'
        ResourceManager.ensure_directories([self.audio_folder, self.stock_audio_folder])
        
        self.config = config
        self.stats = PullingStats()
        
        self.state = 'IDLE'
        self.hand_near_head_time = 0
        self.hand_near_head_duration = 0
        self.last_triggered = 0
        self.last_hand_near_head = 0
        
        self.camera_manager = CameraManager(
            device_id=self.config.camera['device'],
            flip_horizontal=self.config.camera['flip']
        )
        self.gesture_detector = GestureDetector(self.config)
        self.audio_manager = AudioManager(
            audio_folder=self.audio_folder,
            stock_audio_folder=self.stock_audio_folder,
            use_tts=bool(len(os.listdir(self.stock_audio_folder)) == 0),
            config=self.config
        )
        self.ui_manager = UIManager(
            config=self.config,
            stats=self.stats,
            on_quit=self.cleanup,
            on_reset=self.reset_config,
            audio_manager=self.audio_manager,
            camera_manager=self.camera_manager
        )
        self.ui_manager._on_retry_camera = self._retry_camera
        
        self.fps_history = []
        self.frame_count = 0
        self.last_fps_update = time.time()
        self.running = False
        self.detection_thread = None
        
        self.contact_points = []
        self.above_eye_points = []
    
    def reset_config(self) -> None:
        config_manager = ConfigManager()
        config_manager.reset_to_default()
        self.config = config_manager.load_config()  # Reload default config
        
        # Update UIManager's temp_settings and UI elements
        self.ui_manager.temp_settings.trigger_cooldown = self.config.detection['trigger_cooldown']
        self.ui_manager.temp_settings.required_duration = self.config.detection['required_duration']
        self.ui_manager.temp_settings.pull_threshold = self.config.detection['pull_threshold']
        self.ui_manager.temp_settings.full_head_detection = self.config.detection['full_head_detection']
        self.ui_manager.temp_settings.show_meshes = self.config.detection['show_meshes']
        self.ui_manager.temp_settings.tts_cache_limit = self.config.audio['tts_cache_limit']
        self.ui_manager.temp_settings.max_head_distance = self.config.detection['max_head_distance']
        
        # Update UI elements
        if self.ui_manager.cooldown_scale:
            self.ui_manager.cooldown_scale.set(self.config.detection['trigger_cooldown'])
            self.ui_manager.cooldown_var.set(str(self.config.detection['trigger_cooldown']))
        if self.ui_manager.duration_scale:
            self.ui_manager.duration_scale.set(self.config.detection['required_duration'])
            self.ui_manager.duration_var.set(f"{self.config.detection['required_duration']:.1f}")
        if self.ui_manager.threshold_scale:
            self.ui_manager.threshold_scale.set(self.config.detection['pull_threshold'])
            self.ui_manager.threshold_var.set(str(self.config.detection['pull_threshold']))
        if self.ui_manager.cache_limit_scale:
            self.ui_manager.cache_limit_scale.set(self.config.audio['tts_cache_limit'])
            self.ui_manager.cache_limit_var.set(f"{self.config.audio['tts_cache_limit']:.1f}")
        if self.ui_manager.max_head_distance_scale:
            self.ui_manager.max_head_distance_scale.set(self.config.detection['max_head_distance'])
            self.ui_manager.max_head_distance_var.set(str(self.config.detection['max_head_distance']))
        
        if self.ui_manager.full_head_var:
            self.ui_manager.full_head_var.set(self.config.detection['full_head_detection'])
        if self.ui_manager.show_meshes_var:
            self.ui_manager.show_meshes_var.set(self.config.detection['show_meshes'])
        
        self.ui_manager._update_detection_mode_label()
        
        # Enforce cache limit
        if self.audio_manager:
            self.audio_manager._enforce_cache_limit()
        
        logging.info("Configuration reset to default")
    
    def _calculate_fps(self) -> float:
        current_time = time.time()
        time_diff = current_time - self.last_fps_update
        if time_diff > 1.0:
            fps = self.frame_count / time_diff
            self.fps_history.append(fps)
            if len(self.fps_history) > 10:
                self.fps_history.pop(0)
            self.frame_count = 0
            self.last_fps_update = current_time
            return sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        self.frame_count += 1
        return sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
    
    def _hand_near_head(self, hand_results: Any, face_results: Any) -> bool:
        if not hand_results.multi_hand_landmarks or not face_results or not face_results.multi_face_landmarks:
            return False
        
        face_landmarks = face_results.multi_face_landmarks[0]
        h, w, _ = self.current_frame.shape
        
        # Calculate eye level
        right_eye_y = face_landmarks.landmark[self.gesture_detector.RIGHT_EYE].y
        left_eye_y = face_landmarks.landmark[self.gesture_detector.LEFT_EYE].y
        eye_level_normalized = min(right_eye_y, left_eye_y) - 0.05
        eye_level_pixels = int(eye_level_normalized * h)
        
        self.contact_points = []
        self.above_eye_points = []
        
        # Collect face landmarks above eye level for above-eye detection
        face_points_above_eye_3d = []
        for i, lm in enumerate(face_landmarks.landmark):
            if i % 2 == 0 and lm.y * h <= eye_level_pixels:  # Every 2nd landmark above eye level
                x = lm.x * w
                y = lm.y * h
                z = lm.z * w
                face_points_above_eye_3d.append((x, y, z, i))
        
        for hand_landmarks in hand_results.multi_hand_landmarks:
            # Collect hand landmarks above eye level
            above_eye_landmarks = []
            for lm in hand_landmarks.landmark:
                hand_x = lm.x * w
                hand_y = lm.y * h
                hand_z = lm.z * w
                if hand_y <= eye_level_pixels:
                    above_eye_landmarks.append((hand_x, hand_y, hand_z))
            
            if self.config.detection['full_head_detection']:
                # Full head detection: Check for contact with any face landmark
                face_points_3d = []
                for i, lm in enumerate(face_landmarks.landmark):
                    if i % 2 == 0:  # Use every 2nd landmark for denser coverage
                        x = lm.x * w
                        y = lm.y * h
                        z = lm.z * w
                        face_points_3d.append((x, y, z, i))
                
                for hand_lm in hand_landmarks.landmark:
                    hand_x = hand_lm.x * w
                    hand_y = hand_lm.y * h
                    hand_z = hand_lm.z * w
                    hand_point_3d = np.array([hand_x, hand_y, hand_z])
                    
                    for face_x, face_y, face_z, face_idx in face_points_3d:
                        face_point_3d = np.array([face_x, face_y, face_z])
                        distance_3d = np.linalg.norm(hand_point_3d - face_point_3d)
                        if distance_3d < 20.0:
                            self.contact_points.append((int(hand_x), int(hand_y)))
                            logging.debug(f"Contact detected: hand at ({hand_x:.1f}, {hand_y:.1f}, {hand_z:.3f}), "
                                        f"face landmark {face_idx}, 3D_distance={distance_3d:.2f}, "
                                        f"contact_threshold=20.0")
                            return True
                
                # Check for above-eye detection
                if len(above_eye_landmarks) >= 3:
                    for hand_x, hand_y, hand_z in above_eye_landmarks:
                        hand_point_3d = np.array([hand_x, hand_y, hand_z])
                        for face_x, face_y, face_z, face_idx in face_points_above_eye_3d:
                            face_point_3d = np.array([face_x, face_y, face_z])
                            distance_3d = np.linalg.norm(hand_point_3d - face_point_3d)
                            if distance_3d < self.config.detection['max_head_distance']:
                                self.above_eye_points.append((int(hand_x), int(hand_y)))
                                logging.debug(f"Above-eye trigger: {len(above_eye_landmarks)} hand landmarks above eye_level={eye_level_pixels}, "
                                            f"hand at ({hand_x:.1f}, {hand_y:.1f}, {hand_z:.3f}), "
                                            f"face landmark {face_idx}, 3D_distance={distance_3d:.2f}, "
                                            f"proximity_threshold={self.config.detection['max_head_distance']}")
                                return True
            else:
                # Non-full head detection: Check only above-eye detection
                if len(above_eye_landmarks) >= 3:
                    for hand_x, hand_y, hand_z in above_eye_landmarks:
                        hand_point_3d = np.array([hand_x, hand_y, hand_z])
                        for face_x, face_y, face_z, face_idx in face_points_above_eye_3d:
                            face_point_3d = np.array([face_x, face_y, face_z])
                            distance_3d = np.linalg.norm(hand_point_3d - face_point_3d)
                            if distance_3d < self.config.detection['max_head_distance']:
                                self.above_eye_points.append((int(hand_x), int(hand_y)))
                                logging.debug(f"Above-eye trigger: {len(above_eye_landmarks)} hand landmarks above eye_level={eye_level_pixels}, "
                                            f"hand at ({hand_x:.1f}, {hand_y:.1f}, {hand_z:.3f}), "
                                            f"face landmark {face_idx}, 3D_distance={distance_3d:.2f}, "
                                            f"proximity_threshold={self.config.detection['max_head_distance']}")
                                return True
        
        return False
    
    def _check_for_pulling(self, hand_results: Any, face_results: Any) -> None:
        hand_near = self._hand_near_head(hand_results, face_results)
        hand_detected = hand_near
        current_time = time.time()
        if hand_detected:
            if self.state == 'IDLE':
                self.state = 'DETECTING'
                self.hand_near_head_time = current_time
            self.hand_near_head_duration = current_time - self.hand_near_head_time
            self.last_hand_near_head = current_time
            if (self.hand_near_head_duration >= self.config.detection['required_duration'] and 
                self.state == 'DETECTING'):
                self.state = 'PULLING'
        else:
            if current_time - self.last_hand_near_head > 0.1:
                self.state = 'IDLE'
                self.hand_near_head_duration = 0
    
    def _trigger_alert(self) -> None:
        if self.state == 'PULLING':
            current_time = time.time()
            cooldown_passed = (current_time - self.last_triggered) > self.config.detection['trigger_cooldown']
            if cooldown_passed and self.hand_near_head_duration >= self.config.detection['required_duration']:
                self.last_triggered = current_time
                self.audio_manager.play_message()
                self.stats.add_trigger()
                self.state = 'IDLE'
    
    def _retry_camera(self) -> None:
        logging.info("Retrying camera initialization")
        self.camera_manager.close()
        if self.camera_manager.open():
            self.ui_manager.status_label.config(text="Camera reconnected successfully")
        else:
            self.ui_manager.show_camera_error()
    
    def _detection_loop(self) -> None:
        try:
            if not self.camera_manager.open():
                logging.error("Failed to open camera")
                self.ui_manager.show_camera_error()
                return
            while self.running:
                if not self.running:
                    break

                success, frame = self.camera_manager.read_frame()
                if not success:
                    logging.warning("Failed to read frame, retrying...")
                    self.ui_manager.show_camera_error()
                    time.sleep(0.01)
                    continue

                self.current_frame = frame.copy()
                fps = self._calculate_fps()
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                if self.running:
                    hand_results, face_results = self.gesture_detector.process_frame(rgb_frame)
                    self._check_for_pulling(hand_results, face_results)
                    self._trigger_alert()
                    show_meshes = self.ui_manager.show_meshes_var.get()
                    frame_with_landmarks = self.gesture_detector.draw_landmarks(frame, hand_results, face_results, show_meshes)
                    status = self.STATES.get(self.state, 'Monitoring')
                    if self.state == 'DETECTING':
                        status = f"{status} ({self.hand_near_head_duration:.1f}s)"
                    self.ui_manager.update_frame(frame_with_landmarks, fps, status)
                
                time.sleep(0.01)
        except Exception as e:
            logging.error(f"Error in detection loop: {e}")
            self.ui_manager.show_camera_error()
        finally:
            self.camera_manager.close()
            logging.info("Detection loop terminated")
    
    def start(self) -> None:
        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.start()
        self.ui_manager.initialize_ui()
        self.ui_manager.start()
    
    def cleanup(self) -> None:
        logging.info("Shutting down application")
        self.running = False
        
        self.camera_manager.close()
        
        if self.detection_thread and self.detection_thread.is_alive():
            logging.debug("Waiting for detection thread to terminate...")
            self.detection_thread.join(timeout=1.0)
            if self.detection_thread.is_alive():
                logging.warning("Detection thread did not terminate within timeout")
            else:
                logging.info("Detection thread terminated successfully")
        
        self.gesture_detector.cleanup()
        self.audio_manager.cleanup()
        
        config_manager = ConfigManager()
        config_manager.config = self.config
        config_manager.save_config()