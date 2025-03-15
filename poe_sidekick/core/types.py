"""Type definitions for external dependencies."""

from typing import Protocol, TypedDict


class StreamMetrics(TypedDict):
    """Type for screenshot stream metrics."""

    # frame_times: deque[float]  # Frame capture times in ms
    # memory_usage: deque[float]  # Memory usage in MB
    # processing_delays: deque[float]  # Processing delays in ms
    dropped_frames: int


class StreamConfig(TypedDict):
    """Type for screenshot stream configuration."""

    metrics: dict[str, int]  # Metric configuration values
    performance: dict[str, int | float]  # Performance thresholds


class DXCamera(Protocol):
    """Type protocol for dxcam.DXCamera."""

    @property
    def region(self) -> tuple[int, int, int, int] | None:
        """Get capture region."""
        ...

    @region.setter
    def region(self, value: tuple[int, int, int, int]) -> None:
        """Set capture region."""
        ...

    def grab(self) -> bytes | None:
        """Capture a single frame."""
        ...
