import os
import random
import logging
import time
import hashlib
from typing import List
import json
import tempfile
import threading
from gtts import gTTS
import pygame
from resource_manager import ResourceManager

class AudioManager:
    """Manages audio playback for motivational messages using gTTS or stock audio."""
    
    DEFAULT_PHRASES = [
        "You're stronger than this urge!",
        "Keep your hands free!",
        "You’ve got this, stay strong!",
        "Take a deep breath and relax."
    ]
    
    def __init__(self, audio_folder: str, stock_audio_folder: str, use_tts: bool = True, config=None):
        self.audio_folder = audio_folder
        self.stock_audio_folder = stock_audio_folder
        self.use_tts = use_tts
        self.config = config
        self.phrases = self._load_phrases()
        self.audio_files = []
        self.temp_files = []
        self._playback_lock = threading.Lock()
        self.cache_folder = ResourceManager.get_resource_path(os.path.join(audio_folder, "cache"))
        
        os.makedirs(self.cache_folder, exist_ok=True)
        logging.debug(f"TTS cache folder: {self.cache_folder}")
        
        pygame.mixer.init()
        
        if not self.use_tts:
            self._load_stock_audio()
        else:
            try:
                gTTS(text="test", lang="en")
                self._enforce_cache_limit()  # Clean cache on initialization
            except Exception as e:
                logging.error(f"Failed to initialize gTTS: {e}. Falling back to stock audio.")
                self.use_tts = False
                self._load_stock_audio()
    
    def set_mode(self, use_tts: bool) -> None:
        """Switch between gTTS and stock audio modes."""
        self.use_tts = use_tts
        if not self.use_tts:
            self._load_stock_audio()
        else:
            self.phrases = self._load_phrases()
            self._enforce_cache_limit()
    
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
            self._enforce_cache_limit()  # Clean cache after updating phrases
        except Exception as e:
            logging.error(f"Error saving phrases to phrases.json: {e}")
    
    def _load_stock_audio(self) -> None:
        """Load stock audio files from the stock audio folder."""
        self.audio_files = []
        try:
            for file in os.listdir(self.stock_audio_folder):
                if file.lower().endswith(('.mp3', '.wav')):
                    file_path = ResourceManager.get_resource_path(os.path.join(self.stock_audio_folder, file))
                    self.audio_files.append(file_path)
            if not self.audio_files and not self.use_tts:
                logging.warning("No stock audio files found. Falling back to TTS.")
                self.use_tts = True
                self.phrases = self._load_phrases()
        except Exception as e:
            logging.error(f"Error loading stock audio: {e}")
            if not self.use_tts:
                self.use_tts = True
                self.phrases = self._load_phrases()
    
    def reload_audio_files(self) -> None:
        """Reload audio files from stock_audio folder."""
        self._load_stock_audio()
    
    def _delete_temp_file_with_retry(self, temp_file: str, retries: int = 5, delay: float = 0.5) -> bool:
        """Attempt to delete a temporary file with retries."""
        for attempt in range(retries):
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logging.debug(f"Successfully deleted temp file: {temp_file}")
                    return True
                return True
            except OSError as e:
                if e.winerror == 32:
                    logging.debug(f"Temp file {temp_file} in use, retrying ({attempt + 1}/{retries})")
                    time.sleep(delay)
                else:
                    logging.error(f"Error deleting temp file {temp_file}: {e}")
                    return False
        logging.warning(f"Failed to delete temp file {temp_file} after {retries} attempts")
        return False
    
    def _get_cached_audio_path(self, message: str) -> str:
        """Generate a consistent file path for a given message using MD5 hash."""
        message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_folder, f"tts_{message_hash}.mp3")
    
    def _get_cache_size(self) -> float:
        """Calculate the total size of the cache folder in MB."""
        total_size = 0
        try:
            for file in os.listdir(self.cache_folder):
                file_path = os.path.join(self.cache_folder, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            return total_size / (1024 * 1024)  # Convert bytes to MB
        except Exception as e:
            logging.error(f"Error calculating cache size: {e}")
            return 0.0
    
    def _enforce_cache_limit(self) -> None:
        """Remove oldest files if cache size exceeds the limit."""
        if not self.config:
            logging.warning("No config provided, skipping cache limit enforcement")
            return
        
        cache_limit_mb = self.config.audio.get('tts_cache_limit', 50.0)
        current_size_mb = self._get_cache_size()
        
        if current_size_mb <= cache_limit_mb:
            logging.debug(f"Cache size {current_size_mb:.2f} MB is within limit {cache_limit_mb:.2f} MB")
            return
        
        logging.info(f"Cache size {current_size_mb:.2f} MB exceeds limit {cache_limit_mb:.2f} MB, cleaning up...")
        
        # Get list of files with their modification times
        files = []
        try:
            for file in os.listdir(self.cache_folder):
                file_path = os.path.join(self.cache_folder, file)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    files.append((file_path, mtime))
            
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x[1])
            
            # Delete oldest files until size is under limit
            while current_size_mb > cache_limit_mb and files:
                file_path, _ = files.pop(0)
                try:
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                    if self._delete_temp_file_with_retry(file_path):
                        current_size_mb -= file_size
                        logging.debug(f"Deleted cache file {file_path} ({file_size:.2f} MB)")
                except Exception as e:
                    logging.error(f"Failed to delete cache file {file_path}: {e}")
            
            logging.info(f"Cache cleanup complete, new size: {current_size_mb:.2f} MB")
        except Exception as e:
            logging.error(f"Error enforcing cache limit: {e}")
    
    def _play_tts_message(self, message: str) -> None:
        """Play a gTTS message, reusing cached audio if available."""
        try:
            audio_file = self._get_cached_audio_path(message)
            
            if not os.path.exists(audio_file):
                logging.debug(f"Generating new TTS audio for phrase: {message}")
                tts = gTTS(text=message, lang="en")
                tts.save(audio_file)
                with self._playback_lock:
                    self.temp_files.append(audio_file)
                self._enforce_cache_limit()  # Check cache size after adding new file
            
            with self._playback_lock:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
        except Exception as e:
            logging.error(f"Error playing TTS message: {e}")
    
    def play_message(self) -> None:
        """Play a random motivational message."""
        if self.use_tts:
            if not self.phrases:
                logging.warning("No phrases available to play")
                return
            message = random.choice(self.phrases)
            threading.Thread(target=self._play_tts_message, args=(message,), daemon=True).start()
        else:
            if not self.audio_files:
                logging.warning("No audio files available to play")
                return
            try:
                with self._playback_lock:
                    pygame.mixer.music.load(random.choice(self.audio_files))
                    pygame.mixer.music.play()
            except Exception as e:
                logging.error(f"Error playing audio file: {e}")
    
    def cleanup(self) -> None:
        """Clean up audio resources and temporary files."""
        try:
            with self._playback_lock:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            
            time.sleep(0.5)
            
            failed_deletions = []
            for temp_file in self.temp_files[:]:
                if not self._delete_temp_file_with_retry(temp_file, retries=5, delay=0.5):
                    failed_deletions.append(temp_file)
            
            if failed_deletions:
                logging.error(f"Failed to delete the following temporary files: {failed_deletions}")
            else:
                logging.info("All temporary audio files deleted successfully")
            
            self.temp_files = []
            self._enforce_cache_limit()  # Final cache cleanup
        except Exception as e:
            logging.error(f"Error during audio cleanup: {e}")