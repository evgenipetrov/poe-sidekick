"""Screenshot stream implementation using dxcam and RxPY."""

import asyncio
import logging
import time
from collections import deque
from pathlib import Path
from typing import Optional, cast

# dxcam has no type stubs, but we need it for screen capture
import dxcam
import numpy as np
import psutil
from numpy.typing import NDArray
from rx.core.observable.observable import Observable
from rx.subject.subject import Subject

from poe_sidekick.core.types import DXCamera, StreamConfig, StreamMetrics
from poe_sidekick.services.config import ConfigService


class ScreenshotStreamConfigError(ValueError):
    """Raised when screenshot stream configuration is missing or invalid."""

    DEFAULT_MESSAGE = "Missing screenshot_stream configuration"

    def __init__(self, message: str = DEFAULT_MESSAGE) -> None:
        super().__init__(message)


class ScreenshotStream:
    """Provides a stream of screenshots for game state analysis."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize stream with configuration.

        Args:
            config_service: Service for accessing configuration values
        """
        self._config_service = config_service
        self._camera: Optional[DXCamera] = None
        self._subject = Subject()  # Type inference through usage
        self._running = False
        self._capture_task: Optional[asyncio.Task[None]] = None

        # Load config
        self._load_config()

        # Create screenshots directory for debug captures
        project_root = Path(__file__).parent.parent.parent
        self._debug_dir = project_root / "data" / "screenshots"
        self._debug_dir.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Created debug screenshots directory at: {self._debug_dir}")

        self._frame_count = 0
        self._last_frame_time = 0.0
        self._process = psutil.Process()

    def _load_config(self) -> None:
        """Load configuration values from config service."""
        config = self._config_service.get_value("core", "screenshot_stream")
        if not config:
            raise ScreenshotStreamConfigError()

        self._stream_config: StreamConfig = config

        # Initialize metrics with configured window sizes
        metrics_config = self._stream_config["metrics"]
        self._metrics: StreamMetrics = {
            "frame_times": deque(maxlen=metrics_config["frame_time_window"]),
            "memory_usage": deque(maxlen=metrics_config["memory_window"]),
            "processing_delays": deque(maxlen=metrics_config["processing_window"]),
            "dropped_frames": 0,
        }

        # Performance settings
        self._fps = self._stream_config["performance"]["target_fps"]
        self._frame_delay = 1 / self._fps
        self._max_memory = self._stream_config["performance"]["max_memory_mb"]
        self._max_processing = self._stream_config["performance"]["max_processing_ms"]
        self._debug_interval = metrics_config["debug_frame_interval"]

    def _update_frame_metrics(self, frame_start: float) -> None:
        """Update frame timing metrics."""
        if self._last_frame_time:
            frame_time = (frame_start - self._last_frame_time) * 1000
            self._metrics["frame_times"].append(frame_time)

            if frame_time > (self._frame_delay * 1000 * 1.25):  # 25% tolerance
                logging.warning(f"Frame time {frame_time:.2f}ms exceeds target {self._frame_delay * 1000:.2f}ms")
                self._metrics["dropped_frames"] += 1

    def _update_memory_metrics(self) -> None:
        """Update memory usage metrics."""
        memory_mb = self._process.memory_info().rss / (1024 * 1024)
        self._metrics["memory_usage"].append(memory_mb)

        if memory_mb > self._max_memory:
            logging.warning(f"Memory usage {memory_mb:.2f}MB exceeds limit {self._max_memory}MB")

    def _save_debug_frame(self, frame: NDArray[np.uint8]) -> None:
        """Save frame for debugging if interval is reached."""
        if self._frame_count % self._debug_interval == 0:
            logging.debug(f"Attempting to save debug frame {self._frame_count}")
            try:
                import cv2

                if frame.size == 0:
                    logging.error("Frame is empty, skipping save")
                    return
                debug_path = self._debug_dir / f"frame_{self._frame_count}.png"
                success = cv2.imwrite(str(debug_path), frame)
                if success:
                    logging.debug(f"Successfully saved debug frame to {debug_path}")
                else:
                    logging.error("cv2.imwrite failed to save the frame")
            except Exception as e:
                logging.error(f"Failed to save debug frame: {e}", exc_info=True)

    def _process_frame(self, frame: NDArray[np.uint8], frame_start: float) -> None:
        """Process captured frame and update metrics."""
        self._update_memory_metrics()

        # Process and emit frame
        self._subject.on_next(frame)
        processing_time = (time.perf_counter() - frame_start) * 1000
        self._metrics["processing_delays"].append(processing_time)

        if processing_time > self._max_processing:
            logging.warning(f"Frame processing time {processing_time:.2f}ms exceeds limit {self._max_processing}ms")

        # Handle debug frame saving
        self._frame_count += 1
        self._save_debug_frame(frame)

    async def _capture_loop(self) -> None:
        """Continuous capture loop with performance monitoring."""
        while self._running:
            frame_start = time.perf_counter()
            self._update_frame_metrics(frame_start)

            if self._camera:
                frame = self._camera.grab()
                if frame is not None:
                    frame_array = np.asarray(frame, dtype=np.uint8)
                    self._process_frame(frame_array, frame_start)
                else:
                    logging.warning("Failed to capture frame")
                    self._metrics["dropped_frames"] += 1

            self._last_frame_time = frame_start
            await asyncio.sleep(self._frame_delay)

    async def start(self, region: Optional[tuple[int, int, int, int]] = None) -> None:
        """Start capturing and streaming screenshots.

        Args:
            region: Optional capture region as (left, top, right, bottom)
        """
        logging.info("Starting screenshot stream...")
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

            # Log final metrics
            if self._metrics["frame_times"]:
                avg_frame_time = sum(self._metrics["frame_times"]) / len(self._metrics["frame_times"])
                avg_memory = sum(self._metrics["memory_usage"]) / len(self._metrics["memory_usage"])
                avg_processing = sum(self._metrics["processing_delays"]) / len(self._metrics["processing_delays"])

                logging.info(
                    "Screenshot stream metrics:\n"
                    f"  Average frame time: {avg_frame_time:.2f}ms\n"
                    f"  Average memory usage: {avg_memory:.2f}MB\n"
                    f"  Average processing time: {avg_processing:.2f}ms\n"
                    f"  Dropped frames: {self._metrics['dropped_frames']}"
                )

    @property
    def observable(self) -> Observable:
        """Access the RxPY observable for subscribing to screenshots."""
        return cast(Observable, self._subject)

    @property
    def metrics(self) -> StreamMetrics:
        """Access current performance metrics."""
        return self._metrics
