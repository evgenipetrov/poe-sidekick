"""Tests for screenshot stream functionality."""

import asyncio
from unittest.mock import Mock, patch

import pytest
from rx.subject import Subject

from poe_sidekick.core.stream import ScreenshotStream


@pytest.fixture
def stream():
    return ScreenshotStream()


@patch("dxcam.create")
async def test_start_creates_camera(mock_create, stream):
    """Test that start initializes the camera."""
    mock_camera = Mock()
    mock_create.return_value = mock_camera

    await stream.start()

    mock_create.assert_called_once()
    assert stream._running is True
    assert isinstance(stream._capture_task, asyncio.Task)


@patch("dxcam.create")
async def test_start_with_region(mock_create, stream):
    """Test that start sets camera region when provided."""
    mock_camera = Mock()
    mock_create.return_value = mock_camera
    region = (0, 0, 100, 100)

    await stream.start(region)

    assert mock_camera.region == region


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
