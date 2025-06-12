import logging
import cv2
import numpy as np

from auto_snake.constants import (
    CLICK_RESPAWN_DELAY,
    RESPAWN_BUTTON_CONFIDENCE,
)
from auto_snake.input_control import ClickController
from auto_snake.templates import TemplateManager

logger = logging.getLogger(__name__)

class RespawnDetector:
    """Handles respawn button detection and clicking."""

    def __init__(
        self,
        template_manager: TemplateManager,
        click_controller: ClickController,
        debug_mode: bool = False,
    ) -> None:
        """Initialize respawn detector.

        Args:
            template_manager: Template manager instance
            click_controller: Click controller for button clicking
            debug_mode: Whether to enable debug logging
        """
        self.template_manager = template_manager
        self.click_controller = click_controller
        self.debug_mode = debug_mode

    def detect_respawn_button(
        self, screenshot_cv: np.ndarray
    ) -> tuple[bool, tuple[int, int] | None]:
        """Detect if respawn button is visible on screen.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            Tuple of (button_found, button_position)
        """
        respawn_template = self.template_manager.get_respawn_button_template()
        if respawn_template is None:
            return False, None

        try:
            result = cv2.matchTemplate(screenshot_cv, respawn_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > RESPAWN_BUTTON_CONFIDENCE:
                # Calculate center of the button
                h, w = respawn_template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2

                if self.debug_mode:
                    logger.debug(
                        f"Respawn button detected with confidence: {max_val:.3f} "
                        f"at ({center_x}, {center_y})"
                    )

                return True, (center_x, center_y)

            return False, None

        except Exception as e:
            if self.debug_mode:
                logger.debug(f"Error in respawn button detection: {e}")
            return False, None

    def click_respawn_button(self, screenshot_cv: np.ndarray) -> bool:
        """Click the respawn button if detected.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            True if button was found and clicked, False otherwise
        """
        import random

        button_found, button_pos = self.detect_respawn_button(screenshot_cv)

        if button_found and button_pos:
            # Get the respawn button template to calculate button dimensions
            respawn_template = self.template_manager.get_respawn_button_template()
            if respawn_template is not None:
                h, w = respawn_template.shape[:2]

                # Calculate button boundaries (top-left corner from detection)
                button_left = button_pos[0] - w // 2
                button_top = button_pos[1] - h // 2
                button_right = button_left + w
                button_bottom = button_top + h

                # Add margin to stay away from edges
                margin = 10

                click_area_left = button_left + margin
                click_area_top = button_top + margin
                click_area_right = button_right - margin
                click_area_bottom = button_bottom - margin

                # Generate random click position within the click area
                random_x = random.randint(click_area_left, click_area_right)
                random_y = random.randint(click_area_top, click_area_bottom)

                print(f"🔄 Clicking respawn button at position ({random_x}, {random_y})")
                self.click_controller.click_at_position(random_x, random_y, CLICK_RESPAWN_DELAY)
                return True
            else:
                print("❌ Respawn button not found")
                return False

        return False
