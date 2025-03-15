"""Engine module for POE Sidekick.

This module provides the central Engine class that manages the application lifecycle,
including window management, screenshot stream, modules, and workflows.
"""

import argparse
import asyncio
import logging
from typing import TYPE_CHECKING, Any, NoReturn, Protocol, TypedDict, cast

from poe_sidekick.core.stream import ScreenshotStream
from poe_sidekick.core.window import GameWindow
from poe_sidekick.plugins.loot_manager.module import LootModule
from poe_sidekick.services.config import ConfigService
from poe_sidekick.services.input import InputConfig, InputService
from poe_sidekick.services.item import ItemService, TemplateService  # Added ItemService
from poe_sidekick.services.vision import VisionService

if TYPE_CHECKING:
    from poe_sidekick.workflows.loot import LootWorkflow


class Module(Protocol):
    """Protocol defining required module interface."""

    async def cleanup(self) -> None: ...
    async def process_frame(self, frame: Any) -> None: ...


class WorkflowConfig(TypedDict):
    """Type definition for workflow configuration."""

    modules: list[str]


class FrameProcessor(Protocol):
    """Protocol defining frame processing interface."""

    async def __call__(self, frame: Any) -> None: ...


def raise_window_region_error() -> NoReturn:
    """Raise WindowRegionError."""
    raise WindowRegionError()


def raise_workflow_config_error(workflow_name: str) -> NoReturn:
    """Raise WorkflowConfigError."""
    raise WorkflowConfigError(workflow_name)


def raise_required_module_error(module_name: str) -> NoReturn:
    """Raise RequiredModuleError."""
    raise RequiredModuleError(module_name)


def raise_unknown_workflow_error(workflow_name: str) -> NoReturn:
    """Raise UnknownWorkflowError."""
    raise UnknownWorkflowError(workflow_name)


def raise_workflow_import_error(workflow_name: str, error: str) -> NoReturn:
    """Raise WorkflowImportError."""
    raise WorkflowImportError(workflow_name, error)


def raise_stream_initialization_error() -> NoReturn:
    """Raise StreamInitializationError."""
    raise StreamInitializationError()


class EngineError(RuntimeError):
    """Base exception class for engine-related errors."""


class StreamInitializationError(EngineError):
    """Exception raised when screenshot stream initialization fails."""

    def __init__(self) -> None:
        super().__init__("Screenshot stream initialization failed")


class WindowError(EngineError):
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


class WindowRegionError(EngineError):
    """Exception raised when unable to get window region."""

    def __init__(self) -> None:
        super().__init__("Failed to get window region")


class WorkflowConfigError(EngineError):
    """Exception raised for workflow configuration errors."""

    def __init__(self, workflow_name: str) -> None:
        super().__init__(f"No configuration found for workflow: {workflow_name}")


class RequiredModuleError(EngineError):
    """Exception raised when a required module is not found."""

    def __init__(self, module_name: str) -> None:
        super().__init__(f"Required module not found: {module_name}")


class UnknownWorkflowError(EngineError):
    """Exception raised when workflow type is unknown."""

    def __init__(self, workflow_name: str) -> None:
        super().__init__(f"Unknown workflow: {workflow_name}")


class WorkflowImportError(EngineError):
    """Exception raised when workflow import fails."""

    def __init__(self, workflow_name: str, error: str) -> None:
        super().__init__(f"Failed to import workflow {workflow_name}: {error}")


