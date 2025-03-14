import json
from unittest.mock import MagicMock, patch

import pytest

from poe_sidekick.core.engine import Engine
from poe_sidekick.services.config import ConfigService


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create test config files
    core_config = {
        "window": {"title": "Test Window", "executable": "test.exe", "capture_rate": 30},
        "engine": {"shutdown_timeout": 2.0, "module_init_timeout": 1.0},
    }

    with open(config_dir / "core.json", "w") as f:
        json.dump(core_config, f)

    return config_dir


@pytest.fixture
def mock_window():
    """Create a mock window instance."""
    window = MagicMock()
    window.find_window.return_value = True
    return window


@pytest.fixture
async def engine(temp_config_dir, mock_window):
    """Create an engine instance with mocked dependencies."""
    with patch("poe_sidekick.core.engine.GameWindow") as window_cls:
        window_cls.return_value = mock_window

        # Override config directory in engine
        engine = Engine()
        engine._config = ConfigService(str(temp_config_dir))

        return engine


async def test_engine_start(engine, mock_window):
    """Test engine start uses correct configuration."""
    await engine.start()

    # Verify window was searched for
    mock_window.find_window.assert_called_once()
    mock_window.bring_to_front.assert_called_once()

    assert engine.is_running


async def test_engine_stop_uses_config_timeout(engine):
    """Test engine stop uses timeout from config."""
    await engine.start()

    with patch.object(engine, "_cleanup_components") as mock_cleanup:
        await engine.stop()

        # Verify cleanup was called with config timeout
        mock_cleanup.assert_called_once_with(2.0)  # Value from test config
        assert not engine.is_running


async def test_engine_window_not_found_error(engine, mock_window):
    """Test appropriate error when window not found."""
    mock_window.find_window.return_value = False

    with pytest.raises(RuntimeError) as exc_info:
        await engine.start()

    # Verify error message uses window title from config
    assert "Test Window window not found" in str(exc_info.value)
    assert not engine.is_running


async def test_engine_cleanup(engine):
    """Test engine cleanup with modules."""
    # Add some mock modules
    mock_module1 = MagicMock()
    mock_module2 = MagicMock()
    engine._modules = {"module1": mock_module1, "module2": mock_module2}

    await engine._cleanup_components(1.0)

    # Verify all modules were cleaned up
    mock_module1.cleanup.assert_called_once()
    mock_module2.cleanup.assert_called_once()
    assert not engine._modules  # Modules dict should be empty after cleanup


async def test_engine_cleanup_handles_errors(engine):
    """Test engine cleanup handles module errors gracefully."""
    # Add mock modules where one fails cleanup
    mock_module1 = MagicMock()
    mock_module2 = MagicMock()
    mock_module2.cleanup.side_effect = Exception("Cleanup failed")
    engine._modules = {"module1": mock_module1, "module2": mock_module2}

    # Should not raise exception
    await engine._cleanup_components(1.0)

    # Verify all modules were attempted to be cleaned up
    mock_module1.cleanup.assert_called_once()
    mock_module2.cleanup.assert_called_once()
    assert not engine._modules  # Modules dict should be empty after cleanup
