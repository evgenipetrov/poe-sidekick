"""Script to test screenshot capture and debug saving functionality."""

import asyncio
import logging
from pathlib import Path

from poe_sidekick.core.stream import ScreenshotStream
from poe_sidekick.core.window import GameWindow
from poe_sidekick.services.config import ConfigService


async def main() -> None:
    """Run screenshot capture test.

    Tests window detection, screenshot capture, and debug file saving.
    """
    # Configure logging to see debug messages
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # Initialize game window detection
    window = GameWindow()
    await window.initialize()

    if not window.find_window():
        logging.error("Could not find POE2 window. Make sure the game is running.")
        return

    # Bring game window to front
    if not await window.bring_to_front():
        logging.error("Could not bring game window to front")
        return

    # Get window region
    region = window.get_window_rect()
    if not region:
        logging.error("Could not get window region")
        return

    logging.info(f"Found game window at region: {region}")

    # Initialize config service
    config_service = ConfigService()
    await config_service.load_config("core")

    # Create and start the screenshot stream with config
    stream = ScreenshotStream(config_service)

    try:
        # Start capturing with game window region
        await stream.start(region)

        # Let it run for 5 seconds, checking window focus
        logging.info("Running screenshot capture for 5 seconds...")
        for _ in range(5):
            if not window.is_window_focused():
                logging.warning("Game window lost focus!")
            await asyncio.sleep(1)

        # Check if screenshots were saved
        screenshots_dir = Path(__file__).parent.parent / "data" / "screenshots"
        if screenshots_dir.exists():
            files = list(screenshots_dir.glob("frame_*.png"))
            logging.info(f"Found {len(files)} screenshot files in {screenshots_dir}")
            for file in files:
                logging.info(f"Screenshot saved: {file}")
        else:
            logging.error(f"Screenshots directory not found at {screenshots_dir}")

    finally:
        # Clean up
        await stream.stop()
        logging.info("Screenshot stream stopped")


if __name__ == "__main__":
    # asyncio.run lacks type annotations in some Python versions
    asyncio.run(main())
