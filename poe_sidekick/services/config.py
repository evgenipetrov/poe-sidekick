import json
import os
from typing import Any


class ConfigService:
    """Service for managing configuration values across the application."""

    def __init__(self, config_dir: str | None = None):
        """Initialize the config service.

        Args:
            config_dir: Optional path to config directory. If not provided,
                       defaults to 'config' in the same directory as the service.
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
        self._config_dir = os.path.normpath(config_dir)
        self._configs: dict[str, dict[str, Any]] = {}

    async def load_config(self, name: str, custom_path: str | None = None) -> dict[str, Any]:
        """Load and cache a configuration file.

        Args:
            name: Name of the config file without .json extension (e.g. 'core')
            custom_path: Optional full path to config file, overrides config_dir

        Returns:
            Dict containing the configuration values

        Raises:
            FileNotFoundError: If config file doesn't exist
            JSONDecodeError: If config file contains invalid JSON
        """
        if name not in self._configs:
            path = custom_path if custom_path else os.path.join(self._config_dir, f"{name}.json")
            with open(path) as f:
                self._configs[name] = json.load(f)
        return self._configs[name]

    def get_value(self, config: str, path: str, default: Any = None) -> Any:
        """Get a value from a config using dot notation path.

        Args:
            config: Name of the config file without .json extension
            path: Dot notation path to the value (e.g. 'window.title')
            default: Value to return if path doesn't exist

        Returns:
            The value at the specified path, or default if not found

        Example:
            >>> config_service.get_value("core", "window.title")
            'Path of Exile 2'
        """
        try:
            config_dict = self._configs[config]
        except KeyError:
            return default

        parts = path.split(".")
        value = config_dict

        for part in parts:
            try:
                value = value[part]
            except (KeyError, TypeError):
                return default

        return value

    def reload(self, name: str) -> None:
        """Force reload a configuration from disk.

        Args:
            name: Name of the config file without .json extension
        """
        if name in self._configs:
            del self._configs[name]
