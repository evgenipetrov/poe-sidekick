"""Loot manager module implementation."""

import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

from ...core.module import BaseModule, ModuleConfig


class LootModule(BaseModule):
    """Module for detecting and managing loot items.

    This module handles:
    1. Item detection in screenshot frames
    2. Item filtering based on configuration
    3. Automated item pickup (when enabled)
    """

    def __init__(self, services: dict[str, Any]):
        """Initialize loot manager module.

        Args:
            services: Dictionary of service instances including:
                     - vision_service: For item detection
                     - input_service: For item pickup
        """
        # Load module configuration
        config_path = Path(__file__).parent.parent.parent / "config" / "loot_module.json"
        with open(config_path) as f:
            module_config = json.load(f)

        config = ModuleConfig(name="loot_module", enabled=module_config["activation"]["enabled_by_default"])
        super().__init__(config, services)

        # Get required services
        self.vision_service = services["vision_service"]
        self.template_service = services["template_service"]

        # Store configuration sections
        self._filters = module_config["filters"]
        self._behavior = module_config["behavior"]
        self._ui = module_config["ui"]

        # Initialize state
        self._detected_items: list[dict[str, Any]] = []
        self._ground_templates: dict[str, dict] = {}
        self._last_frame: Optional[np.ndarray] = None
        self.update_state({"frame_shape": None, "detected_items": self._detected_items})

    def _process_frame(self, frame: np.ndarray) -> None:
        """Process a screenshot frame to detect and filter items.

        Args:
            frame: Screenshot frame as numpy array
        """
        self._last_frame = frame

        # TODO: Implement item detection using vision service
        # For now, just update state with frame info
        self.update_state({
            "frame_shape": frame.shape if frame is not None else None,
            "detected_items": self._detected_items,
        })

    def _load_ground_templates(self) -> None:
        """Load ground label templates from metadata."""
        try:
            metadata = self.template_service.load_metadata()
            self._ground_templates = {}

            # Load templates from each category
            for _category, templates in metadata["templates"].items():
                # Skip template_format entries
                if "template_format" in templates:
                    continue

                for name, template in templates.items():
                    if "ground_label" in template:
                        self._ground_templates[name] = template

            self.logger.info(f"Loaded {len(self._ground_templates)} ground label templates")

        except Exception:
            self.logger.exception("Failed to load ground label templates")
            raise

    async def _on_activate(self) -> None:
        """Activation handler that initializes item tracking."""
        try:
            # Load ground label templates
            self._load_ground_templates()

            # Reset state
            self._detected_items = []
            self._last_frame = None
            self.update_state({"frame_shape": None, "detected_items": self._detected_items})
            self.logger.info("Loot module activated")

        except Exception:
            self.logger.exception("Failed to activate loot module")
            raise

    async def _on_deactivate(self) -> None:
        """Deactivation handler that cleans up state."""
        self._detected_items = []
        self._last_frame = None
        self._ground_templates = {}
        self.logger.info("Loot module deactivated")
