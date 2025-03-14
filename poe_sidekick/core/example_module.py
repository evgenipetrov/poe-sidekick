"""Example module implementation to validate BaseModule functionality."""

from typing import Any, Optional

import numpy as np

from .module import BaseModule, ModuleConfig


class ExampleModule(BaseModule):
    """Example module that implements BaseModule.

    This module serves as:
    1. A validation of BaseModule functionality
    2. An example implementation for future modules
    3. A test harness for module system integration
    """

    def __init__(self, services: dict[str, Any]):
        """Initialize example module.

        Args:
            services: Dictionary of service instances
        """
        config = ModuleConfig(name="example_module")
        super().__init__(config, services)
        self._frame_count = 0
        self._last_frame: Optional[np.ndarray] = None

    def _process_frame(self, frame: np.ndarray) -> None:
        """Process a screenshot frame.

        For example purposes, this just counts frames and stores the last one.

        Args:
            frame: Screenshot frame as numpy array
        """
        self._frame_count += 1
        self._last_frame = frame

        # Update module state
        self.update_state({
            "frame_count": self._frame_count,
            "last_frame_shape": frame.shape if frame is not None else None,
        })

    def _on_activate(self) -> None:
        """Activation handler that resets frame counter."""
        self._frame_count = 0
        self._last_frame = None
        self.update_state({"frame_count": self._frame_count, "last_frame_shape": None})
        self.logger.info("Example module activated - frame counter reset")

    def _on_deactivate(self) -> None:
        """Deactivation handler that logs final frame count."""
        self.logger.info(f"Example module deactivated - processed {self._frame_count} frames")
