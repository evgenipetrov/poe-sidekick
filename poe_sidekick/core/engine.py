"""Engine module for POE Sidekick.

This module provides the central Engine class that manages the application lifecycle,
including window management, screenshot stream, modules, and workflows.
"""

import asyncio
import logging
from typing import Protocol

from poe_sidekick.core.window import GameWindow
from poe_sidekick.services.config import ConfigService


class WindowError(RuntimeError):
    """Exception raised for window-related errors."""

    def __init__(self, window_title: str, executable: str) -> None:
        """Initialize WindowError with detailed user-friendly message.

        Args:
            window_title: The title of the window being searched for
            executable: The executable name for the game process
        """
        self.window_title = window_title
        self.executable = executable
        self.message = self._create_user_message()
        super().__init__(self.message)

    def _create_user_message(self) -> str:
        return f"""
Unable to find {self.window_title}

This usually means:
1. Path of Exile 2 ({self.executable}) is not running
2. The game is running but not responding
3. The game window title has changed

Please ensure:
- Path of Exile 2 is running and responsive
- The game window is visible on your screen
        """.strip()


class Module(Protocol):
    async def cleanup(self) -> None: ...


class Engine:
    """Central engine class managing POE Sidekick's core functionality."""

    def __init__(self) -> None:
        """Initialize the Engine instance."""
        self._config = ConfigService()
        self._window = GameWindow()
        self._screenshot_stream = None  # Will be initialized later
        self._modules: dict[str, Module] = {}  # Will hold active modules
        self._running: bool = False
        self._shutdown_requested: bool = False
        self._logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the POE Sidekick engine.

        Raises:
            RuntimeError: If the Path of Exile 2 window cannot be found.
        """
        self._logger.info("Starting POE Sidekick engine...")

        # Load core configuration and initialize window
        await self._config.load_config("core")
        await self._window.initialize()

        try:
            # Try to detect the game window with retries
            await self._detect_window()

            if self._shutdown_requested:
                self._logger.info("Startup cancelled due to shutdown request")
                return

            self._running = True
            await self._window.bring_to_front()
            await self._initialize_components()
            self._logger.info("POE Sidekick engine started successfully")
        except Exception:
            self._shutdown_requested = True
            raise

    async def stop(self) -> None:
        """Stop the engine and cleanup resources."""
        if not self._running:
            return

        self._logger.info("Stopping POE Sidekick engine...")
        self._shutdown_requested = True
        self._running = False

        # Get timeout from config or use default
        timeout = self._config.get_value("core", "engine.shutdown_timeout", 5.0)
        await self._cleanup_components(timeout)
        self._logger.info("POE Sidekick engine stopped")

    async def _initialize_components(self) -> None:
        """Initialize screenshot stream, modules, and other components."""
        try:
            # Initialize screenshot stream
            # self._screenshot_stream = await ScreenshotStream.create(self._window)

            # Initialize modules
            # for module_name, module_class in self._get_module_classes().items():
            #     self._modules[module_name] = await module_class.create(
            #         self._screenshot_stream, self._window
            #     )

            # TODO: Set up error handlers
            pass

        except Exception:
            self._logger.exception("Failed to initialize components")
            await self.stop()
            raise

    async def _cleanup_components(self, timeout: float) -> None:
        """Cleanup all components properly."""
        try:
            cleanup_tasks = []

            # Clean up modules
            for module in self._modules.values():
                cleanup_tasks.append(asyncio.create_task(module.cleanup()))

            # Clean up screenshot stream
            if self._screenshot_stream is not None:
                cleanup_tasks.append(asyncio.create_task(self._screenshot_stream.cleanup()))

            # Wait for all cleanup tasks with timeout
            await asyncio.wait_for(asyncio.gather(*cleanup_tasks), timeout=timeout)

        except asyncio.TimeoutError:
            self._logger.warning(f"Component cleanup timed out after {timeout} seconds")
        except Exception:
            self._logger.exception("Error during component cleanup")
        finally:
            self._modules.clear()
            self._screenshot_stream = None

    @property
    def is_running(self) -> bool:
        """Check if the engine is currently running.

        Returns:
            bool: True if the engine is running, False otherwise.
        """
        return self._running

    async def _detect_window(self) -> None:
        """Attempt to detect the game window with retries.

        Raises:
            WindowError: If the window is not found within the configured timeout or if shutdown is requested.
        """
        window_title = self._config.get_value("core", "window.title")
        timeout = self._config.get_value("core", "window.detection_timeout", 30.0)
        interval = self._config.get_value("core", "window.detection_interval", 1.0)

        start_time = asyncio.get_event_loop().time()
        try:
            while not self._shutdown_requested:
                if self._window.find_window():
                    self._logger.info(f"Found {window_title} window")
                    return

                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    executable = self._config.get_value("core", "window.executable")
                    self._logger.error(f"Failed to find {window_title} window after {timeout} seconds")
                    raise WindowError(window_title, executable)

                self._logger.debug(f"Waiting for {window_title} window...")
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            self._logger.info("Window detection cancelled due to shutdown request")
            self._shutdown_requested = True
            raise

    @property
    def window(self) -> GameWindow:
        """Get the game window instance.

        Returns:
            GameWindow: The game window instance.
        """
        return self._window
