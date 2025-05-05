from config_manager import Config

class DetectionMode:
    """Detection sensitivity modes."""
    STRICT = "strict"
    NORMAL = "normal"
    RELAXED = "relaxed"
    
    @staticmethod
    def apply_mode(mode: str, config: Config) -> None:
        """Apply detection mode settings to config."""
        if mode == DetectionMode.STRICT:
            config.detection['required_duration'] = 1.0
            config.detection['pull_threshold'] = 1
        elif mode == DetectionMode.RELAXED:
            config.detection['required_duration'] = 2.0
            config.detection['pull_threshold'] = 2