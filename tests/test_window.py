"""Tests for the window detection module."""

from unittest.mock import Mock, patch

import pytest
import win32con

from poe_sidekick.core.window import GameWindow


@pytest.fixture
def mock_win32gui():
    """Fixture to mock win32gui functions."""
    with patch("poe_sidekick.core.window.win32gui") as mock:
        yield mock


@pytest.fixture
def mock_win32process():
    """Fixture to mock win32process functions."""
    with patch("poe_sidekick.core.window.win32process") as mock:
        yield mock


@pytest.fixture
def mock_win32api():
    """Fixture to mock win32api functions."""
    with patch("poe_sidekick.core.window.win32api") as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Fixture to mock ConfigService."""
    with patch("poe_sidekick.core.window.ConfigService") as mock:
        instance = Mock()
        instance.get_value.side_effect = lambda mod, key: {
            "window.title": "Path of Exile 2",
            "window.executable": "PathOfExile.exe",
        }.get(key)

        # Mock the async load_config method
        async def mock_load_config(config_name):
            pass

        instance.load_config = mock_load_config

        mock.return_value = instance
        yield mock


async def test_find_window_when_game_running(mock_win32gui, mock_win32process, mock_win32api, mock_config):
    """Test finding the game window when it's running."""
    # Setup
    window = GameWindow()
    await window.initialize()
    mock_hwnd = 12345

    def mock_enum_windows(callback, windows_list):
        # Mock window visibility checks in the callback
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.IsWindowVisible.return_value = True
        # Call callback with mock window handle
        callback(mock_hwnd, windows_list)
        return True

    mock_win32gui.EnumWindows.side_effect = mock_enum_windows
    mock_win32gui.IsWindow.return_value = True
    mock_win32gui.IsWindowVisible.return_value = True
    mock_win32gui.GetWindowText.return_value = "Path of Exile 2"

    # Mock process checking
    mock_win32process.GetWindowThreadProcessId.return_value = (None, 67890)
    mock_win32api.OpenProcess.return_value = "handle"
    mock_win32process.GetModuleFileNameEx.return_value = "PathOfExile.exe"

    # Execute
    result = window.find_window()

    # Assert
    assert result is True
    assert window._hwnd == mock_hwnd


async def test_find_window_when_game_not_running(mock_win32gui, mock_win32process, mock_win32api, mock_config):
    """Test finding the game window when it's not running."""
    # Setup
    window = GameWindow()
    await window.initialize()

    def mock_enum_windows(callback, _):
        # Simulate no game window found
        windows = []
        # Mock window visibility checks in the callback
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.IsWindowVisible.return_value = True
        # Call callback and ensure window is added to list
        callback(12345, windows)
        # Verify window was added
        if not windows:
            # If windows list is empty, add the window directly
            windows.append(12345)
        return True

    mock_win32gui.EnumWindows.side_effect = mock_enum_windows
    mock_win32gui.IsWindow.return_value = True
    mock_win32gui.IsWindowVisible.return_value = True
    mock_win32gui.GetWindowText.return_value = "Some Other Window"

    # Execute
    result = window.find_window()

    # Assert
    assert result is False
    assert window._hwnd is None


async def test_is_window_focused_when_focused(mock_win32gui, mock_config):
    """Test checking if window is focused when it is."""
    # Setup
    window = GameWindow()
    await window.initialize()
    window._hwnd = 12345
    mock_win32gui.GetForegroundWindow.return_value = 12345

    # Execute
    result = window.is_window_focused()

    # Assert
    assert result is True


async def test_is_window_focused_when_not_focused(mock_win32gui, mock_config):
    """Test checking if window is focused when it's not."""
    # Setup
    window = GameWindow()
    await window.initialize()
    window._hwnd = 12345
    mock_win32gui.GetForegroundWindow.return_value = 67890

    # Execute
    result = window.is_window_focused()

    # Assert
    assert result is False


async def test_get_window_rect_when_window_exists(mock_win32gui, mock_config):
    """Test getting window rect when window exists."""
    # Setup
    window = GameWindow()
    await window.initialize()
    window._hwnd = 12345
    expected_rect = (0, 0, 1920, 1080)
    mock_win32gui.GetWindowRect.return_value = expected_rect

    # Execute
    result = window.get_window_rect()

    # Assert
    assert result == expected_rect


async def test_get_window_rect_when_error_occurs(mock_win32gui, mock_config):
    """Test getting window rect when win32gui error occurs."""
    # Setup
    window = GameWindow()
    await window.initialize()
    window._hwnd = 12345
    mock_win32gui.GetWindowRect.side_effect = Exception("win32gui.error")

    # Execute
    result = window.get_window_rect()

    # Assert
    assert result is None
    assert window._hwnd is None


async def test_bring_to_front_when_minimized(mock_win32gui, mock_config):
    """Test bringing window to front when it's minimized."""
    # Setup
    window = GameWindow()
    await window.initialize()
    window._hwnd = 12345
    mock_win32gui.IsIconic.return_value = True

    # Execute
    result = await window.bring_to_front()

    # Assert
    assert result is True
    mock_win32gui.ShowWindow.assert_called_once_with(12345, win32con.SW_RESTORE)
    mock_win32gui.SetForegroundWindow.assert_called_once_with(12345)


async def test_bring_to_front_when_error_occurs(mock_win32gui, mock_config):
    """Test bringing window to front when error occurs."""
    # Setup
    window = GameWindow()
    await window.initialize()
    window._hwnd = 12345
    mock_win32gui.SetForegroundWindow.side_effect = Exception("win32gui.error")

    # Execute
    result = await window.bring_to_front()

    # Assert
    assert result is False
    assert window._hwnd is None
