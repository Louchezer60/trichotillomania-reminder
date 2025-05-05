#!/usr/bin/env python3
import os
import logging
from config_manager import ConfigManager
from resource_manager import ResourceManager
from hair_pulling_detector import HairPullingDetector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main application entry point."""
    print("Starting Trichotillomania-Reminder Detection System")
    print("--------------------------------------------------")
    
    # Set working directory to script location
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create necessary directories
    audio_folder = 'audio'
    stock_audio_folder = 'stock_audio'
    ResourceManager.ensure_directories([audio_folder, stock_audio_folder])
    
    # Check for stock audio files and provide hint
    if len(os.listdir(stock_audio_folder)) == 0:
        print("\nNo audio files found in stock_audio folder.")
        print("To use custom alerts, add MP3 or WAV files to the 'stock_audio' folder.")
        print("Falling back to text-to-speech for alerts.\n")
    
    # Load configuration
    config_manager = ConfigManager()
    
    # Initialize and start detector
    detector = HairPullingDetector(config_manager.config)
    
    try:
        detector.start()
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        logging.error(f"Application error: {e}")
        print(f"\nApplication error: {e}")
    finally:
        detector.cleanup()
        print("\nApplication shutdown complete")

if __name__ == "__main__":
    main()