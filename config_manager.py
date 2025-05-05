import json
from dataclasses import dataclass
from typing import Dict, Any
import logging

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
    full_head_detection: bool
    show_meshes: bool  # Added for mesh toggle persistence

class ConfigManager:
    DEFAULT_CONFIG = {
        "detection": {
            "hand_confidence": 0.7,
            "face_confidence": 0.5,
            "trigger_cooldown": 3,
            "required_duration": 0.75,
            "pull_threshold": 1,
            "max_head_distance": 100,
            "full_head_detection": False,
            "show_meshes": True  # Default to showing meshes
        },
        "audio": {"volume": 1.0, "language": "en"},
        "camera": {"device": 0, "flip": True}
    }
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration values and return corrected config."""
        validated = config_data.copy()
        
        # Detection settings
        detection = validated.get('detection', {})
        detection.setdefault('hand_confidence', self.DEFAULT_CONFIG['detection']['hand_confidence'])
        detection.setdefault('face_confidence', self.DEFAULT_CONFIG['detection']['face_confidence'])
        detection.setdefault('trigger_cooldown', self.DEFAULT_CONFIG['detection']['trigger_cooldown'])
        detection.setdefault('required_duration', self.DEFAULT_CONFIG['detection']['required_duration'])
        detection.setdefault('pull_threshold', self.DEFAULT_CONFIG['detection']['pull_threshold'])
        detection.setdefault('max_head_distance', self.DEFAULT_CONFIG['detection']['max_head_distance'])
        detection.setdefault('full_head_detection', self.DEFAULT_CONFIG['detection']['full_head_detection'])
        detection.setdefault('show_meshes', self.DEFAULT_CONFIG['detection']['show_meshes'])

        # Ensure types and ranges
        try:
            detection['hand_confidence'] = max(0.0, min(1.0, float(detection['hand_confidence'])))
            detection['face_confidence'] = max(0.0, min(1.0, float(detection['face_confidence'])))
            detection['trigger_cooldown'] = max(0, int(detection['trigger_cooldown']))
            detection['required_duration'] = max(0.0, float(detection['required_duration']))
            detection['pull_threshold'] = max(0, int(detection['pull_threshold']))
            detection['max_head_distance'] = max(10, int(detection['max_head_distance']))
            detection['full_head_detection'] = bool(detection['full_head_detection'])
            detection['show_meshes'] = bool(detection['show_meshes'])
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid detection config value: {e}. Reverting to defaults.")
            detection.update(self.DEFAULT_CONFIG['detection'])

        validated['detection'] = detection

        # Audio settings
        audio = validated.get('audio', {})
        audio.setdefault('volume', self.DEFAULT_CONFIG['audio']['volume'])
        audio.setdefault('language', self.DEFAULT_CONFIG['audio']['language'])
        try:
            audio['volume'] = max(0.0, min(1.0, float(audio['volume'])))
            audio['language'] = str(audio['language']) if audio['language'] in ['en', 'es', 'fr'] else 'en'
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid audio config value: {e}. Reverting to defaults.")
            audio.update(self.DEFAULT_CONFIG['audio'])
        
        validated['audio'] = audio

        # Camera settings
        camera = validated.get('camera', {})
        camera.setdefault('device', self.DEFAULT_CONFIG['camera']['device'])
        camera.setdefault('flip', self.DEFAULT_CONFIG['camera']['flip'])
        try:
            camera['device'] = max(0, int(camera['device']))
            camera['flip'] = bool(camera['flip'])
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid camera config value: {e}. Reverting to defaults.")
            camera.update(self.DEFAULT_CONFIG['camera'])
        
        validated['camera'] = camera
        return validated
    
    def load_config(self) -> Config:
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                validated_data = self.validate_config(config_data)
                return Config(**validated_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Config load error: {e}. Using default config.")
            return Config(**self.DEFAULT_CONFIG)
    
    def save_config(self) -> None:
        with open(self.config_file, 'w') as f:
            json.dump(self.config.__dict__, f, indent=4)
    
    def reset_to_default(self) -> None:
        self.config = Config(**self.DEFAULT_CONFIG)
        self.save_config()