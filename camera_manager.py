import cv2
import logging
from typing import Tuple, Optional
import numpy as np

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
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
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