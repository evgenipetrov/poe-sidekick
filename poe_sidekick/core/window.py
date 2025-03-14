"""Window detection module for POE Sidekick.

This module provides functionality to detect and track the Path of Exile 2 game window.
"""

import logging
import os
from typing import Any, Optional

import win32api
import win32con
import win32gui
import win32process


class GameWindow:
    """Class for detecting and tracking the Path of Exile 2 game window."""

    def __init__(self) -> None:
        """Initialize the GameWindow instance."""
        self._hwnd: Optional[int] = None
        self._title: str = "Path of Exile 2"  # Game window title to search for
        self._exe_name: str = "PathOfExile2.exe"  # Game executable name

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
                exe_path = win32process.GetModuleFileNameEx(process_handle, 0)
                win32api.CloseHandle(process_handle)

                # Check if the executable name matches
                return os.path.basename(str(exe_path)) == self._exe_name

        except (win32gui.error, win32process.error, win32api.error, Exception) as e:
            logging.debug(f"Failed to check game process: {e}")
            return False
        return False

    def find_window(self) -> bool:
        """Find the Path of Exile 2 window.

        Returns:
            bool: True if the window was found, False otherwise.
        """

        def callback(hwnd: int, _: Any) -> bool:
            if win32gui.GetWindowText(hwnd) == self._title and self._is_game_process(hwnd):
                self._hwnd = hwnd
                return False  # Stop enumeration
            return True

        self._hwnd = None  # Reset handle before searching
        win32gui.EnumWindows(callback, None)
        return self._hwnd is not None

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

    def bring_to_front(self) -> bool:
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
