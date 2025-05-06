import cv2
import logging
from typing import Tuple, Optional
import numpy as np

class CameraManager:
    def __init__(self, device_id: int = 0, flip_horizontal: bool = True):
        self.device_id = device_id
        self.flip_horizontal = flip_horizontal
        self.cap = None
        self.brightness = 0.0  # Range: -100 to 100
        self.contrast = 1.0    # Range: 0.1 to 3.0
        self.gamma = 1.0       # Range: 0.1 to 5.0

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
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, -2)
            self.cap.set(cv2.CAP_PROP_EXPOSURE, -4)
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)
            self.apply_brightness_contrast_gamma()
            logging.debug("Camera settings applied")
        except Exception as e:
            logging.warning(f"Could not set camera settings: {e}")
            print("Warning: Could not set camera settings")

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
            # Apply brightness, contrast, and gamma adjustments
            frame = self.apply_brightness_contrast_gamma(frame)
            return True, frame
        except Exception as e:
            logging.error(f"Error reading frame: {e}")
            return False, None

    def set_exposure(self, value: float) -> None:
        """Set camera exposure."""
        try:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, value)
            logging.debug(f"Exposure set to {value}")
        except Exception as e:
            logging.warning(f"Failed to set exposure: {e}")

    def set_brightness(self, value: float) -> None:
        """Set brightness value for post-processing."""
        self.brightness = value
        logging.debug(f"Brightness set to {value}")

    def set_contrast(self, value: float) -> None:
        """Set contrast value for post-processing."""
        self.contrast = value
        logging.debug(f"Contrast set to {value}")

    def set_gamma(self, value: float) -> None:
        """Set gamma value for post-processing."""
        self.gamma = value
        logging.debug(f"Gamma set to {value}")

    def apply_brightness_contrast_gamma(self, frame: Optional[np.ndarray] = None) -> np.ndarray:
        """Apply brightness, contrast, and gamma adjustments to the frame."""
        if frame is None:
            return None
        # Apply brightness and contrast
        frame = cv2.convertScaleAbs(frame, alpha=self.contrast, beta=self.brightness)
        # Apply gamma correction
        if self.gamma != 1.0:
            inv_gamma = 1.0 / self.gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            frame = cv2.LUT(frame, table)
        return frame

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