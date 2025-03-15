"""Vision service for processing screenshots and detecting game state.

This service provides functionality for:
- Template matching with caching
- OCR for text recognition
- Game state detection
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]

from poe_sidekick.core.stream import ScreenshotStream


@dataclass
class TemplateMatch:
    """Result of a template matching operation."""

    location: tuple[int, int]  # (x, y) coordinates of match
    confidence: float  # Match confidence score (0-1)


class VisionService:
    """Service for computer vision operations on game screenshots."""

    def __init__(self, stream: ScreenshotStream):
        self._stream = stream
        self._frame: Optional[np.ndarray] = None
        self._cache: dict[str, TemplateMatch] = {}

        # Subscribe to screenshot stream
        self._stream.observable.subscribe(self._on_frame)

    def _on_frame(self, frame: np.ndarray) -> None:
        """Handle new frame from screenshot stream."""
        self._frame = frame
        self._cache.clear()  # Invalidate cache on new frame

    async def find_template(
        self, template: np.ndarray, search_frame: Optional[np.ndarray] = None, threshold: float = 0.9
    ) -> Optional[TemplateMatch]:
        """Find template in frame using simple template matching.

        Args:
            template: numpy array of template image
            search_frame: optional frame to search in, uses current frame if None
            threshold: minimum confidence threshold (0-1)

        Returns:
            TemplateMatch if found above threshold, else None
        """
        frame = search_frame if search_frame is not None else self._frame
        if frame is None:
            return None

        # Simple template matching
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return None

        return TemplateMatch(location=max_loc, confidence=max_val)

    async def get_text(
        self,
        region: tuple[int, int, int, int],
        source_frame: Optional[np.ndarray] = None,
        preprocessing: Optional[dict] = None,
    ) -> Optional[str]:
        """Extract text from specified region using OCR.

        Args:
            region: (x, y, w, h) region to extract text from
            source_frame: optional frame to extract text from, uses current frame if None
            preprocessing: optional dict of preprocessing parameters with keys:
                - threshold: int (0-255) for binary threshold
                - denoise: bool for denoising
                - scale: float for image scaling

        Returns:
            Extracted text if successful, else None
        """
        frame = source_frame if source_frame is not None else self._frame
        if frame is None:
            return None

        x, y, w, h = region
        roi = frame[y : y + h, x : x + w]

        # Apply preprocessing if specified
        if preprocessing:
            # Convert to grayscale
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # Apply binary threshold
            if "threshold" in preprocessing:
                _, roi = cv2.threshold(roi, int(preprocessing["threshold"]), 255, cv2.THRESH_BINARY)

            # Apply denoising
            if preprocessing.get("denoise", False):
                roi = cv2.fastNlMeansDenoising(roi)

            # Scale image
            if "scale" in preprocessing:
                scale = preprocessing["scale"]
                roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        try:
            # Extract text using pytesseract
            text: str = pytesseract.image_to_string(roi).strip()
            if not text:
                return None
            else:
                return text
        except Exception:
            return None

    async def detect_game_state(self, state_templates: dict[str, np.ndarray]) -> Optional[str]:
        """Detect current game state using template matching.

        Args:
            state_templates: dict mapping state names to template images

        Returns:
            Name of detected state if confidence above threshold, else None
        """
        if self._frame is None:
            return None

        best_confidence = 0.0  # Change to float since we're comparing with confidence scores
        best_state = None

        for state_name, template in state_templates.items():
            match = await self.find_template(template)
            if match and match.confidence > best_confidence:
                best_confidence = match.confidence
                best_state = state_name

        return best_state
