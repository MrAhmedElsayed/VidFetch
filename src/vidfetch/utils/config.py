"""Configuration management."""

import json
from pathlib import Path


class Config:
    """Manages application configuration."""
    
    def __init__(self, config_file: Path = None):
        if config_file is None:
            # Use user's home directory for config
            config_file = Path.home() / "vidfetch_settings.json"
        self.file = config_file
        self.data = {"download_path": str(Path.home() / "Downloads" / "VidFetch")}
        self.load()
        
    def load(self):
        """Load configuration from file."""
        if self.file.exists():
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    self.data.update(json.load(f))
            except Exception:
                pass
            
    def save(self):
        """Save configuration to file."""
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass
        
    @property
    def download_path(self) -> Path:
        """Get the download path."""
        try:
            return Path(self.data["download_path"])
        except Exception:
            return Path.home() / "Downloads" / "VidFetch"

    def set_download_path(self, path: str | Path):
        """Set the download path."""
        self.data["download_path"] = str(path)
        self.save()

