"""Base module implementation for POE Sidekick."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from rx.core.observable.observable import Observable
from rx.subject.subject import Subject


@dataclass
class ModuleConfig:
    """Configuration for a module instance.

    Args:
        name: Unique name for the module instance
        enabled: Whether the module is enabled by default
    """

    name: str
    enabled: bool = True


class BaseModule(ABC):
    """Base class for POE Sidekick modules.

    Modules are the core building blocks of functionality in POE Sidekick.
    Each module:
    1. Processes screenshot frames from the game
    2. Maintains its own state
    3. Can be activated/deactivated
    4. Has access to shared services
    5. Can emit frame analysis results
    """

    def __init__(self, config: ModuleConfig, services: dict[str, Any]) -> None:
        """Initialize a new module instance.

        Args:
            config: Module configuration
            services: Dictionary of service instances
        """
        self.name = config.name
        self.services = services
        self.enabled = config.enabled
        self.active = False
        self._state: dict[str, Any] = {}
        self.logger = logging.getLogger(f"module.{self.name}")
        self._frame_subject = Subject()  # Type inference through usage

    @property
    def state(self) -> dict[str, Any]:
        """Get module state.

        Returns:
            A copy of the current state dictionary
        """
        return self._state.copy()

    async def activate(self) -> None:
        """Activate the module.

        This will:
        1. Call module-specific activation code
        2. Enable frame processing
        3. Mark the module as active

        Raises:
            Exception: If activation fails
        """
        if not self.enabled:
            self.logger.info(f"Module {self.name} is disabled, skipping activation")
            return
        try:
            await self._on_activate()
            self.active = True
            self.logger.info(f"Module {self.name} activated")
        except Exception:
            self.logger.exception(f"Failed to activate module {self.name}")
            raise

    async def deactivate(self) -> None:
        """Deactivate the module.

        This will:
        1. Call module-specific deactivation code
        2. Disable frame processing
        3. Mark the module as inactive

        Raises:
            Exception: If deactivation fails
        """
        try:
            await self._on_deactivate()
            self.active = False
            self.logger.info(f"Module {self.name} deactivated")
        except Exception:
            self.logger.exception(f"Failed to deactivate module {self.name}")
            raise

    async def process_frame(self, frame: NDArray[np.uint8]) -> None:
        """Process a new screenshot frame.

        This method:
        1. Checks if module is active
        2. Emits frame to subscribers
        3. Calls module-specific frame processing
        4. Handles any errors

        Args:
            frame: Screenshot frame as numpy array
        """
        if not self.active:
            return

        try:
            self._frame_subject.on_next(frame)
            await self._process_frame(frame)
        except Exception:
            self.logger.exception(f"Error processing frame in module {self.name}")

    def subscribe_to_frames(self, observer: Callable[[NDArray[np.uint8]], Any]) -> Observable:
        """Subscribe to frame processing results.

        Args:
            observer: Observer to receive frame results

        Returns:
            Subscription object
        """
        return cast(Observable, self._frame_subject.subscribe(observer))

    @abstractmethod
    async def _process_frame(self, frame: NDArray[np.uint8]) -> None:
        """Process a screenshot frame.

        This method should be implemented by subclasses to define
        module-specific frame processing logic.

        Args:
            frame: Screenshot frame as numpy array
        """
        raise NotImplementedError

    @abstractmethod
    async def _on_activate(self) -> None:
        """Called when the module is activated.

        Override to perform module-specific activation tasks.
        """
        pass

    @abstractmethod
    async def _on_deactivate(self) -> None:
        """Called when the module is deactivated.

        Override to perform module-specific cleanup tasks.
        """
        pass

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update module state.

        Args:
            updates: Dictionary of state updates
        """
        self._state.update(updates)
