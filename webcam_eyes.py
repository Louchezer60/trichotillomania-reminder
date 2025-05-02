import os
import random
import time
import threading
import pygame
import cv2
import mediapipe as mp
import argparse
import json
import numpy as np
from gtts import gTTS
import sys
from collections import deque
    
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Configuration
AUDIO_FOLDER = os.path.join(resource_path('static'), 'generated_audio')
STOCK_AUDIO_FOLDER = os.path.join(resource_path('static'), 'stock_audio')
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(STOCK_AUDIO_FOLDER, exist_ok=True)

_AUDIO_CACHE = None

def get_audio_files():
    global _AUDIO_CACHE
    if _AUDIO_CACHE is None:
        _AUDIO_CACHE = [f for f in os.listdir(STOCK_AUDIO_FOLDER)
                       if f.endswith(('.mp3', '.wav'))]
    return _AUDIO_CACHE

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

# Global state
playback_active = False
current_interval = 300
control_event = threading.Event()
remaining_time = current_interval
pygame.mixer.init()

# Détection de gestes
mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
hair_trigger_cooldown = 3
last_hair_trigger = 0
hair_lock = threading.Lock()

# Audio mode configuration
USE_TTS = None  # Will be set during runtime

CONFIG = {
    "detection": {
        "hand_confidence": 0.7,
        "face_confidence": 0.5,
        "trigger_cooldown": 3,
        "required_duration": 0.75,
        "pull_threshold": 1,
        "max_head_distance": 150
    },
    "audio": {
        "volume": 1.0,
        "language": "fr"
    },
    "camera": {
        "device": 0,
        "flip": True
    }
}

# Add after CONFIG definition
temp_settings = {}  # Will store temporary values while adjusting settings

class DetectionMode:
    STRICT = "strict"      # Très sensible, détecte tout mouvement
    NORMAL = "normal"      # Mode par défaut
    RELAXED = "relaxed"    # Plus tolérant
    
    @staticmethod
    def apply_mode(mode, config):
        if mode == DetectionMode.STRICT:
            config['detection']['required_duration'] = 1.0
            config['detection']['pull_threshold'] = 1
        elif mode == DetectionMode.RELAXED:
            config['detection']['required_duration'] = 2.0
            config['detection']['pull_threshold'] = 2

class PullingStats:
    def __init__(self):
        self.triggers = []
        self.daily_stats = {}
        self.load_stats()
    
    def add_trigger(self):
        now = time.time()
        self.triggers.append(now)
        self.update_daily_stats()
        self.save_stats()
    
    def get_daily_report(self):
        today = time.strftime("%Y-%m-%d")
        return f"Today's triggers: {self.daily_stats.get(today, 0)}"

def get_audio_files(folder):
    return [f for f in os.listdir(folder) if f.endswith(('.mp3', '.wav'))]

def generate_tts(phrase, filename):
    filepath = os.path.join(AUDIO_FOLDER, filename)
    if not os.path.exists(filepath):
        tts = gTTS(text=phrase, lang='en')
        tts.save(filepath)
    return filepath

def play_audio(audio_file):
    try:
        pygame.mixer.music.unload()  # Unload any previously loaded music
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # Wait for the audio to finish or be interrupted
        while pygame.mixer.music.get_busy() and not control_event.is_set():
            pygame.time.Clock().tick(10)  # Control the loop rate
            
        # Ensure the music stops and unloads
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        
    except Exception as e:
        print(f"Erreur de lecture audio: {e}")
        # Try to reinitialize mixer if there's an error
        try:
            pygame.mixer.quit()
            pygame.mixer.init()
        except:
            pass

def play_message():
    """Play audio from stock folder or generate TTS based on user choice"""
    global USE_TTS  # Move global declaration to the top of the function
    
    if USE_TTS:
        # Use TTS
        phrase = random.choice(MOTIVATIONAL_PHRASES)
        filename = f"hair_touch_{int(time.time())}.mp3"
        generate_tts(phrase, filename)
        play_audio(os.path.join(AUDIO_FOLDER, filename))
    else:
        # Use stock audio files
        stock_audio_files = [f for f in os.listdir(STOCK_AUDIO_FOLDER) 
                           if f.endswith(('.mp3', '.wav'))]
        if stock_audio_files:
            audio_file = os.path.join(STOCK_AUDIO_FOLDER, random.choice(stock_audio_files))
            play_audio(audio_file)
        else:
            # Fallback to TTS if stock folder became empty
            print("\nWarning: Stock audio folder is empty, falling back to TTS")
            USE_TTS = True
            play_message()


