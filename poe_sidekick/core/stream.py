"""Screenshot stream implementation using dxcam and RxPY."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import dxcam  # type: ignore[import-untyped]
from rx.core.observable.observable import Observable
from rx.subject import Subject

from poe_sidekick.core.types import DXCamera


class ScreenshotStream:
    """Provides a stream of screenshots for game state analysis."""

    def __init__(self) -> None:
        """Initialize stream with no active camera."""
        self._camera: Optional[DXCamera] = None
        self._subject = Subject()
        self._running = False
        self._capture_task: Optional[asyncio.Task] = None
        self._fps = 30  # Configurable frames per second

        # Create screenshots directory for debug captures
        project_root = Path(__file__).parent.parent.parent
        self._debug_dir = project_root / "data" / "screenshots"
        self._debug_dir.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Created debug screenshots directory at: {self._debug_dir}")
        self._frame_count = 0

    async def _capture_loop(self) -> None:
        """Continuous capture loop."""
        frame_delay = 1 / self._fps
        while self._running:
            if self._camera:
                frame = self._camera.grab()
                if frame is not None:
                    logging.debug("Frame captured successfully")
                    self._subject.on_next(frame)

                    # Save every 30th frame for debug verification
                    self._frame_count += 1
                    if self._frame_count % 30 == 0:
                        logging.debug(f"Attempting to save frame {self._frame_count}")
                        try:
                            import cv2
                            import numpy as np

                            # Ensure frame is a numpy array for OpenCV
                            frame_array = np.asarray(frame)
                            if frame_array.size == 0:
                                logging.error("Frame is empty, skipping save")
                                continue
                            debug_path = self._debug_dir / f"frame_{self._frame_count}.png"
                            success = cv2.imwrite(str(debug_path), frame_array)
                            if success:
                                logging.debug(f"Successfully saved debug frame to {debug_path}")
                            else:
                                logging.error("cv2.imwrite failed to save the frame")
                        except Exception as e:
                            logging.error(f"Failed to save debug frame: {e}", exc_info=True)

            await asyncio.sleep(frame_delay)

    async def start(self, region: Optional[tuple[int, int, int, int]] = None) -> None:
        logging.info("Starting screenshot stream...")
        """Start capturing and streaming screenshots.

        Args:
            region: Optional capture region as (left, top, right, bottom)
        """
        if self._running:
            return

        camera = dxcam.create()
        if region:
            camera.region = region

        self._camera = camera
        self._running = True
        self._capture_task = asyncio.create_task(self._capture_loop())

    async def stop(self) -> None:
        """Stop the screenshot stream and cleanup."""
        if self._running:
            self._running = False
            if self._capture_task:
                self._capture_task.cancel()
                from contextlib import suppress

                with suppress(asyncio.CancelledError):
                    await self._capture_task
            if self._camera:
                self._camera = None
            self._subject.on_completed()

    @property
    def observable(self) -> Observable:
        """Access the RxPY observable for subscribing to screenshots."""
        return self._subject
