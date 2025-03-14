import json
import os

import pytest

from poe_sidekick.services.config import ConfigService


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create test config files
    core_config = {"window": {"title": "Test Window", "executable": "test.exe"}}

    with open(config_dir / "core.json", "w") as f:
        json.dump(core_config, f)

    return config_dir


@pytest.fixture
def config_service(temp_config_dir):
    """Create a ConfigService instance with test config directory."""
    return ConfigService(str(temp_config_dir))


async def test_load_config(config_service: ConfigService):
    """Test loading a configuration file."""
    config = await config_service.load_config("core")
    assert isinstance(config, dict)
    assert "window" in config
    assert config["window"]["title"] == "Test Window"


async def test_load_nonexistent_config(config_service: ConfigService):
    """Test loading a non-existent configuration file raises error."""
    with pytest.raises(FileNotFoundError):
        await config_service.load_config("nonexistent")


async def test_get_value(config_service: ConfigService):
    """Test getting values using dot notation."""
    await config_service.load_config("core")

    # Test successful value retrieval
    assert config_service.get_value("core", "window.title") == "Test Window"
    assert config_service.get_value("core", "window.executable") == "test.exe"

    # Test with default values
    assert config_service.get_value("core", "nonexistent", "default") == "default"
    assert config_service.get_value("nonexistent", "some.path", 123) == 123

    # Test nested non-existent paths
    assert config_service.get_value("core", "window.nonexistent", "default") == "default"


async def test_config_caching(config_service: ConfigService, temp_config_dir):
    """Test that configurations are properly cached."""
    # Load config initially
    config1 = await config_service.load_config("core")

    # Modify the file on disk
    new_config = {"window": {"title": "Modified"}}
    with open(temp_config_dir / "core.json", "w") as f:
        json.dump(new_config, f)

    # Load again - should return cached version
    config2 = await config_service.load_config("core")
    assert config2 is config1
    assert config2["window"]["title"] == "Test Window"

    # Test reload
    config_service.reload("core")
    config3 = await config_service.load_config("core")
    assert config3 is not config1
    assert config3["window"]["title"] == "Modified"


def test_default_config_dir():
    """Test that default config directory is set correctly."""
    service = ConfigService()
    expected_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "poe_sidekick", "config")
    assert service._config_dir == expected_dir
