"""Tests for the window detection module."""

from unittest.mock import patch

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


def test_find_window_when_game_running(mock_win32gui, mock_win32process, mock_win32api):
    """Test finding the game window when it's running."""
    # Setup
    window = GameWindow()
    mock_hwnd = 12345

    def mock_enum_windows(callback, _):
        # Simulate finding the game window
        callback(mock_hwnd, None)

    mock_win32gui.EnumWindows.side_effect = mock_enum_windows
    mock_win32gui.GetWindowText.return_value = "Path of Exile 2"

    # Mock process checking
    mock_win32process.GetWindowThreadProcessId.return_value = (None, 67890)
    mock_win32api.OpenProcess.return_value = "handle"
    mock_win32process.GetModuleFileNameEx.return_value = "C:\\Games\\PathOfExile2.exe"

    # Execute
    result = window.find_window()

    # Assert
    assert result is True
    assert window._hwnd == mock_hwnd


def test_find_window_when_game_not_running(mock_win32gui, mock_win32process, mock_win32api):
    """Test finding the game window when it's not running."""
    # Setup
    window = GameWindow()

    def mock_enum_windows(callback, _):
        # Simulate no game window found
        callback(12345, None)

    mock_win32gui.EnumWindows.side_effect = mock_enum_windows
    mock_win32gui.GetWindowText.return_value = "Some Other Window"

    # Execute
    result = window.find_window()

    # Assert
    assert result is False
    assert window._hwnd is None


def test_is_window_focused_when_focused(mock_win32gui):
    """Test checking if window is focused when it is."""
    # Setup
    window = GameWindow()
    window._hwnd = 12345
    mock_win32gui.GetForegroundWindow.return_value = 12345

    # Execute
    result = window.is_window_focused()

    # Assert
    assert result is True


def test_is_window_focused_when_not_focused(mock_win32gui):
    """Test checking if window is focused when it's not."""
    # Setup
    window = GameWindow()
    window._hwnd = 12345
    mock_win32gui.GetForegroundWindow.return_value = 67890

    # Execute
    result = window.is_window_focused()

    # Assert
    assert result is False


def test_get_window_rect_when_window_exists(mock_win32gui):
    """Test getting window rect when window exists."""
    # Setup
    window = GameWindow()
    window._hwnd = 12345
    expected_rect = (0, 0, 1920, 1080)
    mock_win32gui.GetWindowRect.return_value = expected_rect

    # Execute
    result = window.get_window_rect()

    # Assert
    assert result == expected_rect


def test_get_window_rect_when_error_occurs(mock_win32gui):
    """Test getting window rect when win32gui error occurs."""
    # Setup
    window = GameWindow()
    window._hwnd = 12345
    mock_win32gui.GetWindowRect.side_effect = Exception("win32gui.error")

    # Execute
    result = window.get_window_rect()

    # Assert
    assert result is None
    assert window._hwnd is None


def test_bring_to_front_when_minimized(mock_win32gui):
    """Test bringing window to front when it's minimized."""
    # Setup
    window = GameWindow()
    window._hwnd = 12345
    mock_win32gui.IsIconic.return_value = True

    # Execute
    result = window.bring_to_front()

    # Assert
    assert result is True
    mock_win32gui.ShowWindow.assert_called_once_with(12345, win32con.SW_RESTORE)
    mock_win32gui.SetForegroundWindow.assert_called_once_with(12345)


def test_bring_to_front_when_error_occurs(mock_win32gui):
    """Test bringing window to front when error occurs."""
    # Setup
    window = GameWindow()
    window._hwnd = 12345
    mock_win32gui.SetForegroundWindow.side_effect = Exception("win32gui.error")

    # Execute
    result = window.bring_to_front()

    # Assert
    assert result is False
    assert window._hwnd is None
