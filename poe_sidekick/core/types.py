"""Type definitions for external dependencies."""

from typing import Optional, Protocol


class DXCamera(Protocol):
    """Type protocol for dxcam.DXCamera."""

    @property
    def region(self) -> Optional[tuple[int, int, int, int]]:
        """Get capture region."""
        ...

    @region.setter
    def region(self, value: tuple[int, int, int, int]) -> None:
        """Set capture region."""
        ...

    def grab(self) -> Optional[bytes]:
        """Capture a single frame."""
        ...
