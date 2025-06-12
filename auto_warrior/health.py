import logging
import cv2
import numpy as np

from auto_warrior.constants import (
    EMPTY_HEALTH_CONFIDENCE,
    MIN_TEMPLATE_CONFIDENCE,
)
from auto_warrior.exceptions import TemplateMatchError
from auto_warrior.templates import TemplateManager

logger = logging.getLogger(__name__)

class HealthDetector:
    """Handles health bar detection and analysis."""

    def __init__(self, template_manager: TemplateManager, debug_mode: bool = False) -> None:
        """Initialize health detector.

        Args:
            template_manager: Template manager instance
            debug_mode: Whether to enable debug logging
        """
        self.template_manager = template_manager
        self.debug_mode = debug_mode

    def get_health_percentage(self, screenshot_cv: np.ndarray) -> float:
        """Get current health percentage using template matching.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Health percentage as float (0.0 to 1.0)

        Raises:
            TemplateMatchError: If template matching fails
        """
        if self.debug_mode:
            logger.debug("Starting health percentage detection")

        if not self.template_manager.has_health_templates():
            if self.debug_mode:
                logger.error("No health templates loaded!")
            return 1.0

        try:
            return self._match_health_template(screenshot_cv)
        except Exception as e:
            logger.error(f"Health detection failed: {e}")
            raise TemplateMatchError("health_percentage", str(e)) from e

    def is_health_empty(self, screenshot_cv: np.ndarray) -> bool:
        """Check if health bar is completely empty.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            True if health is empty, False otherwise
        """
        empty_template = self.template_manager.get_empty_health_template()

        if empty_template is None:
            # Fallback to percentage-based detection
            health_percent = self.get_health_percentage(screenshot_cv)
            is_empty = health_percent <= 0.01  # Less than 1%

            if self.debug_mode and is_empty:
                logger.debug(f"Health extremely low ({health_percent:.2%}), treating as empty")

            return is_empty

        # Use template matching for empty health detection
        try:
            result = cv2.matchTemplate(screenshot_cv, empty_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            is_empty = max_val > EMPTY_HEALTH_CONFIDENCE

            if self.debug_mode and is_empty:
                logger.debug(f"Empty health bar detected with confidence: {max_val:.3f}")

            return is_empty

        except Exception as e:
            if self.debug_mode:
                logger.debug(f"Error in empty health detection: {e}")
            return False

    def _match_health_template(self, screen_image: np.ndarray) -> float:
        """Match current screen with health bar templates.

        Args:
            screen_image: OpenCV image array

        Returns:
            Health percentage as float (0.0 to 1.0)
        """
        if self.debug_mode:
            logger.debug(f"Screen image shape: {screen_image.shape}")

        # Convert to grayscale for template matching
        screen_gray = self._prepare_image_for_matching(screen_image)

        best_match = None
        best_score = 0.0
        all_scores = {}

        # Test all health templates
        health_templates = self.template_manager.get_all_health_templates()

        for percentage, template in health_templates.items():
            score = self._match_single_template(screen_gray, template, percentage)
            all_scores[percentage] = score

            if score > best_score and score > MIN_TEMPLATE_CONFIDENCE:
                best_score = score
                best_match = percentage

        if self.debug_mode:
            logger.debug(f"All match scores: {all_scores}")
            logger.debug(f"Best match: {best_match} with score {best_score:.4f}")

        # Convert to percentage
        return self._convert_match_to_percentage(best_match, best_score)

    def _prepare_image_for_matching(self, image: np.ndarray) -> np.ndarray:
        """Prepare image for template matching.

        Args:
            image: Input image array

        Returns:
            Grayscale image ready for matching
        """
        if len(image.shape) == 3:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if self.debug_mode:
                logger.debug(f"Converted to grayscale, shape: {gray_image.shape}")
            return gray_image

        if self.debug_mode:
            logger.debug(f"Already grayscale, shape: {image.shape}")
        return image

    def _match_single_template(
        self, screen_gray: np.ndarray, template: np.ndarray, percentage: str
    ) -> float:
        """Match a single template against the screen.

        Args:
            screen_gray: Grayscale screen image
            template: Template to match
            percentage: Template percentage for logging

        Returns:
            Match confidence score
        """
        try:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if self.debug_mode:
                logger.debug(f"Template {percentage}% score: {max_val:.4f} at location {max_loc}")

            return max_val

        except Exception as e:
            if self.debug_mode:
                logger.error(f"Template matching failed for {percentage}%: {e}")
            return 0.0

    def _convert_match_to_percentage(self, best_match: str | None, best_score: float) -> float:
        """Convert template match result to health percentage.

        Args:
            best_match: Name of best matching template
            best_score: Confidence score of best match

        Returns:
            Health percentage as float
        """
        if best_score < MIN_TEMPLATE_CONFIDENCE:
            if self.debug_mode:
                logger.warning(
                    f"Best match score {best_score:.4f} below threshold "
                    f"{MIN_TEMPLATE_CONFIDENCE}, defaulting to full health"
                )
            return 1.0

        if best_match == "full":
            return 1.0
        elif best_match == "empty":
            return 0.0
        elif best_match in ["20", "40", "50", "70", "90"]:
            return int(best_match) / 100.0
        else:
            if self.debug_mode:
                logger.warning("No good template match found, defaulting to full health")
            return 1.0
