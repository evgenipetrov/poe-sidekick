"""Loot manager module implementation."""

import json
import time
from pathlib import Path
from typing import Any, Optional, TypedDict

import cv2
import numpy as np
from numpy.typing import NDArray

from ...core.module import BaseModule, ModuleConfig


class ItemInfo(TypedDict):
    """Type definition for item detection information."""

    name: str
    location: tuple[int, int]
    confidence: float
    timestamp: float


class GroundLabelConfig(TypedDict):
    """Type definition for ground label configuration."""

    path: str
    color_range: dict[str, list[int]]
    detection_threshold: float


class TemplateData(TypedDict):
    """Type definition for template data."""

    ground_label: GroundLabelConfig


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

        config = ModuleConfig(name="loot_module", enabled=True)  # Always enabled by default
        super().__init__(config, services)

        # Get required services
        self.vision_service = services["vision_service"]
        self.item_service = services["item_service"]
        self.input_service = services["input_service"]
        self.stream = services["stream"]  # Screenshot stream for region info

        # Store configuration sections
        self._filters = module_config["filters"]
        self._behavior = module_config["behavior"]

        # Initialize state and tracking
        self._detected_items: list[ItemInfo] = []
        self._ground_templates: dict[str, TemplateData] = {}
        self._last_frame: Optional[NDArray[np.uint8]] = None
        self.update_state({"frame_shape": None, "detected_items": self._detected_items})

    async def _process_frame(self, frame: NDArray[np.uint8]) -> None:
        """Process a screenshot frame to detect and filter items.

        Args:
            frame: Screenshot frame as numpy array
        """
        self.logger.debug(f"Processing frame with shape: {frame.shape if frame is not None else 'None'}")

        if frame is None:
            return

        self._last_frame = frame
        self._detected_items.clear()

        if not self._ground_templates:
            self.logger.debug("No ground templates loaded, skipping frame processing")
            return

        # Perform template matching for each ground label
        for item_name, template_data in self._ground_templates.items():
            try:
                # Convert relative path to absolute using project root
                relative_path = template_data["ground_label"]["path"]
                project_root = Path(__file__).parent.parent.parent.parent
                template_path = project_root / relative_path

                self.logger.debug(f"Looking for template at: {template_path}")
                if not template_path.exists():
                    self.logger.warning(f"Template file not found: {template_path}")
                    continue

                # Load template image
                template = cv2.imread(str(template_path))
                if template is None:
                    self.logger.warning(f"Failed to load template: {template_path}")
                    continue

                template_array = np.asarray(template, dtype=np.uint8)
                self.logger.debug(f"Successfully loaded template: {template_path} with shape {template_array.shape}")

                # Save debug images if needed
                screenshots_dir = Path("data/screenshots")
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time() * 1000)

                # Save original frame and template
                cv2.imwrite(str(screenshots_dir / f"frame_{timestamp}.png"), frame)
                cv2.imwrite(str(screenshots_dir / f"template_{timestamp}.png"), template_array)

                # Simple template matching on raw images
                threshold = self._behavior["detection_threshold"]
                threshold = self._behavior["detection_threshold"]
                self.logger.debug(f"Attempting template match for {item_name} with threshold {threshold}")
                self.logger.debug(f"Template shape: {template_array.shape}, Frame shape: {frame.shape}")

                match = await self.vision_service.find_template(template_array, frame, threshold=threshold)

                if match:
                    # Draw match location on frame for debugging
                    debug_frame = frame.copy()
                    h, w = template_array.shape[:2]
                    x, y = match.location
                    cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(debug_frame, match.location, 5, (0, 0, 255), -1)
                    cv2.putText(
                        debug_frame,
                        f"{match.confidence:.2f}",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )
                    cv2.imwrite(str(screenshots_dir / f"match_{timestamp}.png"), debug_frame)

                    # Add detected item
                    item_info: ItemInfo = {
                        "name": item_name,
                        "location": match.location,
                        "confidence": match.confidence,
                        "timestamp": time.time(),
                    }
                    self._detected_items.append(item_info)
                    self.logger.info(
                        f"Detected item: {item_name} at {match.location} with confidence {match.confidence:.2f}"
                    )

                    # Try to pick up item if auto-pickup is enabled
                    if self._behavior["auto_pickup"]:
                        await self._pickup_item(item_info)

                    # Try to pick up item if auto-pickup is enabled
                    if self._behavior["auto_pickup"]:
                        await self._pickup_item(item_info)

            except Exception:
                self.logger.exception(f"Error processing template {item_name}")

        # Update state with current frame info and detections
        self.update_state({
            "frame_shape": frame.shape,
            "detected_items": self._detected_items,
        })

    async def _pickup_item(self, item_info: ItemInfo) -> None:
        """Attempt to pick up a detected item.

        Args:
            item_info: Dictionary containing item detection information
        """
        try:
            # Get item location and convert to screen coordinates
            frame_x, frame_y = item_info["location"]

            # Get capture region from stream
            region = self.stream._camera.region if self.stream._camera else None
            if not region:
                self.logger.error("No capture region available")
                return

            # Convert frame coordinates to screen coordinates
            screen_x = frame_x + region[0]  # Add left offset
            screen_y = frame_y + region[1]  # Add top offset

            self.logger.debug(
                f"Converting coordinates for {item_info['name']}: "
                f"frame({frame_x}, {frame_y}) -> screen({screen_x}, {screen_y})"
            )

            # Add small random offset for natural clicks
            offset_x = np.random.randint(-3, 4)
            offset_y = np.random.randint(-3, 4)
            click_x = screen_x + offset_x
            click_y = screen_y + offset_y

            # Move cursor and click
            self.input_service.move_cursor_to(click_x, click_y)
            time.sleep(self._behavior["min_delay_seconds"])
            self.input_service.click_left()

            self.logger.info(f"Attempted to pick up {item_info['name']} at ({click_x}, {click_y})")

        except Exception:
            self.logger.exception(f"Error attempting to pick up item: {item_info['name']}")

    async def _load_ground_templates(self) -> None:
        """Load ground label templates from metadata."""
        try:
            metadata = await self.item_service.load_metadata()
            self.logger.debug(f"Loaded metadata: {metadata}")
            self._ground_templates = {}

            # Load templates from each category
            for category, templates in metadata["templates"].items():
                self.logger.debug(f"Processing category: {category} with keys: {list(templates.keys())}")

                # Process each template in the category
                for name, template in templates.items():
                    if name == "template_format":
                        self.logger.debug("Skipping template_format entry")
                        continue

                    self.logger.debug(f"Processing template: {name} with keys: {list(template.keys())}")
                    if "ground_label" in template:
                        self._ground_templates[name] = template
                        self.logger.debug(f"Added ground label template: {name}")
                    else:
                        self.logger.debug(f"Template {name} has no ground_label")

            self.logger.info(f"Loaded {len(self._ground_templates)} ground label templates")
            if len(self._ground_templates) == 0:
                self.logger.warning("No ground label templates were loaded!")

        except Exception:
            self.logger.exception("Failed to load ground label templates")
            raise

    async def _on_activate(self) -> None:
        """Activation handler that initializes item tracking."""
        try:
            # Load ground label templates
            await self._load_ground_templates()

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

    async def cleanup(self) -> None:
        """Clean up resources and deactivate module."""
        if self.active:
            await self.deactivate()