def adjust_exposure(frame):
    # Conversion en LAB pour travailler sur la luminance
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    
    # Fusionner les canaux et reconvertir en BGR
    processed_lab = cv2.merge((l, a, b))
    return cv2.cvtColor(processed_lab, cv2.COLOR_LAB2BGR)


def detect_hair_touch():
    global last_hair_trigger
    hands = mp_hands.Hands(
        min_detection_confidence=0.7,
        max_num_hands=1,  # On ne suit qu'une seule main
        model_complexity=0,  # Utiliser le modèle le plus léger
        static_image_mode=False
    )
    
    face_mesh = mp_face_mesh.FaceMesh(
        min_detection_confidence=0.5,
        max_num_faces=1,  # On ne suit qu'un seul visage
        refine_landmarks=False,  # Désactiver le raffinement des landmarks
        static_image_mode=False,
        min_tracking_confidence=0.5
    )
    mp_drawing = mp.solutions.drawing_utils
    drawing_spec_hands = mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2)
    drawing_spec_face = mp_drawing.DrawingSpec(color=(0,0,255), thickness=1, circle_radius=1)
    
    # Try different camera indices
    camera_index = 0
    cap = cv2.VideoCapture(camera_index)
    # Essayer de régler la FPS matériellement
    cap.set(cv2.CAP_PROP_FPS, 10)
    # Ajouter dans la section d'initialisation de la caméra (après cap = cv2.VideoCapture(camera_index))
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Désactiver l'exposition automatique
    cap.set(cv2.CAP_PROP_EXPOSURE, -4)  # Ajuster selon la caméra (-1 à -8 typiquement)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)  # Désactiver la balance des blancs automatique
    
    while not cap.isOpened() and camera_index < 3:
        print(f"Trying camera index {camera_index}...")
        camera_index += 1
        cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print("Erreur: Impossible d'ouvrir la caméra")
        return
    else:
        print(f"Caméra trouvée à l'index {camera_index}")
    
    # Test the camera feed
    success, test_frame = cap.read()
    if success:
        h, w, _ = test_frame.shape
        print(f"Résolution de la caméra: {w}x{h}")
    
    # Define eye landmarks (using right and left eyes)
    RIGHT_EYE = 159  # Right eye outer corner
    LEFT_EYE = 386   # Left eye outer corner

  
    # Add variables to track hand movement and time
    last_hand_y = None
    pull_threshold = 1
    movement_window = []
    window_size = 5
    
    # Add time tracking variables
    hand_near_head_start = None
    max_head_distance = 150  # pixels - adjust this value based on your needs
    
    # Add more detection points
    FOREHEAD = 10  # Forehead landmark
    CROWN = 152    # Top of head landmark
    TEMPLES = [447, 227]  # Temple landmarks
    
    last_time = time.time()
    
    settings_window_active = False
    settings_window_exists = False
    
    # After camera initialization, set a fixed window size
    cv2.namedWindow('Gesture Tracking', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Gesture Tracking', 1280, 720)  # Adjust size as needed
    
    # Réduire la résolution de la caméra
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Limiter le FPS
    cap.set(cv2.CAP_PROP_FPS, 15)
    
    # Ajouter une variable pour le frame skipping
    frame_counter = 0
    process_every_n_frames = 3  # Traiter une frame sur 2
    
# Add reference hand size calculation
    def get_hand_size(hand_landmarks, frame_width, frame_height):
    # Optimized: Vectorized calculation with NumPy
        landmarks_np = np.array([(lm.x * frame_width, lm.y * frame_height) for lm in hand_landmarks.landmark])
        x_coords = landmarks_np[:, 0]
        y_coords = landmarks_np[:, 1]
        return (np.max(x_coords) - np.min(x_coords)) * (np.max(y_coords) - np.min(y_coords))

    def get_head_size(face_landmarks, frame_width, frame_height):
        # Optimized: Vectorized calculation
        landmarks_np = np.array([(lm.x * frame_width, lm.y * frame_height) for lm in face_landmarks.landmark])
        x_coords = landmarks_np[:, 0]
        y_coords = landmarks_np[:, 1]
        return (np.max(x_coords) - np.min(x_coords)) * (np.max(y_coords) - np.min(y_coords))
    
    while True:
        success, frame = cap.read()
        if not success:
            continue
        
        current_time = time.time()
            
        # Vérifier la surexposition
        if is_overexposed(frame):
            # Ajustement dynamique de l'exposition
            current_exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
            cap.set(cv2.CAP_PROP_EXPOSURE, current_exposure * 0.9)
            cv2.putText(frame, "Overexposure detected!", (20, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            
        # Skip frames pour réduire la charge CPU
        if frame_counter % process_every_n_frames != 0:
            frame_counter += 1
            continue
            
        # Flip l'image AVANT le traitement
        frame = cv2.flip(frame, 1)
        frame = adjust_exposure(frame)  # Appliquer le prétraitement
            
        # Réduire la taille de l'image pour le traitement
        frame_small = cv2.resize(frame, (320, 240))
        
        # Faire le traitement sur l'image réduite
        image = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
        
        try:
                # Détections sur l'image réduite
                hand_results = hands.process(image)
                if hand_results.multi_hand_landmarks:
                    face_results.multi_face_landmarks  # Only process hands if face detected
                else:
                    face_results = None

                face_results = face_mesh.process(image)
                
                # Utiliser directement frame comme display_frame puisqu'il est déjà flippé
                display_frame = frame
                
                # Ne dessiner les landmarks que si nécessaire
                if settings_window_active:
                    if hand_results.multi_hand_landmarks:
                        for hand_landmarks in hand_results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(display_frame, hand_landmarks, mp_hands.HAND_CONNECTIONS, drawing_spec_hands)
                    
                    if face_results.multi_face_landmarks:
                        for face_landmarks in face_results.multi_face_landmarks:
                            mp_drawing.draw_landmarks(display_frame, face_landmarks, mp_face_mesh.FACEMESH_CONTOURS, drawing_spec_face)
                
                if hand_results.multi_hand_landmarks and face_results.multi_face_landmarks:
                    for hand_landmarks in hand_results.multi_hand_landmarks:
                        index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                        
                        for face_landmarks in face_results.multi_face_landmarks:
                            right_eye = face_landmarks.landmark[RIGHT_EYE]
                            left_eye = face_landmarks.landmark[LEFT_EYE]
                            
                            h, w, _ = frame.shape
                            index_y = index_tip.y * h
                            index_x = index_tip.x * w
                            eye_level = min(right_eye.y * h, left_eye.y * h)
                            eye_x = (right_eye.x + left_eye.x) * w / 2
                            
                            # Calculate distance from hand to head
                            distance_to_head = abs(index_x - eye_x)
                            
                            # Calculate sizes
                            hand_size = get_hand_size(hand_landmarks, w, h)
                            head_size = get_head_size(face_landmarks, w, h)
                            
                            # Calculate size ratio (hand should be roughly 1/4 to 1/2 of head size when at same depth)
                            size_ratio = hand_size / head_size
                            
                            # Check if hand is at similar depth as head
                            is_at_same_depth = 0.15 < size_ratio < 0.6  # Adjust these thresholds as needed
                            
                            # Add depth check to detection condition
                            if index_y < eye_level and distance_to_head < max_head_distance and is_at_same_depth:
                                if hand_near_head_start is None:
                                    hand_near_head_start = time.time()
                                
                                # Check if hand has been near head long enough
                                if (time.time() - hand_near_head_start) >= CONFIG['detection']['required_duration']:
                                    # Now check for pulling motion
                                    if last_hand_y is not None:
                                        movement = index_y - last_hand_y
                                        movement_window.append(movement)
                                        if len(movement_window) > window_size:
                                            movement_window.pop(0)
                                        
                                        total_movement = sum(movement_window)
                                        
                                        if total_movement > pull_threshold:
                                            with hair_lock:
                                                if time.time() - last_hair_trigger > hair_trigger_cooldown:
                                                    last_hair_trigger = time.time()
                                                    play_message()  # Replace the TTS code with this call
                                                    print(f"Détection de traction cheveux à {time.ctime()}")
                                                    movement_window.clear()
                                                    hand_near_head_start = None  # Reset timer
                                
                                # Draw visual feedback
                                if hand_near_head_start is not None:
                                    if (current_time - hand_near_head_start) >= CONFIG['detection']['required_duration']:
                                        # Draw progress bar
                                        progress = int((current_time - hand_near_head_start / CONFIG['detection']['required_duration']) * w)
                                        cv2.line(display_frame, (0, 30), (progress, 30), (0, 255, 0), 5)
                                
                                last_hand_y = index_y
                                # Draw a line at eye level for visualization
                                cv2.line(display_frame, (0, int(eye_level)), (w, int(eye_level)), (0, 255, 255), 2)
                            else:
                                # Reset when hand moves away from head
                                hand_near_head_start = None
                                last_hand_y = None
                                movement_window.clear()
                            # Optional: Display depth information
                            if settings_window_active:  # Only show when settings window is open
                                cv2.putText(display_frame, f"Depth ratio: {size_ratio:.2f}", 
                                        (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                                        (0,255,0) if is_at_same_depth else (0,0,255), 2)
        except Exception as e:
            print(f"Erreur de traitement: {str(e)}")
            continue
        
        # Calcul et affichage FPS
        fps = 1 / (current_time - last_time + 1e-6)  # Éviter division par zéro
        last_time = current_time
        cv2.putText(display_frame, f"FPS: {int(fps)}", (10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
        
        # Mettre à jour l'affichage moins souvent
        if frame_counter % 3 == 0:  # Update display every 3 frames
            frame = add_config_interface(display_frame)
            cv2.imshow('Gesture Tracking', display_frame)
        
        # Check if settings window was closed by user (X button)
        if settings_window_active and settings_window_exists:
            try:
                # Try to get window property, will fail if window was closed
                prop = cv2.getWindowProperty('Settings', cv2.WND_PROP_VISIBLE)
                if prop < 0:  # Window was closed
                    settings_window_active = False
                    settings_window_exists = False
                    cv2.waitKey(1)  # Process window events
            except:
                settings_window_active = False
                settings_window_exists = False
                cv2.waitKey(1)
        
        key = cv2.waitKey(1) & 0xFF
        
        # Handle key presses
        if key == ord('q'):
            break
        elif key == ord('s'):
            settings_window_active = not settings_window_active
            if settings_window_active:
                if not settings_window_exists:
                    show_settings()
                    settings_window_exists = True
            else:
                if settings_window_exists:
                    try:
                        cv2.destroyWindow('Settings')
                        cv.waitKey(1)
                    except:
                        pass
                    settings_window_exists = False
        elif key == ord('a') and settings_window_active:
            # Apply settings changes from temp_settings to CONFIG
            CONFIG['detection']['trigger_cooldown'] = temp_settings['trigger_cooldown']
            CONFIG['detection']['required_duration'] = temp_settings['required_duration']
            CONFIG['detection']['pull_threshold'] = temp_settings['pull_threshold']
            print("\nParamètres mis à jour:")
            print(f"Cooldown: {CONFIG['detection']['trigger_cooldown']}s")
            print(f"Duration: {CONFIG['detection']['required_duration']}s")
            print(f"Threshold: {CONFIG['detection']['pull_threshold']}")
            save_config()
        elif key == ord('r'):
            # Reset to default settings
            CONFIG['detection'] = {
                "hand_confidence": 0.7,
                "face_confidence": 0.5,
                "trigger_cooldown": 3,
                "required_duration": 1,
                "pull_threshold": 1,
                "max_head_distance": 150
            }
            if settings_window_active and settings_window_exists:
                show_settings()  # This will also reset temp_settings

    cap.release()
    cv2.destroyAllWindows()

def add_config_interface(frame):
    """Add configuration controls to the video frame"""
    h, w, _ = frame.shape
    # Larger text size and thickness
    cv2.putText(frame, "Controls:", (20, h-100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
    cv2.putText(frame, "Q: Quit | S: Settings | R: Reset", (20, h-60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
    
    # Afficher le temps actuel
    cv2.putText(frame, f"Temps detection: {CONFIG['detection']['required_duration']:.1f}s", 
                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    return frame

def update_cooldown(value):
    """Callback for cooldown trackbar"""
    CONFIG['detection']['trigger_cooldown'] = value

def update_duration(value):
    """Callback for duration trackbar"""
    CONFIG['detection']['required_duration'] = value / 10.0  # Convert back to seconds

def show_settings():
    """Show settings window with trackbars"""
    global temp_settings
    
    # Create temporary settings for modifications
    temp_settings = {
        'required_duration': CONFIG['detection']['required_duration'],
        'trigger_cooldown': CONFIG['detection']['trigger_cooldown'],
        'pull_threshold': CONFIG['detection']['pull_threshold']
    }
    
    cv2.namedWindow('Settings', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Settings', 1000, 400)
    
    # Create a blank image for the settings window
    settings_img = np.zeros((400, 1000, 3), dtype=np.uint8)
    
    # Add title
    cv2.putText(settings_img, "Settings", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    # Add labels for each setting with descriptions
    y_pos = 80
    spacing = 70
    
    # Cooldown setting
    cv2.putText(settings_img, "Trigger Cooldown: Temps minimum entre alertes (secondes)", 
                (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    cv2.createTrackbar('Cooldown', 'Settings', 
                      temp_settings['trigger_cooldown'], 10,
                      lambda x: temp_settings.__setitem__('trigger_cooldown', x))
    
    # Duration setting
    y_pos += spacing
    cv2.putText(settings_img, "Required Duration: Temps de detection necessaire (secondes)", 
                (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    cv2.createTrackbar('Duration', 'Settings', 
                      int(temp_settings['required_duration']*10), 50,
                      lambda x: temp_settings.__setitem__('required_duration', x/10.0))
    
    # Threshold setting
    y_pos += spacing
    cv2.putText(settings_img, "Pull Threshold: Sensibilite de detection du mouvement", 
                (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    cv2.createTrackbar('Threshold', 'Settings',
                      temp_settings['pull_threshold'], 30, 
                      lambda x: temp_settings.__setitem__('pull_threshold', x))
    
    # Add apply button instructions
    y_pos += spacing + 30
    cv2.putText(settings_img, "Appuyer sur 'A' pour appliquer les changements", 
                (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Show the settings window
    cv2.imshow('Settings', settings_img)

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        return CONFIG

def save_config():
    with open('config.json', 'w') as f:
        json.dump(CONFIG, f, indent=4)

class DetectionError(Exception):
    pass

def safe_detection():
    try:
        detect_hair_touch()
    except cv2.error as e:
        print(f"Erreur caméra: {e}")
        time.sleep(5)
        return safe_detection()
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False

def list_available_cameras():
    """Return the first available camera index."""
    for index in range(10):  # Limit to a reasonable number of checks
        cap = cv2.VideoCapture(index)
        if cap.read()[0]:
            cap.release()
            return [index]
    return []

# Add this before camera initialization
available_cameras = list_available_cameras()
print(f"Caméras disponibles: {available_cameras}")
if not available_cameras:
    print("No cameras found. Exiting.")
    exit()

# Ajouter cette fonction de vérification
def is_overexposed(frame, threshold=220):
    small_frame = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray) > threshold

if __name__ == '__main__':
    print("\nHair-pulling detection starting...")
    print("-----------------------------------------------------")
    
    # Check for audio files
    stock_audio_files = [f for f in os.listdir(STOCK_AUDIO_FOLDER) 
                        if f.endswith(('.mp3', '.wav'))]
    
    if stock_audio_files:
        print(f"\nFound {len(stock_audio_files)} audio files in {STOCK_AUDIO_FOLDER}")
        print("\nChoose your audio feedback mode:")
        print("1. Text-to-speech")
        print("2. Stock audio files")
        
        while True:
            choice = input("\nEnter your choice (1-2) [default: 2]: ").strip()
            if choice == "1":
                USE_TTS = True
                print("\nUsing text-to-speech feedback")
                break
            elif choice == "2" or choice == "":
                USE_TTS = False
                print("\nUsing stock audio files for feedback")
                break
            else:
                print("Invalid choice. Please enter 1 or 2")
    else:
        print("\nNo audio files found in stock folder")
        print("Using text-to-speech feedback")
        USE_TTS = True
    
    # Délai d'initialisation pour permettre le démarrage d'Iriun
    time.sleep(2)
    
    # Lancer directement la détection
    safe_detection()