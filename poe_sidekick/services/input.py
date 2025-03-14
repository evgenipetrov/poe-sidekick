"""Input service for interacting with game through mouse and keyboard inputs."""

import time
from dataclasses import dataclass
from typing import Optional

import pyautogui  # We'll need to add this to dependencies


@dataclass
class InputConfig:
    """Configuration for input service behaviors.

    Args:
        min_delay_seconds: Minimum delay between actions
        cursor_speed: Movement speed multiplier (1.0 = normal speed)
    """

    min_delay_seconds: float = 0.05
    cursor_speed: float = 1.0


class InputService:
    """Service for interacting with game through mouse inputs.

    This service provides explicit, low-level input operations with
    safety features like minimum delays between actions.

    Args:
        config: Optional configuration for input behaviors
    """

    def __init__(self, config: Optional[InputConfig] = None):
        self.config = config or InputConfig()
        self._last_action_time: float = 0

        # Configure pyautogui safety
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.MINIMUM_DURATION = self.config.min_delay_seconds
        pyautogui.PAUSE = self.config.min_delay_seconds

    def get_cursor_position(self) -> tuple[int, int]:
        """Get current cursor coordinates.

        Returns:
            Tuple of (x, y) coordinates
        """
        x, y = pyautogui.position()
        return (int(x), int(y))

    def move_cursor_to(self, x: int, y: int) -> None:
        """Move cursor to specific screen coordinates.

        Args:
            x: Target x coordinate
            y: Target y coordinate
        """
        self._enforce_delay()
        pyautogui.moveTo(x, y, duration=self.config.min_delay_seconds)

    def click_left(self) -> None:
        """Perform left mouse button click."""
        self._enforce_delay()
        pyautogui.click(button="left")

    def click_right(self) -> None:
        """Perform right mouse button click."""
        self._enforce_delay()
        pyautogui.click(button="right")

    def hold_left(self) -> None:
        """Press and hold left mouse button."""
        self._enforce_delay()
        pyautogui.mouseDown(button="left")

    def release_left(self) -> None:
        """Release left mouse button."""
        self._enforce_delay()
        pyautogui.mouseUp(button="left")

    def _enforce_delay(self) -> None:
        """Enforce minimum delay between actions."""
        current_time = time.time()
        time_since_last = current_time - self._last_action_time

        if time_since_last < self.config.min_delay_seconds:
            time.sleep(self.config.min_delay_seconds - time_since_last)

        self._last_action_time = time.time()
