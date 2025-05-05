import cv2
import numpy as np

class ImageProcessor:
    @staticmethod
    def adjust_exposure(frame: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        processed_lab = cv2.merge((l, a, b))
        return cv2.cvtColor(processed_lab, cv2.COLOR_LAB2BGR)
    
    @staticmethod
    def is_overexposed(frame: np.ndarray, threshold: int = 220) -> bool:
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) > threshold