class Engine:
    """Central engine class managing POE Sidekick's core functionality."""

    def __init__(self) -> None:
        """Initialize the Engine instance."""
        self._config = ConfigService()
        self._window = GameWindow()
        self._screenshot_stream: ScreenshotStream | None = None
        self._modules: dict[str, Module] = {}
        self._running: bool = False
        self._shutdown_requested: bool = False
        self._logger = logging.getLogger(__name__)
        self._workflow: Any | None = None  # Type will be refined when workflow system is typed
        self._frame_tasks: list[asyncio.Task[None]] = []

        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("--workflow", type=str, help="Name of workflow to run")
        args, _ = parser.parse_known_args()
        self._workflow_name = args.workflow

    async def start(self) -> None:
        """Start the POE Sidekick engine.

        Raises:
            RuntimeError: If the Path of Exile 2 window cannot be found.
        """
        self._logger.info("Starting POE Sidekick engine...")

        # Load core configuration and workflows
        await self._config.load_config("core")
        await self._config.load_config("workflows")
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

        # Cancel any pending frame tasks
        for task in self._frame_tasks:
            if not task.done():
                task.cancel()

        # Get timeout from config or use default
        timeout = self._config.get_value("core", "engine.shutdown_timeout", 5.0)
        await self._cleanup_components(timeout)
        self._logger.info("POE Sidekick engine stopped")

    async def _initialize_components(self) -> None:
        """Initialize screenshot stream, modules, and other components."""
        try:
            # Initialize screenshot stream
            self._screenshot_stream = ScreenshotStream(self._config)
            window_rect = self._window.get_window_rect()
            if not window_rect:
                self._logger.error("Failed to get window region")
                raise_window_region_error()
                return

            self._logger.info(f"Starting screenshot stream with window region: {window_rect}")
            await self._screenshot_stream.start(region=window_rect)

            # Initialize core services
            if not self._screenshot_stream:
                raise_stream_initialization_error()

            vision_service = VisionService(self._screenshot_stream)
            template_service = TemplateService(self._config)
            item_service = ItemService(self._config)  # Initialize ItemService

            # Load input config
            input_config = self._config.get_value("core", "input")
            input_service = InputService(
                InputConfig(
                    min_delay_seconds=input_config.get("min_delay_seconds", 0.1),
                    cursor_speed=input_config.get("cursor_speed", 1.0),
                    key_press_duration=input_config.get("key_press_duration", 0.1),
                )
            )

            # Create service dictionary
            services: dict[str, Any] = {
                "vision_service": vision_service,
                "input_service": input_service,
                "template_service": template_service,
                "item_service": item_service,  # Add ItemService to services
                "stream": self._screenshot_stream,
            }

            # Initialize base modules
            self._modules["loot_module"] = LootModule(services)

            # Subscribe modules to screenshot stream
            async def process_frame(frame: Any) -> None:
                if "loot_module" in self._modules:
                    await self._modules["loot_module"].process_frame(frame)

            # Convert the async function to a sync callback and store task references
            def frame_callback(frame: Any) -> None:
                task = asyncio.create_task(process_frame(frame))
                self._frame_tasks.append(task)
                task.add_done_callback(self._frame_tasks.remove)

            self._screenshot_stream.observable.subscribe(frame_callback)

            # Start workflow if specified
            if self._workflow_name:
                await self._start_workflow(self._workflow_name)

        except Exception:
            self._logger.exception("Failed to initialize components")
            await self.stop()
            raise

    async def _cleanup_components(self, timeout: float) -> None:
        """Cleanup all components properly."""
        try:
            cleanup_tasks: list[asyncio.Task[None]] = []

            # Clean up workflow if running
            if self._workflow is not None:
                cleanup_tasks.append(asyncio.create_task(self._workflow.deactivate_modules()))

            # Clean up modules
            for module in self._modules.values():
                cleanup_tasks.append(asyncio.create_task(module.cleanup()))

            # Clean up screenshot stream
            if self._screenshot_stream is not None:
                cleanup_tasks.append(asyncio.create_task(self._screenshot_stream.stop()))

            # Wait for all cleanup tasks with timeout
            if cleanup_tasks:  # Only wait if there are tasks
                await asyncio.wait_for(asyncio.gather(*cleanup_tasks), timeout=timeout)

        except TimeoutError:
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
            WindowError: If shutdown is requested before finding the window or if detection fails.
        """
        window_title = self._config.get_value("core", "window.title")
        executable = self._config.get_value("core", "window.executable")
        interval = self._config.get_value("core", "window.detection_interval", 1.0)
        timeout = self._config.get_value("core", "window.detection_timeout", 30.0)
        attempts = int(timeout / interval)

        try:
            for _ in range(attempts):
                if self._shutdown_requested:
                    break

                try:
                    if self._window.find_window():
                        self._logger.info(f"Found {window_title} window")
                        return
                except Exception as e:
                    self._logger.debug(f"Error during window detection: {e}")

                self._logger.debug(f"Waiting for {window_title} window...")
                await asyncio.sleep(interval)

            if not self._shutdown_requested:
                raise WindowError(window_title, executable)

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

    def _validate_workflow_config(self, workflow_name: str, workflow_config: WorkflowConfig | None) -> None:
        """Validate workflow configuration.

        Args:
            workflow_name: Name of the workflow
            workflow_config: Workflow configuration dictionary

        Raises:
            WorkflowConfigError: If workflow configuration is missing or invalid
        """
        if not workflow_config:
            raise_workflow_config_error(workflow_name)

    def _validate_required_modules(self, workflow_config: WorkflowConfig) -> list[Module]:
        """Validate and collect required modules.

        Args:
            workflow_config: Workflow configuration dictionary

        Returns:
            List of required modules

        Raises:
            RequiredModuleError: If a required module is not found
        """
        workflow_modules = []
        for module_name in workflow_config["modules"]:
            if module_name not in self._modules:
                raise_required_module_error(module_name)
            workflow_modules.append(self._modules[module_name])
        return workflow_modules

    def _get_workflow_class(self, workflow_name: str) -> type["LootWorkflow"]:
        """Get workflow class based on workflow name.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Workflow class

        Raises:
            UnknownWorkflowError: If workflow type is not recognized
            WorkflowImportError: If workflow module import fails
        """
        try:
            from poe_sidekick.workflows import LootWorkflow

            if workflow_name == "loot":
                return LootWorkflow
            raise_unknown_workflow_error(workflow_name)  # NoReturn, so no need for else
        except ImportError as e:
            raise_workflow_import_error(workflow_name, str(e))

    async def _start_workflow(self, workflow_name: str) -> None:
        """Start a workflow by name.

        Args:
            workflow_name: The name of the workflow to start
        """
        try:
            # Load and validate workflow configuration
            workflow_config = self._config.get_value("workflows", workflow_name)
            if not workflow_config:
                raise_workflow_config_error(workflow_name)

            # Get required modules
            workflow_modules = self._validate_required_modules(workflow_config)

            # Get workflow class and create instance
            workflow_class = self._get_workflow_class(workflow_name)
            # Cast first module to LootModule since we know it's the only required module
            loot_module = cast(LootModule, workflow_modules[0])
            self._workflow = workflow_class(loot_module)

            # Start workflow
            self._logger.info(f"Starting workflow: {workflow_name}")
            await self._workflow.execute()

        except Exception:
            self._logger.exception(f"Failed to start workflow: {workflow_name}")
            await self.stop()
            raise
