"""Window detection module for POE Sidekick.

This module provides functionality to detect and track the Path of Exile 2 game window.
"""

import logging
import os
from typing import Optional

import win32api
import win32con
import win32gui
import win32process

from poe_sidekick.services.config import ConfigService


class GameWindow:
    """Class for detecting and tracking the Path of Exile 2 game window."""

    def __init__(self) -> None:
        """Initialize the GameWindow instance."""
        self._hwnd: Optional[int] = None
        self._config = ConfigService()
        self._title: Optional[str] = None
        self._exe_name: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize window properties from config.

        This must be called before using any window detection methods.
        """
        await self._config.load_config("core")
        self._title = self._config.get_value("core", "window.title")
        self._exe_name = self._config.get_value("core", "window.executable")

    def _is_game_process(self, hwnd: int) -> bool:
        """Check if the window belongs to the Path of Exile 2 process.

        Args:
            hwnd: Window handle to check.

        Returns:
            bool: True if the window belongs to the game process, False otherwise.
        """
        try:
            # Get the process ID for the window
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # Get a handle to the process
            process_handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
            )

            if process_handle:
                # Get the process executable path
                exe_path = str(win32process.GetModuleFileNameEx(process_handle, 0))
                win32api.CloseHandle(process_handle)

                # Check if the executable name matches
                basename = os.path.basename(exe_path)
                logging.debug(f"Comparing executable names: {basename} == {self._exe_name}")
                return basename == self._exe_name

        except (win32gui.error, win32process.error, win32api.error, Exception) as e:
            logging.debug(f"Failed to check game process: {e}")
            return False
        return False

    def find_window(self) -> bool:
        """Find the Path of Exile 2 window.

        Returns:
            bool: True if the window was found, False otherwise.
        """
        if not self._title or not self._exe_name:
            logging.debug("Window title or executable name not set")
            return False

        try:
            # Get all top-level windows
            def enum_windows_callback(hwnd: int, windows: list[int]) -> bool:
                if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                    windows.append(hwnd)
                return True

            windows: list[int] = []
            win32gui.EnumWindows(enum_windows_callback, windows)

            # Check each window
            logging.debug(f"Found {len(windows)} windows to check")
            for hwnd in windows:
                try:
                    title = win32gui.GetWindowText(hwnd)
                    logging.debug(f"Checking window: '{title}' against '{self._title}'")

                    if title == self._title:
                        logging.debug("Found matching window title, checking process...")
                        process_match = self._is_game_process(hwnd)
                        logging.debug(f"Process match result: {process_match}")
                        if process_match:
                            logging.debug("Found matching process")
                            self._hwnd = hwnd
                            return True
                        else:
                            logging.debug("Process did not match")
                except Exception as e:
                    logging.debug(f"Error checking window {hwnd}: {e}")
                    continue

            logging.debug("No matching window found")
        except Exception as e:
            logging.debug(f"Error during window search: {e}")
            return False
        else:
            return False

    def is_window_available(self) -> bool:
        """Check if the game window is currently available.

        Returns:
            bool: True if the window is found and available, False otherwise.
        """
        return self.find_window()

    def is_window_focused(self) -> bool:
        """Check if the game window is currently focused.

        Returns:
            bool: True if the window is focused, False otherwise.
        """
        if not self._hwnd:
            return False
        return self._hwnd == win32gui.GetForegroundWindow()

    def get_window_rect(self) -> Optional[tuple[int, int, int, int]]:
        """Get the game window rectangle coordinates.

        Returns:
            Optional[Tuple[int, int, int, int]]: Tuple of (left, top, right, bottom) if window
                is found, None otherwise.
        """
        if not self._hwnd:
            return None
        try:
            return win32gui.GetWindowRect(self._hwnd)
        except Exception:
            self._hwnd = None
            return None

    def get_window_size(self) -> Optional[tuple[int, int]]:
        """Get the game window size.

        Returns:
            Optional[Tuple[int, int]]: Tuple of (width, height) if window is found,
                None otherwise.
        """
        rect = self.get_window_rect()
        if not rect:
            return None
        return (rect[2] - rect[0], rect[3] - rect[1])

    async def bring_to_front(self) -> bool:
        """Bring the game window to the foreground.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not self._hwnd:
            return False
        try:
            if win32gui.IsIconic(self._hwnd):  # If minimized
                win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self._hwnd)
        except Exception:
            self._hwnd = None
            return False
        else:
            return True
