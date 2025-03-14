"""Tests for input service functionality."""

import time
from unittest.mock import patch

import pytest

from poe_sidekick.services.input import InputConfig, InputService


@pytest.fixture
def input_service():
    """Create input service for testing."""
    return InputService(InputConfig(min_delay_seconds=0.01))


def test_config_defaults():
    """Test default configuration values."""
    config = InputConfig()
    assert config.min_delay_seconds == 0.05
    assert config.cursor_speed == 1.0
    assert config.key_press_duration == 0.1


def test_custom_config():
    """Test custom configuration values."""
    config = InputConfig(min_delay_seconds=0.1, cursor_speed=2.0, key_press_duration=0.2)
    service = InputService(config)
    assert service.config.min_delay_seconds == 0.1
    assert service.config.cursor_speed == 2.0
    assert service.config.key_press_duration == 0.2


@patch("pyautogui.position")
def test_get_cursor_position(mock_position):
    """Test getting cursor position."""
    mock_position.return_value = (100, 200)
    service = InputService()

    pos = service.get_cursor_position()
    assert pos == (100, 200)
    mock_position.assert_called_once()


@patch("pyautogui.moveTo")
def test_move_cursor_to(mock_move):
    """Test moving cursor to position."""
    service = InputService(InputConfig(min_delay_seconds=0.01))

    service.move_cursor_to(100, 200)
    mock_move.assert_called_once_with(100, 200, duration=0.01)


@patch("pyautogui.click")
def test_click_left(mock_click):
    """Test left click."""
    service = InputService()

    service.click_left()
    mock_click.assert_called_once_with(button="left")


@patch("pyautogui.click")
def test_click_right(mock_click):
    """Test right click."""
    service = InputService()

    service.click_right()
    mock_click.assert_called_once_with(button="right")


@patch("pyautogui.mouseDown")
def test_hold_left(mock_down):
    """Test holding left button."""
    service = InputService()

    service.hold_left()
    mock_down.assert_called_once_with(button="left")


@patch("pyautogui.mouseUp")
def test_release_left(mock_up):
    """Test releasing left button."""
    service = InputService()

    service.release_left()
    mock_up.assert_called_once_with(button="left")


@patch("pyautogui.keyDown")
def test_press_key(mock_keydown):
    """Test pressing a key."""
    service = InputService()

    service.press_key("a")
    mock_keydown.assert_called_once_with("a")


@patch("pyautogui.keyUp")
def test_release_key(mock_keyup):
    """Test releasing a key."""
    service = InputService()

    service.release_key("a")
    mock_keyup.assert_called_once_with("a")


@patch("pyautogui.write")
def test_type_string_default_interval(mock_write):
    """Test typing string with default interval."""
    service = InputService(InputConfig(min_delay_seconds=0.1))

    service.type_string("test")
    mock_write.assert_called_once_with("test", interval=0.1)


@patch("pyautogui.write")
def test_type_string_custom_interval(mock_write):
    """Test typing string with custom interval."""
    service = InputService()

    service.type_string("test", interval=0.2)
    mock_write.assert_called_once_with("test", interval=0.2)


@patch("pyautogui.press")
def test_tap_key(mock_press):
    """Test tapping a key."""
    service = InputService()

    service.tap_key("a")
    mock_press.assert_called_once_with("a")


def test_enforce_delay():
    """Test minimum delay between actions is enforced."""
    service = InputService(InputConfig(min_delay_seconds=0.1))

    start = time.time()

    # Perform multiple actions
    service.click_left()
    service.click_right()
    service.click_left()

    duration = time.time() - start

    # Should take at least 0.3 seconds (3 actions * 0.1 delay)
    assert duration >= 0.3, "Minimum delay not enforced"
