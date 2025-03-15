"""Template service for managing template metadata and configuration."""

import json
from pathlib import Path
from typing import Any, Optional, cast

from poe_sidekick.services.config import ConfigService


class TemplateError(Exception):
    """Base exception for template-related errors."""


class TemplateNotFoundError(TemplateError):
    """Raised when a template cannot be found."""

    def __init__(self) -> None:
        super().__init__("Template not found")


class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""

    def __init__(self, field: str) -> None:
        super().__init__(f"Missing required fields in {field}")


class MetadataError(TemplateError):
    """Raised when metadata is not loaded or invalid."""

    def __init__(self) -> None:
        super().__init__("Template metadata not loaded")


class MetadataNotFoundError(TemplateError):
    """Raised when metadata file cannot be found."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Template metadata not found at {path}")


class FileValidationError(TypeError):
    """Raised when a file has an invalid type."""

    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must be a dictionary")


class RangeValidationError(TypeError):
    """Raised when a range value is invalid."""

    def __init__(self) -> None:
        super().__init__("Range must be a list of two values")


class ThresholdValidationError(TypeError):
    """Raised when a threshold value is invalid."""

    def __init__(self) -> None:
        super().__init__("Threshold must be a number")


class TemplateService:
    """Service for managing template metadata and configuration."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize the template service.

        Args:
            config_service: Config service for accessing paths
        """
        self.config_service = config_service
        self._metadata: Optional[dict] = None

    async def load_metadata(self) -> dict[str, Any]:
        """Load and validate the template metadata.

        Returns:
            Dict containing the validated template metadata

        Raises:
            FileNotFoundError: If metadata.json doesn't exist
            TemplateValidationError: If metadata validation fails
        """
        if self._metadata is not None:
            return self._metadata

        # Use project root path
        project_root = Path(__file__).parent.parent.parent
        metadata_path = project_root / "data" / "templates" / "metadata.json"
        if not metadata_path.exists():
            raise MetadataNotFoundError(metadata_path)

        metadata = await self.config_service.load_config("templates", str(metadata_path))
        print(f"DEBUG - Raw metadata loaded: {json.dumps(metadata, indent=2)}")  # Temporary debug print
        await self.validate_metadata(metadata)
        self._metadata = metadata
        return metadata

    def _validate_base_metadata(self, metadata: dict) -> None:
        """Validate the base metadata structure."""
        required_fields = ["version", "templates"]
        if not all(field in metadata for field in required_fields):
            raise TemplateValidationError("metadata")

        if not isinstance(metadata["templates"], dict):
            raise FileValidationError("templates")

    def _validate_template_data(self, template: dict, name: str) -> None:
        """Validate individual template data."""
        if not isinstance(template, dict):
            raise FileValidationError("template")

        required_template_fields = ["name", "category"]
        if not all(field in template for field in required_template_fields):
            raise TemplateValidationError("template")

        if "ground_label" in template:
            self._validate_ground_label(template["ground_label"], name)

        if "item_appearance" in template:
            self._validate_item_appearance(template["item_appearance"], name)

    async def validate_metadata(self, metadata: dict) -> None:
        """Validate the template metadata structure.

        Args:
            metadata: Template metadata to validate

        Raises:
            TemplateValidationError: If metadata validation fails
        """
        self._validate_base_metadata(metadata)

        for _category, templates in metadata["templates"].items():
            if not isinstance(templates, dict):
                raise FileValidationError("templates")

            # Skip validation for template_format entries
            if "template_format" in templates:
                continue

            for name, template in templates.items():
                self._validate_template_data(template, name)

    def _validate_ground_label(self, ground_label: dict, template_name: str) -> None:
        """Validate ground label configuration.

        Args:
            ground_label: Ground label configuration to validate
            template_name: Name of the template being validated

        Raises:
            TemplateValidationError: If validation fails
        """
        required_fields = ["path", "color_range", "detection_threshold"]
        if not all(field in ground_label for field in required_fields):
            raise TemplateValidationError("ground_label")

        color_range = ground_label["color_range"]
        required_color_fields = ["hue", "saturation", "value"]
        if not all(field in color_range for field in required_color_fields):
            raise TemplateValidationError("color_range")

        for field in required_color_fields:
            if not isinstance(color_range[field], list) or len(color_range[field]) != 2:
                raise RangeValidationError()

        if not isinstance(ground_label["detection_threshold"], (int, float)):
            raise ThresholdValidationError()

    def _validate_item_appearance(self, item_appearance: dict, template_name: str) -> None:
        """Validate item appearance configuration.

        Args:
            item_appearance: Item appearance configuration to validate
            template_name: Name of the template being validated

        Raises:
            TemplateValidationError: If validation fails
        """
        required_fields = ["path", "detection_threshold", "grid_size"]
        if not all(field in item_appearance for field in required_fields):
            raise TemplateValidationError("item_appearance")

        if not isinstance(item_appearance["detection_threshold"], (int, float)):
            raise ThresholdValidationError()

        grid_size = item_appearance["grid_size"]
        if not isinstance(grid_size, list) or len(grid_size) != 2:
            raise RangeValidationError()

    async def get_template_config(self, name: str) -> dict[str, Any]:
        """Get configuration for a specific template.

        Args:
            name: Name of the template to get

        Returns:
            Template configuration dictionary

        Raises:
            TemplateNotFoundError: If template not found
            MetadataError: If metadata not loaded
        """
        if self._metadata is None:
            raise MetadataError()

        # Search through all categories
        for category in self._metadata["templates"].values():
            if name in category:
                return cast(dict[str, Any], category[name])

        raise TemplateNotFoundError()
