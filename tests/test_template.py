"""Tests for the template service."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from poe_sidekick.services.item import (
    FileValidationError,
    MetadataError,
    RangeValidationError,
    TemplateNotFoundError,
    TemplateService,
    TemplateValidationError,
)


@pytest.fixture
def template_service():
    """Create a template service instance for testing."""
    config_service = MagicMock()
    return TemplateService(config_service)


@pytest.fixture
def valid_metadata():
    """Create valid template metadata for testing."""
    return {
        "version": "0.1.0",
        "templates": {
            "currency": {
                "divine_orb": {
                    "name": "Divine Orb",
                    "category": "currency",
                    "value_tier": 1,
                    "ground_label": {
                        "path": "ground_labels/currency/divine_orb.png",
                        "color_range": {"hue": [30, 40], "saturation": [180, 255], "value": [200, 255]},
                        "detection_threshold": 0.85,
                    },
                    "item_appearance": {
                        "path": "item_appearances/currency/divine_orb.png",
                        "detection_threshold": 0.90,
                        "grid_size": [1, 1],
                    },
                }
            }
        },
    }


def test_load_metadata_success(template_service, valid_metadata):
    """Test successful metadata loading."""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("builtins.open", mock_open(read_data=json.dumps(valid_metadata))),
    ):
        mock_exists.return_value = True
        metadata = template_service.load_metadata()
        assert metadata == valid_metadata
        assert template_service._metadata == valid_metadata


def test_load_metadata_file_not_found(template_service):
    """Test metadata loading when file doesn't exist."""
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        with pytest.raises(FileNotFoundError):
            template_service.load_metadata()


def test_load_metadata_invalid_json(template_service):
    """Test metadata loading with invalid JSON."""
    with patch("pathlib.Path.exists") as mock_exists, patch("builtins.open", mock_open(read_data="invalid json")):
        mock_exists.return_value = True
        with pytest.raises(json.JSONDecodeError):
            template_service.load_metadata()


def test_validate_metadata_missing_fields(template_service):
    """Test metadata validation with missing required fields."""
    invalid_metadata = {"templates": {}}  # Missing version
    with pytest.raises(TemplateValidationError):
        template_service.validate_metadata(invalid_metadata)


def test_validate_metadata_invalid_templates(template_service):
    """Test metadata validation with invalid templates structure."""
    invalid_metadata = {
        "version": "0.1.0",
        "templates": [],  # Should be dict
    }
    with pytest.raises(FileValidationError):
        template_service.validate_metadata(invalid_metadata)


def test_validate_ground_label(template_service):
    """Test ground label validation."""
    invalid_ground_label = {
        "path": "test.png",
        "color_range": {
            "hue": [30],  # Invalid length
            "saturation": [180, 255],
            "value": [200, 255],
        },
        "detection_threshold": 0.85,
    }
    with pytest.raises(RangeValidationError):
        template_service._validate_ground_label(invalid_ground_label, "test_template")


def test_validate_item_appearance(template_service):
    """Test item appearance validation."""
    invalid_item_appearance = {
        "path": "test.png",
        "detection_threshold": 0.9,
        "grid_size": [1],  # Invalid length
    }
    with pytest.raises(RangeValidationError):
        template_service._validate_item_appearance(invalid_item_appearance, "test_template")


def test_get_template_config_success(template_service, valid_metadata):
    """Test successful template config retrieval."""
    template_service._metadata = valid_metadata
    config = template_service.get_template_config("divine_orb")
    assert config["name"] == "Divine Orb"
    assert config["category"] == "currency"


def test_get_template_config_not_found(template_service, valid_metadata):
    """Test template config retrieval for non-existent template."""
    template_service._metadata = valid_metadata
    with pytest.raises(TemplateNotFoundError):
        template_service.get_template_config("nonexistent_template")


def test_get_template_config_metadata_not_loaded(template_service):
    """Test template config retrieval when metadata not loaded."""
    with pytest.raises(MetadataError):
        template_service.get_template_config("any_template")
