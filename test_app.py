"""Test script to run VidFetch with full error logging."""

import sys
import traceback
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('vidfetch_debug.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)

try:
    logger.info("=" * 60)
    logger.info("Starting VidFetch Test")
    logger.info("=" * 60)
    
    from src.vidfetch.app import main
    
    logger.info("Calling main()...")
    main()
    
except KeyboardInterrupt:
    logger.info("Application interrupted by user")
except Exception as e:
    logger.error("=" * 60)
    logger.error("FATAL ERROR")
    logger.error("=" * 60)
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Error message: {str(e)}")
    logger.error("Full traceback:")
    logger.error(traceback.format_exc())
    logger.error("=" * 60)
    sys.exit(1)

