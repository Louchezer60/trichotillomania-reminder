import os
import random
import logging
from typing import List
import json
import tempfile
from gtts import gTTS
import pygame
from resource_manager import ResourceManager

class AudioManager:
    """Manages audio playback for motivational messages using gTTS."""
    
    DEFAULT_PHRASES = [
        "You're stronger than this urge!",
        "Keep your hands free!",
        "You’ve got this, stay strong!",
        "Take a deep breath and relax."
    ]
    
    def __init__(self, audio_folder: str, stock_audio_folder: str, use_tts: bool = True):
        self.audio_folder = audio_folder
        self.stock_audio_folder = stock_audio_folder
        self.use_tts = use_tts
        self.phrases = self._load_phrases()
        self.audio_files = []
        self.temp_files = []  # Track temporary MP3 files for cleanup
        
        pygame.mixer.init()
        
        if not self.use_tts:
            self._load_stock_audio()
        else:
            # Ensure gTTS is available
            try:
                # Test gTTS import
                gTTS(text="test", lang="en")
            except Exception as e:
                logging.error(f"Failed to initialize gTTS: {e}. Falling back to stock audio.")
                self.use_tts = False
                self._load_stock_audio()
    
    def _load_phrases(self) -> List[str]:
        """Load motivational phrases from phrases.json, create file with defaults if missing."""
        phrases_file = ResourceManager.get_resource_path("phrases.json")
        try:
            if not os.path.exists(phrases_file):
                with open(phrases_file, 'w') as f:
                    json.dump(self.DEFAULT_PHRASES, f, indent=4)
                logging.info(f"Created phrases.json with default phrases at {phrases_file}")
                return self.DEFAULT_PHRASES
            with open(phrases_file, 'r') as f:
                phrases = json.load(f)
                if not isinstance(phrases, list) or not all(isinstance(p, str) for p in phrases):
                    raise ValueError("phrases.json must contain a list of strings")
                return phrases if phrases else self.DEFAULT_PHRASES
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Error loading phrases.json: {e}. Using default phrases.")
            with open(phrases_file, 'w') as f:
                json.dump(self.DEFAULT_PHRASES, f, indent=4)
            return self.DEFAULT_PHRASES
    
    def save_phrases(self, phrases: List[str]) -> None:
        """Save phrases to phrases.json."""
        phrases_file = ResourceManager.get_resource_path("phrases.json")
        try:
            with open(phrases_file, 'w') as f:
                json.dump(phrases, f, indent=4)
            self.phrases = phrases
            logging.info("Phrases saved successfully")
        except Exception as e:
            logging.error(f"Error saving phrases to phrases.json: {e}")
    
    def _load_stock_audio(self) -> None:
        """Load stock audio files from the stock audio folder."""
        self.audio_files = []
        try:
            for file in os.listdir(self.stock_audio_folder):
                if file.endswith(('.mp3', '.wav')):
                    file_path = ResourceManager.get_resource_path(os.path.join(self.stock_audio_folder, file))
                    self.audio_files.append(file_path)
            if not self.audio_files:
                logging.warning("No stock audio files found. Falling back to TTS.")
                self.use_tts = True
        except Exception as e:
            logging.error(f"Error loading stock audio: {e}")
            self.use_tts = True
    
    def play_message(self) -> None:
        """Play a random motivational message."""
        if not self.phrases:
            logging.warning("No phrases available to play")
            return
            
        message = random.choice(self.phrases)
        
        if self.use_tts:
            try:
                # Generate temporary MP3 file with gTTS
                tts = gTTS(text=message, lang="en")
                temp_file = os.path.join(tempfile.gettempdir(), f"tts_{random.randint(0, 1000000)}.mp3")
                tts.save(temp_file)
                self.temp_files.append(temp_file)
                
                # Play the MP3 file
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            except Exception as e:
                logging.error(f"Error playing gTTS message: {e}")
        elif self.audio_files:
            try:
                pygame.mixer.music.load(random.choice(self.audio_files))
                pygame.mixer.music.play()
            except Exception as e:
                logging.error(f"Error playing audio file: {e}")
    
    def cleanup(self) -> None:
        """Clean up audio resources and temporary files."""
        try:
            pygame.mixer.quit()
            # Remove temporary MP3 files
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logging.error(f"Error removing temp file {temp_file}: {e}")
            self.temp_files = []
        except Exception as e:
            logging.error(f"Error during audio cleanup: {e}")