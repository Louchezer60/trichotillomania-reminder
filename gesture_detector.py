import cv2
import numpy as np
import mediapipe as mp
from typing import Any, Tuple
import time
import logging
import random

class HandTracker:
    """Track hand visibility over time."""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.left_hand_visible = []
        self.right_hand_visible = []
        self.last_visible_time = {"left": 0, "right": 0}
        
    def update(self, left_visible: bool, right_visible: bool) -> None:
        """Update hand visibility history."""
        self.left_hand_visible.append(left_visible)
        self.right_hand_visible.append(right_visible)
        
        current_time = time.time()
        if left_visible:
            self.last_visible_time["left"] = current_time
        if right_visible:
            self.last_visible_time["right"] = current_time
            
        if len(self.left_hand_visible) > self.max_history:
            self.left_hand_visible.pop(0)
        if len(self.right_hand_visible) > self.max_history:
            self.right_hand_visible.pop(0)
    
    def hand_disappeared(self) -> bool:
        """Check if a hand was visible and then disappeared recently."""
        if len(self.left_hand_visible) < 3 or len(self.right_hand_visible) < 3:
            return False
            
        left_was_visible = any(self.left_hand_visible[:-2])
        right_was_visible = any(self.right_hand_visible[:-2])
        
        left_now_invisible = not self.left_hand_visible[-1]
        right_now_invisible = not self.right_hand_visible[-1]
        
        return (left_was_visible and left_now_invisible) or (right_was_visible and right_now_invisible)
    
    def time_since_visible(self) -> float:
        """Return time since any hand was last visible."""
        current_time = time.time()
        latest_visible = max(self.last_visible_time["left"], self.last_visible_time["right"])
        return current_time - latest_visible

class GestureDetector:
    RIGHT_EYE = 159
    LEFT_EYE = 386
    FOREHEAD = 10
    CROWN = 152
    TEMPLES = [447, 227]
    CHIN = 152
    LEFT_CHEEK = 234
    RIGHT_CHEEK = 454
    JAW_LEFT = 136
    JAW_RIGHT = 365
    NOSE_TIP = 4
    EYEBROW_LEFT = 282
    EYEBROW_RIGHT = 52
    
    def __init__(self, config):
        self.config = config
        self.mp_hands = mp.solutions.hands
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=config.detection['hand_confidence'],
            max_num_hands=2,
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
        self.hand_tracker = HandTracker()
    
    def process_frame(self, frame: np.ndarray) -> Tuple[Any, Any]:
        hand_results = self.hands.process(frame)
        face_results = self.face_mesh.process(frame)
        
        # Initialize visibility flags
        left_visible = False
        right_visible = False
        
        if hand_results.multi_hand_landmarks:
            current_hand_count = len(hand_results.multi_hand_landmarks)
            if hand_results.multi_handedness:
                for idx, handedness in enumerate(hand_results.multi_handedness):
                    if idx < len(hand_results.multi_hand_landmarks):
                        hand_type = handedness.classification[0].label.lower()
                        if hand_type == "left":
                            left_visible = True
                        elif hand_type == "right":
                            right_visible = True
        
        self.face_visible = face_results and face_results.multi_face_landmarks and len(face_results.multi_face_landmarks) > 0
        self.hand_tracker.update(left_visible, right_visible)
        
        return hand_results, face_results
    
    def draw_landmarks(self, frame: np.ndarray, hand_results: Any, face_results: Any, show_meshes: bool = True) -> np.ndarray:
        if show_meshes:
            if hand_results.multi_hand_landmarks:
                for hand_landmarks in hand_results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.drawing_spec_hands
                    )
            if face_results and face_results.multi_face_landmarks:
                face_landmarks = face_results.multi_face_landmarks[0]
                self.mp_drawing.draw_landmarks(
                    frame, face_landmarks, self.mp_face_mesh.FACEMESH_CONTOURS,
                    self.drawing_spec_face
                )
                h, w, _ = frame.shape
                if self.config.detection['full_head_detection']:
                    for idx in [self.CHIN, self.LEFT_CHEEK, self.RIGHT_CHEEK, 
                               self.JAW_LEFT, self.JAW_RIGHT, self.EYEBROW_LEFT, 
                               self.EYEBROW_RIGHT, self.NOSE_TIP]:
                        x = int(face_landmarks.landmark[idx].x * w)
                        y = int(face_landmarks.landmark[idx].y * h)
                        cv2.circle(frame, (x, y), 4, (0, 255, 255), -1)
                    
        return frame
    
    @staticmethod
    def get_hand_size(hand_landmarks: Any, frame_width: int, frame_height: int) -> float:
        landmarks_np = np.array([
            (lm.x * frame_width, lm.y * frame_height) 
            for lm in hand_landmarks.landmark
        ])
        x_coords = landmarks_np[:, 0]
        y_coords = landmarks_np[:, 1]
        return (np.max(x_coords) - np.min(x_coords)) * (np.max(y_coords) - np.min(y_coords))
    
    @staticmethod
    def get_head_size(face_landmarks: Any, frame_width: int, frame_height: int) -> float:
        landmarks_np = np.array([
            (lm.x * frame_width, lm.y * frame_height) 
            for lm in face_landmarks.landmark
        ])
        x_coords = landmarks_np[:, 0]
        y_coords = landmarks_np[:, 1]
        return (np.max(x_coords) - np.min(x_coords)) * (np.max(y_coords) - np.min(y_coords))
    
    def cleanup(self) -> None:
        try:
            if self.hands is not None:
                self.hands.close()
                self.hands = None
            if self.face_mesh is not None:
                self.face_mesh.close()
                self.face_mesh = None
        except Exception as e:
            logging.error(f"Error during gesture detector cleanup: {e}")