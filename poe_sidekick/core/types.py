"""Type definitions for external dependencies."""

from collections import deque
from typing import Optional, Protocol, TypedDict


class StreamMetrics(TypedDict):
    """Type for screenshot stream metrics."""

    frame_times: deque[float]  # Frame capture times in ms
    memory_usage: deque[float]  # Memory usage in MB
    processing_delays: deque[float]  # Processing delays in ms
    dropped_frames: int


class StreamConfig(TypedDict):
    """Type for screenshot stream configuration."""

    metrics: dict[str, int]  # Metric configuration values
    performance: dict[str, int | float]  # Performance thresholds


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
