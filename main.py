import logging
from config_manager import ConfigManager
from hair_pulling_detector import HairPullingDetector

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main entry point for the application."""
    setup_logging()
    logging.info("Starting Trichotillomania-Reminder application")
    
    config_manager = ConfigManager()
    detector = HairPullingDetector(config_manager.config)
    
    try:
        detector.start()
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Application error: {e}")
    finally:
        detector.cleanup()
        logging.info("Application shutdown complete")

if __name__ == "__main__":
    main()