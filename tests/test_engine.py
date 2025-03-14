import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from poe_sidekick.core.engine import Engine
from poe_sidekick.services.config import ConfigService


class CleanupError(Exception):
    """Error raised during module cleanup."""


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create test config files
    core_config = {
        "window": {
            "title": "Test Window",
            "executable": "test.exe",
            "capture_rate": 30,
            "detection_timeout": 5.0,
            "detection_interval": 0.1,
        },
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
        # Mock all async window methods
        async def _mock_initialize():
            pass

        async def _mock_bring_to_front():
            return True

        mock_window.initialize = MagicMock(wraps=_mock_initialize)
        mock_window.bring_to_front = MagicMock(wraps=_mock_bring_to_front)
        window_cls.return_value = mock_window

        # Override config directory in engine
        engine = Engine()
        engine._config = ConfigService(str(temp_config_dir))
        await engine._config.load_config("core")  # Pre-load core config

        return engine


async def test_engine_start(engine, mock_window):
    """Test engine start uses correct configuration."""
    await engine.start()

    # Verify window was initialized and searched for in correct order
    mock_window.initialize.assert_called_once()
    mock_window.find_window.assert_called_once()
    mock_window.bring_to_front.assert_called_once()

    # Check initialization happened before find_window
    initialize_call = mock_window.method_calls.index(("initialize", (), {}))
    find_window_call = mock_window.method_calls.index(("find_window", (), {}))
    assert initialize_call < find_window_call

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
    """Test appropriate error when window not found after timeout."""
    mock_window.find_window.return_value = False

    with pytest.raises(RuntimeError) as exc_info:
        await engine.start()

    # Verify error message uses window title from config
    error_msg = str(exc_info.value)
    assert "Unable to find Test Window" in error_msg
    assert "Path of Exile 2 (test.exe) is not running" in error_msg
    assert not engine.is_running
    # Check that find_window was called multiple times
    assert mock_window.find_window.call_count > 1


async def test_engine_window_retry_success(engine, mock_window):
    """Test successful window detection after retries."""
    # First two attempts fail, third succeeds
    mock_window.find_window.side_effect = [False, False, True]

    await engine.start()

    # Verify window was found after retries
    assert mock_window.find_window.call_count == 3
    assert mock_window.bring_to_front.call_count == 1
    assert engine.is_running


async def test_engine_window_detection_timeout(engine, mock_window):
    """Test window detection timeout with custom config values."""
    mock_window.find_window.return_value = False

    # Override detection timeout for faster test
    engine._config._configs["core"]["window"]["detection_timeout"] = 0.3
    engine._config._configs["core"]["window"]["detection_interval"] = 0.1

    start_time = asyncio.get_event_loop().time()
    with pytest.raises(RuntimeError) as exc_info:
        await engine.start()
    elapsed_time = asyncio.get_event_loop().time() - start_time

    # Verify timeout behavior
    error_msg = str(exc_info.value)
    assert "Unable to find Test Window" in error_msg
    assert "Path of Exile 2 (test.exe) is not running" in error_msg
    assert elapsed_time >= 0.3  # Should have waited for timeout
    assert elapsed_time < 0.5  # But not too long
    assert mock_window.find_window.call_count >= 3  # Should have tried multiple times
    assert not engine.is_running


async def test_engine_cleanup(engine):
    """Test engine cleanup with modules."""
    # Add mock modules with async cleanup methods
    mock_module1 = MagicMock()
    mock_module2 = MagicMock()

    async def _mock_cleanup():
        pass

    mock_module1.cleanup = MagicMock(wraps=_mock_cleanup)
    mock_module2.cleanup = MagicMock(wraps=_mock_cleanup)
    engine._modules = {"module1": mock_module1, "module2": mock_module2}

    await engine._cleanup_components(1.0)

    # Verify cleanup methods were accessed
    assert mock_module1.cleanup.called
    assert mock_module2.cleanup.called
    assert not engine._modules  # Modules dict should be empty after cleanup


async def test_engine_cleanup_handles_errors(engine):
    """Test engine cleanup handles module errors gracefully."""
    # Add mock modules with async cleanup methods
    mock_module1 = MagicMock()
    mock_module2 = MagicMock()

    # First module cleanup succeeds
    async def _mock_cleanup_success():
        pass

    # Second module cleanup raises an error
    async def _mock_cleanup_error():
        raise CleanupError()

    mock_module1.cleanup = MagicMock(wraps=_mock_cleanup_success)
    mock_module2.cleanup = MagicMock(wraps=_mock_cleanup_error)

    engine._modules = {"module1": mock_module1, "module2": mock_module2}

    # Should not raise exception
    await engine._cleanup_components(1.0)

    # Verify cleanup was attempted
    assert mock_module1.cleanup.called
    assert mock_module2.cleanup.called
    assert not engine._modules  # Modules dict should be empty after cleanup
