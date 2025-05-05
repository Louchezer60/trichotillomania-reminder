import os
import sys
from typing import List

class ResourceManager:
    """Manages access to application resources."""
    
    @staticmethod
    def get_resource_path(relative_path: str) -> str:
        """Get absolute path to resource, works for dev and for PyInstaller."""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def ensure_directories(dirs: List[str]) -> None:
        """Ensure all directories in the list exist."""
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)