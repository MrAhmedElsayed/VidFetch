"""Path resolution utilities."""

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Resolve paths correctly for PyInstaller / standalone builds."""
    # Check if running as compiled executable (PyInstaller sets sys.frozen = True)
    if getattr(sys, "frozen", False):
        # PyInstaller compiled mode
        # For onefile: data files are extracted to temp directory (_MEIPASS)
        # For onedir: data files are next to executable
        
        # PyInstaller onefile mode sets _MEIPASS to temp directory
        if hasattr(sys, "_MEIPASS"):
            # Onefile mode: use temp directory
            base_path = Path(sys._MEIPASS)
        else:
            # Onedir mode: use executable directory
            base_path = Path(sys.executable).parent
        
        return base_path / relative_path
    else:
        # Development mode: use project root
        return Path(__file__).parent.parent.parent.parent / relative_path

