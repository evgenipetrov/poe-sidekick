"""Engine module for POE Sidekick.

This module provides the central Engine class that manages the application lifecycle,
including window management, screenshot stream, modules, and workflows.
"""

import logging
from typing import Protocol

from poe_sidekick.core.window import GameWindow
from poe_sidekick.services.config import ConfigService


class WindowError(RuntimeError):
    """Exception raised for window-related errors."""

    def __init__(self, window_title: str) -> None:
        super().__init__(f"{window_title} window not found")


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
        self._logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the POE Sidekick engine.

        Raises:
            RuntimeError: If the Path of Exile 2 window cannot be found.
        """
        self._logger.info("Starting POE Sidekick engine...")

        # Load core configuration
        await self._config.load_config("core")
        window_title = self._config.get_value("core", "window.title")

        if not self._window.find_window():
            raise WindowError(window_title)

        self._running = True
        self._window.bring_to_front()
        await self._initialize_components()
        self._logger.info("POE Sidekick engine started successfully")

    async def stop(self) -> None:
        """Stop the engine and cleanup resources."""
        self._logger.info("Stopping POE Sidekick engine...")
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
        # Clean up modules
        for module in self._modules.values():
            try:
                await module.cleanup()
            except Exception:
                self._logger.exception("Error cleaning up module")

        # Clean up screenshot stream
        if self._screenshot_stream is not None:
            try:
                await self._screenshot_stream.cleanup()
            except Exception:
                self._logger.exception("Error cleaning up screenshot stream")

        self._modules.clear()
        self._screenshot_stream = None

    @property
    def is_running(self) -> bool:
        """Check if the engine is currently running.

        Returns:
            bool: True if the engine is running, False otherwise.
        """
        return self._running

    @property
    def window(self) -> GameWindow:
        """Get the game window instance.

        Returns:
            GameWindow: The game window instance.
        """
        return self._window
