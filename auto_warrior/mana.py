"""Mana detection module for game mana bar monitoring.

This module contains the ManaDetector class that handles mana bar detection
and analysis using template matching and color-based detection methods.
"""

import logging

import cv2
import numpy as np

from auto_warrior.constants import (
    DEFAULT_MANA_THRESHOLD,
    MANA_COLOR_RANGE_LOWER,
    MANA_COLOR_RANGE_UPPER,
    MANA_TEMPLATE_CONFIDENCE,
    MIN_TEMPLATE_CONFIDENCE,
)
from auto_warrior.exceptions import TemplateMatchError
from auto_warrior.templates import TemplateManager

logger = logging.getLogger(__name__)


class ManaDetector:
    """Handles mana bar detection and analysis."""

    def __init__(self, template_manager: TemplateManager, debug_mode: bool = False) -> None:
        """Initialize mana detector.

        Args:
            template_manager: Template manager instance
            debug_mode: Whether to enable debug logging
        """
        self.template_manager = template_manager
        self.debug_mode = debug_mode

    def get_mana_percentage(self, screenshot_cv: np.ndarray) -> float:
        """Get current mana percentage using robust template matching.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Mana percentage as float (0.0 to 1.0)

        Raises:
            TemplateMatchError: If template matching fails
        """
        if self.debug_mode:
            logger.debug("Starting mana percentage detection with robust template matching")

        # Prioritize template matching with high confidence thresholds
        if self.template_manager.has_mana_templates():
            try:
                return self._match_mana_template_robust(screenshot_cv)
            except Exception as e:
                logger.warning(f"Robust template matching failed: {e}")
                # Only fall back to basic template matching if robust fails
                try:
                    return self._match_mana_template_basic(screenshot_cv)
                except Exception as e2:
                    logger.warning(f"Basic template matching also failed: {e2}")

        # Only use color detection as last resort
        if self.debug_mode:
            logger.debug(
                "No mana templates available or all template matching failed, using color detection"
            )

        try:
            return self._detect_mana_by_color(screenshot_cv)
        except Exception as e:
            logger.error(f"All mana detection methods failed: {e}")
            # Return a safe default value (assume full mana)
            return 1.0

    def is_mana_empty(self, screenshot_cv: np.ndarray) -> bool:
        """Check if mana bar is completely empty using percentage-based detection.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            True if mana is empty, False otherwise
        """
        # Use percentage-based detection
        mana_percent = self.get_mana_percentage(screenshot_cv)
        is_empty = mana_percent <= 0.01  # Less than 1%

        if self.debug_mode and is_empty:
            logger.debug(f"Mana extremely low ({mana_percent:.2%}), treating as empty")

        return is_empty

    def _match_mana_template_robust(self, screenshot_cv: np.ndarray) -> float:
        """Match mana templates with high confidence thresholds for robust detection.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Mana percentage as float (0.0 to 1.0)

        Raises:
            TemplateMatchError: If template matching fails
        """
        mana_templates = self.template_manager.get_all_mana_templates()

        if not mana_templates:
            raise TemplateMatchError("mana_percentage", "No mana templates available")

        best_match_percentage = 0.0
        best_difference = float("inf")  # Start with worst possible difference for SQDIFF

        for percentage_str, template in mana_templates.items():
            try:
                result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_SQDIFF_NORMED)
                min_val, _, min_loc, _ = cv2.minMaxLoc(result)

                if self.debug_mode:
                    logger.debug(
                        f"Mana template {percentage_str}%: difference={min_val:.3f} at {min_loc}"
                    )

                if min_val < best_difference and min_val < MANA_TEMPLATE_CONFIDENCE:
                    best_difference = min_val
                    if percentage_str == "full":
                        best_match_percentage = 1.0
                    else:
                        best_match_percentage = int(percentage_str) / 100.0

            except Exception as e:
                logger.warning(f"Error matching mana template {percentage_str}: {e}")
                continue

        if best_difference == float("inf"):
            if self.debug_mode:
                logger.debug(
                    f"No mana templates matched with difference <= {MANA_TEMPLATE_CONFIDENCE}"
                )
            raise TemplateMatchError(
                "mana_percentage",
                f"No templates matched with difference <= {MANA_TEMPLATE_CONFIDENCE}",
            )

        if self.debug_mode:
            logger.debug(
                f"Robust mana match: {best_match_percentage:.1%} with difference {best_difference:.3f}"
            )

        return best_match_percentage

    def _match_mana_template_basic(self, screenshot_cv: np.ndarray) -> float:
        """Basic mana template matching with lower confidence threshold as fallback.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Mana percentage as float (0.0 to 1.0)

        Raises:
            TemplateMatchError: If template matching fails
        """
        mana_templates = self.template_manager.get_all_mana_templates()

        if not mana_templates:
            raise TemplateMatchError("mana_percentage", "No mana templates available")

        best_match_percentage = 0.0
        best_difference = float("inf")  # Start with worst possible difference for SQDIFF

        for percentage_str, template in mana_templates.items():
            try:
                result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_SQDIFF_NORMED)
                min_val, _, min_loc, _ = cv2.minMaxLoc(result)

                if self.debug_mode:
                    logger.debug(
                        f"Basic mana template {percentage_str}%: difference={min_val:.3f} at {min_loc}"
                    )

                if min_val < best_difference and min_val < MIN_TEMPLATE_CONFIDENCE:
                    best_difference = min_val
                    if percentage_str == "full":
                        best_match_percentage = 1.0
                    else:
                        best_match_percentage = int(percentage_str) / 100.0

            except Exception as e:
                logger.warning(f"Error matching basic mana template {percentage_str}: {e}")
                continue

        if best_difference == float("inf"):
            if self.debug_mode:
                logger.debug(
                    f"No mana templates matched with basic difference <= {MIN_TEMPLATE_CONFIDENCE}"
                )
            raise TemplateMatchError(
                "mana_percentage",
                f"No templates matched with difference <= {MIN_TEMPLATE_CONFIDENCE}",
            )

        if self.debug_mode:
            logger.debug(
                f"Basic mana match: {best_match_percentage:.1%} with difference {best_difference:.3f}"
            )

        return best_match_percentage

    def _detect_mana_by_color(self, screenshot_cv: np.ndarray) -> float:
        """Detect mana percentage using color-based analysis as fallback method.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Mana percentage as float (0.0 to 1.0)
        """
        if self.debug_mode:
            logger.debug("Using color-based mana detection (fallback method)")

        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2HSV)

        # Create mask for mana colors (typically blue)
        lower_bound = np.array(MANA_COLOR_RANGE_LOWER)
        upper_bound = np.array(MANA_COLOR_RANGE_UPPER)
        mana_mask = cv2.inRange(hsv, lower_bound, upper_bound)

        # Define mana bar region (you may need to adjust these coordinates)
        # This is a rough estimate - in a real implementation, you'd want to
        # calibrate this based on your specific game UI
        height, width = screenshot_cv.shape[:2]

        # Assume mana bar is in the top-left area (common in many games)
        mana_region_x = int(width * 0.02)  # 2% from left
        mana_region_y = int(height * 0.08)  # 8% from top
        mana_region_width = int(width * 0.15)  # 15% of screen width
        mana_region_height = int(height * 0.03)  # 3% of screen height

        # Extract mana bar region
        mana_roi = mana_mask[
            mana_region_y : mana_region_y + mana_region_height,
            mana_region_x : mana_region_x + mana_region_width,
        ]

        if mana_roi.size == 0:
            logger.warning("Mana ROI is empty, returning safe default value")
            return 1.0

        # Calculate mana percentage based on blue pixels
        total_pixels = mana_roi.size
        mana_pixels = cv2.countNonZero(mana_roi)

        if total_pixels == 0:
            mana_percentage = 1.0
        else:
            mana_percentage = mana_pixels / total_pixels

        # Clamp to reasonable bounds
        mana_percentage = max(0.0, min(1.0, mana_percentage))

        # Log warning since this is fallback method
        if self.debug_mode:
            logger.warning(
                f"Color-based mana detection (fallback): {mana_pixels}/{total_pixels} = {mana_percentage:.2%}"
            )

        return mana_percentage

    def calibrate_mana_region(self, screenshot_cv: np.ndarray) -> dict:
        """Calibrate mana bar region for better detection.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Dictionary with calibration results
        """
        if self.debug_mode:
            logger.debug("Calibrating mana bar region")

        # Convert to HSV
        hsv = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2HSV)

        # Create mask for mana colors
        lower_bound = np.array(MANA_COLOR_RANGE_LOWER)
        upper_bound = np.array(MANA_COLOR_RANGE_UPPER)
        mana_mask = cv2.inRange(hsv, lower_bound, upper_bound)

        # Find contours of mana-colored regions
        contours, _ = cv2.findContours(mana_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {"success": False, "message": "No mana-colored regions found"}

        # Find the largest contour (likely the mana bar)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        calibration_result = {
            "success": True,
            "mana_region": {"x": x, "y": y, "width": w, "height": h},
            "area": cv2.contourArea(largest_contour),
        }

        if self.debug_mode:
            logger.debug(f"Mana region calibrated: {calibration_result}")

        return calibration_result

    def get_mana_bar_info(self, screenshot_cv: np.ndarray) -> dict:
        """Get comprehensive mana bar information.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Dictionary containing mana bar analysis results
        """
        try:
            mana_percentage = self.get_mana_percentage(screenshot_cv)
            is_empty = mana_percentage <= 0.01

            # Determine mana status
            if is_empty:
                status = "empty"
            elif mana_percentage <= 0.2:
                status = "critical"
            elif mana_percentage <= 0.5:
                status = "low"
            elif mana_percentage <= 0.8:
                status = "medium"
            else:
                status = "high"

            return {
                "percentage": mana_percentage,
                "is_empty": is_empty,
                "status": status,
                "needs_potion": mana_percentage < DEFAULT_MANA_THRESHOLD,
                "detection_method": "template"
                if self.template_manager.has_mana_templates()
                else "color",
            }

        except Exception as e:
            logger.error(f"Error getting mana bar info: {e}")
            return {
                "percentage": 1.0,
                "is_empty": False,
                "status": "unknown",
                "needs_potion": False,
                "error": str(e),
            }
