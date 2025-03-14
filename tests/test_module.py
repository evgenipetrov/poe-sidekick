"""Unit tests for core module system."""

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest
from rx.subject import Subject

from poe_sidekick.core.example_module import ExampleModule
from poe_sidekick.core.module import BaseModule, ModuleConfig


class CustomModule(BaseModule):
    """Custom module implementation for testing BaseModule."""

    def __init__(self, config: ModuleConfig, services: dict[str, Any]):
        super().__init__(config, services)
        self.processed_frames = []

    def _process_frame(self, frame: np.ndarray) -> None:
        self.processed_frames.append(frame)

    async def _on_activate(self) -> None:
        """Test implementation of activate hook."""
        pass

    async def _on_deactivate(self) -> None:
        """Test implementation of deactivate hook."""
        pass


@pytest.fixture
def mock_services():
    return {"vision": MagicMock(), "keyboard": MagicMock(), "mouse": MagicMock()}


@pytest.fixture
def custom_module(mock_services):
    config = ModuleConfig(name="custom_module")
    return CustomModule(config, mock_services)


@pytest.fixture
def example_module(mock_services):
    return ExampleModule(mock_services)


def test_module_initialization(custom_module):
    """Test basic module initialization."""
    assert custom_module.name == "custom_module"
    assert not custom_module.active
    assert custom_module.state == {}
    assert isinstance(custom_module._frame_subject, Subject)


@pytest.mark.asyncio
async def test_module_activation(custom_module):
    """Test module activation and deactivation."""
    # Test activation
    await custom_module.activate()
    assert custom_module.active

    # Test double activation (should not raise)
    await custom_module.activate()
    assert custom_module.active

    # Test deactivation
    await custom_module.deactivate()
    assert not custom_module.active

    # Test double deactivation (should not raise)
    await custom_module.deactivate()
    assert not custom_module.active


@pytest.mark.asyncio
async def test_disabled_module_activation(mock_services):
    """Test that disabled modules cannot be activated."""
    config = ModuleConfig(name="disabled_module", enabled=False)
    module = CustomModule(config, mock_services)

    await module.activate()
    assert not module.active


@pytest.mark.asyncio
async def test_frame_processing(custom_module):
    """Test frame processing workflow."""
    # Create test frame
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Module should not process frames when inactive
    custom_module.process_frame(frame)
    assert len(custom_module.processed_frames) == 0

    # Activate and process frame
    await custom_module.activate()
    custom_module.process_frame(frame)
    assert len(custom_module.processed_frames) == 1
    assert np.array_equal(custom_module.processed_frames[0], frame)


@pytest.mark.asyncio
async def test_frame_subscription(custom_module):
    """Test frame subscription functionality."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    received_frames = []

    # Subscribe to frames
    custom_module.subscribe_to_frames(lambda f: received_frames.append(f))

    # Activate and process frame
    await custom_module.activate()
    custom_module.process_frame(frame)

    assert len(received_frames) == 1
    assert np.array_equal(received_frames[0], frame)


@pytest.mark.asyncio
async def test_state_updates(custom_module):
    """Test module state management."""
    # Initial state should be empty
    assert custom_module.state == {}

    # Update state
    test_state = {"key": "value"}
    custom_module.update_state(test_state)

    # Verify state was updated
    assert custom_module.state == test_state

    # Verify state copy is returned (not reference)
    state_copy = custom_module.state
    state_copy["new_key"] = "new_value"
    assert "new_key" not in custom_module.state


@pytest.mark.asyncio
async def test_example_module_functionality(example_module):
    """Test the TestModule implementation."""
    # Create test frame
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Verify initial state
    assert example_module.state.get("frame_count", 0) == 0
    assert example_module.state.get("last_frame_shape") is None

    # Activate and process frames
    await example_module.activate()
    for _ in range(3):
        example_module.process_frame(frame)

    # Verify frame counting and state updates
    assert example_module.state["frame_count"] == 3
    assert example_module.state["last_frame_shape"] == frame.shape

    # Test deactivation resets
    await example_module.deactivate()
    await example_module.activate()  # Should reset counter
    assert example_module.state["frame_count"] == 0
