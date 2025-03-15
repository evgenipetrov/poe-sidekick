"""Item service implementation for managing item metadata and templates."""

import json
from pathlib import Path
from typing import Any, TypedDict, cast

from poe_sidekick.services.config import ConfigService


class ItemMetadataError(Exception):
    """Base exception for item metadata errors."""


class MetadataNotFoundError(ItemMetadataError):
    """Raised when item metadata file cannot be found."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Item metadata file not found: {path}")


class InvalidMetadataError(ItemMetadataError):
    """Raised when item metadata file has invalid format."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Invalid item metadata format in: {path}")


class TemplateConfig(TypedDict):
    """Type definition for template configuration."""

    path: str
    detection_threshold: float


class ItemService:
    """Service for managing item metadata and state."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize service with configuration.

        Args:
            config_service: Service for accessing configuration values
        """
        self._config = config_service
        self._metadata_path = Path(__file__).parent.parent.parent / "data" / "items" / "metadata.json"

    async def load_metadata(self) -> dict[str, Any]:
        """Load item metadata from file.

        Returns:
            Item metadata dictionary containing templates and configurations

        Raises:
            MetadataNotFoundError: If metadata file is not found
            InvalidMetadataError: If metadata file has invalid format
        """
        try:
            with open(self._metadata_path) as f:
                metadata = json.load(f)
            return cast(dict[str, Any], metadata)
        except FileNotFoundError as err:
            raise MetadataNotFoundError(self._metadata_path) from err
        except json.JSONDecodeError as err:
            raise InvalidMetadataError(self._metadata_path) from err


class TemplateService:
    """Service for managing item templates."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize service with configuration.

        Args:
            config_service: Service for accessing configuration values
        """
        self._config = config_service
        self._metadata_path = Path(__file__).parent.parent.parent / "data" / "items" / "metadata.json"

    async def load_metadata(self) -> dict[str, Any]:
        """Load item metadata from file.

        Returns:
            Item metadata dictionary

        Raises:
            FileNotFoundError: If metadata file is not found
            ValueError: If metadata file is invalid
        """
        try:
            with open(self._metadata_path) as f:
                metadata = json.load(f)
            return cast(dict[str, Any], metadata)
        except FileNotFoundError as err:
            raise MetadataNotFoundError(self._metadata_path) from err
        except json.JSONDecodeError as err:
            raise InvalidMetadataError(self._metadata_path) from err
