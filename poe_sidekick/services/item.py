"""Item service implementation for managing item metadata and templates."""

import json
from pathlib import Path
from typing import Any, TypedDict, cast

from poe_sidekick.services.config import ConfigService

class TemplateConfig(TypedDict):
    """Type definition for template configuration."""

    path: str
    detection_threshold: float

class TemplateService:
    """Service for managing item templates."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize service with configuration.

        Args:
            config_service: Service for accessing configuration values
        """
        self._config = config_service
        self._metadata_path = Path(__file__).parent.parent / "data" / "item_metadata.json"

    async def load_metadata(self) -> dict[str, Any]:
        """Load item metadata from file.

        Returns:
            Item metadata dictionary

        Raises:
            FileNotFoundError: If metadata file is not found
            ValueError: If metadata file is invalid
        """
        try:
            with open(self._metadata_path, "r") as f:
                metadata = json.load(f)
            return cast(dict[str, Any], metadata)
        except FileNotFoundError:
            raise FileNotFoundError(f"Item metadata file not found: {self._metadata_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid item metadata format in: {self._metadata_path}")
