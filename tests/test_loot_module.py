"""Tests for the loot manager module."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from poe_sidekick.plugins.loot_manager import LootModule
from poe_sidekick.services.template import TemplateService


@pytest.fixture
def mock_template_service():
    """Create a mock template service."""
    service = MagicMock(spec=TemplateService)
    service.load_metadata.return_value = {
        "version": "0.1.0",
        "templates": {
            "currency": {
                "divine_orb": {
                    "name": "Divine Orb",
                    "category": "currency",
                    "ground_label": {
                        "path": "test/path.png",
                        "color_range": {"hue": [30, 40], "saturation": [180, 255], "value": [200, 255]},
                        "detection_threshold": 0.85,
                    },
                }
            }
        },
    }
    return service


@pytest.fixture
def mock_services(mock_template_service):
    """Create mock services for testing."""
    return {"vision_service": MagicMock(), "input_service": MagicMock(), "template_service": mock_template_service}


@pytest.fixture
def mock_config(monkeypatch):
    """Create mock config that enables the module for testing."""
    test_config = {
        "activation": {"enabled_by_default": True, "hotkey": "F4"},
        "filters": {
            "min_item_value": 1.0,
            "priority_items": ["Chaos Orb", "Divine Orb", "Exalted Orb"],
            "item_classes": {"currency": True, "unique": True, "rare": {"enabled": True, "min_item_level": 75}},
        },
        "behavior": {"auto_pickup_threshold": 5.0, "scan_frequency": 0.5, "pickup_radius": 50},
        "ui": {"highlight_color": "#00ff00", "show_item_value": True, "show_item_level": True},
    }

    def mock_open(*args, **kwargs):
        return type(
            "MockFile",
            (),
            {
                "read": lambda self: json.dumps(test_config),
                "__enter__": lambda self: self,
                "__exit__": lambda self, *args: None,
                "__iter__": lambda self: iter([json.dumps(test_config)]),
            },
        )()

    monkeypatch.setattr("builtins.open", mock_open)
    return test_config


@pytest.fixture
def loot_config():
    """Load the actual loot module configuration."""
    config_path = Path("poe_sidekick/config/loot_module.json")
    with open(config_path) as f:
        return json.load(f)


def test_loot_module_initialization(mock_services, mock_config):
    """Test that the loot module initializes correctly."""
    module = LootModule(mock_services)

    # Verify module name
    assert module.name == "loot_module"

    # Verify enabled setting loaded from config
    assert module.enabled == mock_config["activation"]["enabled_by_default"]

    # Verify initial state
    state = module.state
    assert state["frame_shape"] is None
    assert state["detected_items"] == []


@pytest.mark.asyncio
async def test_loot_module_activation(mock_services, mock_config):
    """Test module activation and deactivation."""
    module = LootModule(mock_services)

    # Test activation
    await module.activate()
    assert module.active
    assert len(module._ground_templates) == 1  # One template from mock data
    state = module.state
    assert state["frame_shape"] is None
    assert state["detected_items"] == []

    # Test deactivation
    await module.deactivate()
    assert not module.active
    assert not module._ground_templates  # Templates cleared


def test_frame_processing(mock_services, mock_config):
    """Test basic frame processing functionality."""
    module = LootModule(mock_services)

    # Create a test frame
    test_frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Process frame
    module._process_frame(test_frame)

    # Verify state updated
    state = module.state
    assert state["frame_shape"] == (100, 100, 3)
    assert state["detected_items"] == []


@pytest.mark.asyncio
async def test_template_loading_error(mock_services, mock_config):
    """Test error handling during template loading."""
    mock_services["template_service"].load_metadata.side_effect = ValueError("Test error")
    module = LootModule(mock_services)

    # Activation should fail due to template loading error
    with pytest.raises(ValueError, match="Test error"):
        await module.activate()
