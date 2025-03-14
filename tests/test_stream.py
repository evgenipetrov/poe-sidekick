"""Tests for screenshot stream functionality."""

import asyncio
from collections import deque
from unittest.mock import Mock, patch

import pytest
from rx.subject import Subject

from poe_sidekick.core.stream import ScreenshotStream
from poe_sidekick.services.config import ConfigService


@pytest.fixture
def config_service():
    """Create a mock config service with test values."""
    config = Mock(spec=ConfigService)
    config.get_value.return_value = {
        "metrics": {
            "frame_time_window": 10,
            "memory_window": 10,
            "processing_window": 10,
            "metrics_save_interval": 300,
            "debug_frame_interval": 30,
        },
        "performance": {"target_fps": 30, "frame_buffer_size": 10, "max_memory_mb": 500, "max_processing_ms": 33},
    }
    return config


@pytest.fixture
@patch("psutil.Process")
def stream(mock_process, config_service):
    """Create a ScreenshotStream with mock config service."""
    mock_memory_info = Mock()
    mock_memory_info.rss = 500 * 1024 * 1024  # 500MB
    mock_process_instance = Mock()
    mock_process_instance.memory_info.return_value = mock_memory_info
    mock_process.return_value = mock_process_instance
    return ScreenshotStream(config_service)


@patch("dxcam.create")
async def test_start_creates_camera(mock_create, stream, config_service):
    """Test that start initializes the camera."""
    mock_camera = Mock()
    mock_create.return_value = mock_camera

    await stream.start()

    mock_create.assert_called_once()
    assert stream._running is True
    assert isinstance(stream._capture_task, asyncio.Task)


@patch("dxcam.create")
async def test_start_with_region(mock_create, stream, config_service):
    """Test that start sets camera region when provided."""
    mock_camera = Mock()
    mock_create.return_value = mock_camera
    region = (0, 0, 100, 100)

    await stream.start(region)

    assert mock_camera.region == region


@patch("dxcam.create")
async def test_metrics_tracking(mock_create, stream):
    """Test that performance metrics are tracked."""
    # Setup camera mock
    mock_camera = Mock()
    mock_create.return_value = mock_camera

    # Simulate frame capture
    frame = Mock()
    mock_camera.grab.return_value = frame

    await stream.start()
    await asyncio.sleep(0.1)  # Let it capture a few frames
    await stream.stop()

    # Print actual values for debugging
    print("Memory values:", list(stream.metrics["memory_usage"]))

    # Verify metrics
    metrics = stream.metrics
    assert isinstance(metrics["frame_times"], deque)
    assert isinstance(metrics["memory_usage"], deque)
    assert isinstance(metrics["processing_delays"], deque)
    assert isinstance(metrics["dropped_frames"], int)

    assert len(metrics["frame_times"]) > 0
    assert len(metrics["memory_usage"]) > 0
    assert len(metrics["processing_delays"]) > 0

    # Check memory usage values
    assert all(mem == 500.0 for mem in metrics["memory_usage"])  # Should be 500MB from our mock


def test_metrics_initialization(stream, config_service):
    """Test that metrics are properly initialized from config."""
    config = config_service.get_value("core", "screenshot_stream")
    metrics = stream.metrics

    assert len(metrics["frame_times"]) == 0
    assert metrics["frame_times"].maxlen == config["metrics"]["frame_time_window"]
    assert metrics["memory_usage"].maxlen == config["metrics"]["memory_window"]
    assert metrics["processing_delays"].maxlen == config["metrics"]["processing_window"]
    assert metrics["dropped_frames"] == 0


@patch("dxcam.create")
async def test_continuous_capture(mock_create, stream):
    """Test that screenshots are continuously captured."""
    mock_camera = Mock()
    mock_create.return_value = mock_camera
    frames = [Mock(), Mock(), Mock()]
    mock_camera.grab.side_effect = frames

    received_frames = []
    stream.observable.subscribe(lambda x: received_frames.append(x))

    await stream.start()
    # Let capture loop run for a short time
    await asyncio.sleep(0.1)
    await stream.stop()

    assert len(received_frames) > 0
    assert all(frame in frames for frame in received_frames)


async def test_stop_cleanup(stream):
    """Test that stop cleans up resources."""
    stream._running = True
    stream._camera = Mock()
    stream._capture_task = asyncio.create_task(asyncio.sleep(1))

    await stream.stop()

    assert stream._running is False
    assert stream._camera is None
    assert stream._capture_task.cancelled()


def test_observable_returns_subject(stream):
    """Test that observable property returns RxPY Subject."""
    assert isinstance(stream.observable, Subject)
