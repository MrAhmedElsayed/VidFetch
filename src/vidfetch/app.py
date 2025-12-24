"""Main entry point for VidFetch application."""

import sys
import traceback
import logging

from .ui import VidFetchApp
from .utils import log_error
from .version import __version__

# Setup logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    try:
        logger.info(f"Starting VidFetch v{__version__}")
        logger.info("Initializing application...")
        app = VidFetchApp()
        logger.info("Application initialized, starting main loop...")
        app.mainloop()
        logger.info("Application closed normally")
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in main(): {e}", exc_info=True)
        log_error("Fatal error in main()", e)
        # Try to show error dialog if Tkinter is partially working
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # Hide main window
            error_msg = f"Application failed to start.\n\nError: {e}\n\n{traceback.format_exc()}"
            messagebox.showerror("VidFetch Error", error_msg)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
