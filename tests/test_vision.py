"""Tests for the vision service."""

from typing import Any, Callable, cast
from unittest.mock import Mock, patch

import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image, ImageDraw
from rx.core.observable import Observable
from rx.core.observer import Observer
from rx.subject.subject import Subject

from poe_sidekick.core.stream import ScreenshotStream
from poe_sidekick.services.vision import TemplateMatch, VisionService


@pytest.fixture
def mock_stream() -> ScreenshotStream:
    """Create a mock screenshot stream."""
    mock = Mock(spec=ScreenshotStream)
    mock_subject = Mock(spec=Subject)
    mock.observable = mock_subject
    mock_subject.subscribe = Mock(return_value=Mock())
    return mock


@pytest.fixture
def vision_service(mock_stream: ScreenshotStream) -> VisionService:
    """Create a vision service with mock stream."""
    return VisionService(mock_stream)


@pytest.fixture
def sample_frame() -> NDArray[np.uint8]:
    """Create a sample frame for testing."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


@pytest.fixture
def sample_template() -> NDArray[np.uint8]:
    """Create a sample template for testing."""
    return np.zeros((10, 10, 3), dtype=np.uint8)


class TestVisionService:
    """Tests for VisionService class."""

    def test_initialization(self, mock_stream: ScreenshotStream) -> None:
        """Test service initialization."""
        service = VisionService(mock_stream)
        assert service._frame is None
        assert isinstance(service._cache, dict)
        assert mock_stream.observable.subscribe.called

    async def test_find_template_no_frame(
        self, vision_service: VisionService, sample_template: NDArray[np.uint8]
    ) -> None:
        """Test template matching with no frame available."""
        result = await vision_service.find_template(sample_template)
        assert result is None

    async def test_find_template_with_frame(
        self,
        vision_service: VisionService,
        sample_frame: NDArray[np.uint8],
        sample_template: NDArray[np.uint8],
    ) -> None:
        """Test template matching with frame."""
        vision_service._frame = sample_frame
        result = await vision_service.find_template(sample_template)
        assert result is not None
        assert isinstance(result, TemplateMatch)
        assert isinstance(result.location, tuple)
        assert isinstance(result.confidence, float)

    async def test_find_template_with_search_frame(
        self,
        vision_service: VisionService,
        sample_frame: NDArray[np.uint8],
        sample_template: NDArray[np.uint8],
    ) -> None:
        """Test template matching with provided search frame."""
        result = await vision_service.find_template(sample_template, search_frame=sample_frame)
        assert result is not None
        x, y = result.location
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_frame_update(self, vision_service: VisionService, sample_frame: NDArray[np.uint8]) -> None:
        """Test frame update handler."""
        vision_service._cache["test"] = Mock()
        vision_service._on_frame(sample_frame)
        assert vision_service._frame is sample_frame
        assert len(vision_service._cache) == 0  # Cache should be cleared

    async def test_get_text_no_frame(self, vision_service: VisionService) -> None:
        """Test OCR with no frame available."""
        region = (0, 0, 50, 50)
        result = await vision_service.get_text(region)
        assert result is None

    @patch("pytesseract.image_to_string")
    async def test_get_text_with_frame(self, mock_ocr: Mock, vision_service: VisionService) -> None:
        """Test OCR with frame containing text."""
        # Setup mock OCR response
        mock_ocr.return_value = "Test Text"

        # Create a test image
        img = Image.new("RGB", (200, 50), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test Text", fill="black")
        frame = np.array(img, dtype=np.uint8)

        # Set frame and test region
        vision_service._frame = frame
        region = (0, 0, 200, 50)

        # Test with preprocessing
        result = await vision_service.get_text(region, preprocessing={"threshold": 128, "denoise": True, "scale": 2.0})
        assert result == "Test Text"
        mock_ocr.assert_called_once()

    @patch("pytesseract.image_to_string")
    async def test_get_text_error_handling(
        self,
        mock_ocr: Mock,
        vision_service: VisionService,
        sample_frame: NDArray[np.uint8],
    ) -> None:
        """Test OCR error handling."""
        mock_ocr.side_effect = Exception("OCR Error")
        vision_service._frame = sample_frame
        region = (0, 0, 50, 50)
        result = await vision_service.get_text(region)
        assert result is None

    async def test_detect_game_state_no_frame(
        self, vision_service: VisionService, sample_template: NDArray[np.uint8]
    ) -> None:
        """Test game state detection with no frame."""
        templates = {"state1": sample_template}
        result = await vision_service.detect_game_state(templates)
        assert result is None

    async def test_detect_game_state_with_frame(
        self,
        vision_service: VisionService,
        sample_frame: NDArray[np.uint8],
        sample_template: NDArray[np.uint8],
    ) -> None:
        """Test game state detection with frame."""
        vision_service._frame = sample_frame
        templates = {"state1": sample_template, "state2": sample_template}
        result = await vision_service.detect_game_state(templates)
        assert result in templates or result is None
