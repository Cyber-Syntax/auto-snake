"""Core automation module for game health monitoring and respawn management.

This module contains the main GameAutomation class that orchestrates
health monitoring, potion usage, respawn detection, and other automation
features using a modular architecture.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pyautogui

from auto_warrior.constants import (
    AUTOMATION_LOOP_DELAY,
    CLICK_RESPAWN_DELAY,
    CRITICAL_HEALTH_THRESHOLD,
    DEBUG_SCREENSHOT_NAME,
    DEFAULT_HEALTH_THRESHOLD,
    EMERGENCY_HEALING_MAX_ATTEMPTS,
    EMERGENCY_HEALING_TIMEOUT,
    EMERGENCY_HEALING_WAIT,
    EMPTY_HEALTH_CONFIDENCE,
    ERROR_MESSAGES,
    LOW_HEALTH_THRESHOLD,
    MAIN_LOOP_DELAY,
    MIN_TEMPLATE_CONFIDENCE,
    MULTIPLE_POTION_DELAY,
    POST_RESPAWN_HEAL_DURATION,
    POST_RESPAWN_POTION_DELAY,
    POST_RESPAWN_WAIT,
    POTION_EFFECT_WAIT,
    POTION_USAGE_MAP,
    PYAUTOGUI_FAILSAFE,
    PYAUTOGUI_PAUSE,
    RESPAWN_BUTTON_CONFIDENCE,
    RESPAWN_WAIT_DURATION,
    SUCCESS_MESSAGES,
)
from auto_warrior.exceptions import AutoSnakeError, TemplateMatchError
from auto_warrior.input_control import AutomationController, ClickController, InputController
from auto_warrior.screenshot import ScreenshotManager
from auto_warrior.templates import TemplateManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AutomationState:
    """State management for automation system."""
    
    # Health monitoring
    empty_health_detected: bool = False
    empty_health_count: int = 0
    last_empty_health_message: float = 0.0
    
    # Emergency healing system (for death detection)
    emergency_healing_active: bool = False
    emergency_healing_attempts: int = 0
    emergency_healing_start_time: float | None = None
    
    # Respawn system
    is_dead: bool = False
    respawn_wait_start: float | None = None
    post_respawn_heal_time: float | None = None
    
    # Loop control
    automation_running: bool = False
    loop_count: int = 0


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
        
    def _match_single_template(self, screen_gray: np.ndarray, template: np.ndarray, percentage: str) -> float:
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
        elif best_match in ["20", "40", "50"]:
            return int(best_match) / 100.0
        else:
            if self.debug_mode:
                logger.warning("No good template match found, defaulting to full health")
            return 1.0


class RespawnDetector:
    """Handles respawn button detection and clicking."""
    
    def __init__(self, template_manager: TemplateManager, click_controller: ClickController, debug_mode: bool = False) -> None:
        """Initialize respawn detector.
        
        Args:
            template_manager: Template manager instance
            click_controller: Click controller for button clicking
            debug_mode: Whether to enable debug logging
        """
        self.template_manager = template_manager
        self.click_controller = click_controller
        self.debug_mode = debug_mode
        
    def detect_respawn_button(self, screenshot_cv: np.ndarray) -> tuple[bool, tuple[int, int] | None]:
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
        button_found, button_pos = self.detect_respawn_button(screenshot_cv)
        
        if button_found and button_pos:
            print(f"🔄 Clicking respawn button at position {button_pos}")
            self.click_controller.click_at_position(
                button_pos[0], 
                button_pos[1], 
                CLICK_RESPAWN_DELAY
            )
            return True
            
        return False


class PotionManager:
    """Manages potion usage based on health levels."""
    
    def __init__(self, input_controller: InputController, debug_mode: bool = False) -> None:
        """Initialize potion manager.
        
        Args:
            input_controller: Input controller for key presses
            debug_mode: Whether to enable debug logging
        """
        self.input_controller = input_controller
        self.debug_mode = debug_mode
        self.health_threshold = DEFAULT_HEALTH_THRESHOLD
        
    def use_health_potion(self, health_percent: float, force_heal: bool = False, emergency_mode: bool = False) -> bool | str:
        """Use health potion based on health percentage.
        
        Args:
            health_percent: Current health percentage (0.0 to 1.0)
            force_heal: Whether to force healing (post-respawn)
            emergency_mode: Whether this is emergency healing (don't return "empty")
            
        Returns:
            True if potions were used, False if not needed, "empty" if health is empty (non-emergency only)
        """
        if self.debug_mode:
            logger.debug(f"Checking health status: {health_percent:.2%} (emergency: {emergency_mode})")
            
        if force_heal:
            return self._force_heal()
            
        # Check if health is effectively empty - but not during emergency mode
        if health_percent <= 0.01 and not emergency_mode:
            return "empty"
            
        # Determine potion usage
        potions_needed = self._calculate_potions_needed(health_percent)
        
        # In emergency mode, always use at least some potions if health is very low
        if emergency_mode and health_percent <= 0.05 and potions_needed == 0:
            potions_needed = POTION_USAGE_MAP["emergency"]
            if self.debug_mode:
                logger.debug(f"Emergency mode: forcing {potions_needed} potions for critical health")
        
        if potions_needed > 0:
            return self._use_multiple_potions(potions_needed, health_percent)
            
        if self.debug_mode:
            logger.debug(f"Health {health_percent:.2%} > {self.health_threshold:.2%}, no potion needed")
            
        return False
        
    def _force_heal(self) -> bool:
        """Force healing mode for post-respawn.
        
        Returns:
            True indicating potions were used
        """
        potions_to_use = POTION_USAGE_MAP["post_respawn"]
        print(f"Post-respawn healing: Using {potions_to_use} health potion(s)...")
        
        for i in range(potions_to_use):
            if self.debug_mode:
                logger.debug(f"Pressing potion {i+1}/{potions_to_use}")
                
            self.input_controller.press_health_potion()
            
            if i < potions_to_use - 1:
                time.sleep(POST_RESPAWN_POTION_DELAY)
                
        time.sleep(POST_RESPAWN_WAIT)
        
        if self.debug_mode:
            logger.debug(f"Finished post-respawn healing with {potions_to_use} potion(s)")
            
        return True
        
    def _calculate_potions_needed(self, health_percent: float) -> int:
        """Calculate number of potions needed based on health level.
        
        Args:
            health_percent: Current health percentage
            
        Returns:
            Number of potions to use
        """
        if health_percent <= CRITICAL_HEALTH_THRESHOLD:
            if self.debug_mode:
                logger.debug(f"Critical health ({health_percent:.2%}) - using 4 potions")
            return POTION_USAGE_MAP["critical"]
            
        elif health_percent <= LOW_HEALTH_THRESHOLD:
            if self.debug_mode:
                logger.debug(f"Low health ({health_percent:.2%}) - using 2 potions")
            return POTION_USAGE_MAP["low"]
            
        elif health_percent <= self.health_threshold:
            if self.debug_mode:
                logger.debug(f"Medium health ({health_percent:.2%}) - using 1 potion")
            return POTION_USAGE_MAP["medium"]
            
        return 0
        
    def _use_multiple_potions(self, potions_needed: int, health_percent: float) -> bool:
        """Use multiple health potions.
        
        Args:
            potions_needed: Number of potions to use
            health_percent: Current health percentage for logging
            
        Returns:
            True indicating potions were used
        """
        print(f"Using {potions_needed} health potion(s) (Health: {health_percent:.2%})...")
        
        for i in range(potions_needed):
            if self.debug_mode:
                logger.debug(f"Pressing potion {i+1}/{potions_needed}")
                
            self.input_controller.press_health_potion()
            
            if i < potions_needed - 1:
                time.sleep(MULTIPLE_POTION_DELAY)
                
        time.sleep(POTION_EFFECT_WAIT)
        
        if self.debug_mode:
            logger.debug(f"Finished using {potions_needed} potion(s)")
            
        return True
        
    def use_emergency_potions(self) -> bool:
        """Use emergency potions when health is critically low before confirming death.
        
        This method is called when empty health is detected to give the character
        a chance to recover before confirming death status.
        
        Returns:
            True indicating emergency potions were used
        """
        potions_to_use = POTION_USAGE_MAP["emergency"]
        print(f"⚡ Emergency healing: Using {potions_to_use} health potion(s) before death check...")
        
        for i in range(potions_to_use):
            if self.debug_mode:
                logger.debug(f"Emergency potion {i+1}/{potions_to_use}")
                
            self.input_controller.press_health_potion()
            
            if i < potions_to_use - 1:
                time.sleep(MULTIPLE_POTION_DELAY)
                
        # Wait for potions to take effect before checking results
        print(f"⏳ Waiting {EMERGENCY_HEALING_WAIT}s for emergency potions to take effect...")
        time.sleep(EMERGENCY_HEALING_WAIT)
        
        if self.debug_mode:
            logger.debug(f"Finished emergency healing with {potions_to_use} potion(s)")
            
        return True
    
    def set_health_threshold(self, threshold: float) -> None:
        """Set the health threshold for potion usage.
        
        Args:
            threshold: Health threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Health threshold must be between 0.0 and 1.0, got {threshold}")
            
        self.health_threshold = threshold
        
        if self.debug_mode:
            logger.debug(f"Health threshold set to: {threshold:.2%}")


class GameAutomation:
    """Main automation class for game health monitoring and respawn management."""
    
    def __init__(
        self, 
        debug_mode: bool = False, 
        images_path: Path | str | None = None,
        health_threshold: float = DEFAULT_HEALTH_THRESHOLD
    ) -> None:
        """Initialize the game automation system.
        
        Args:
            debug_mode: Whether to enable debug mode for detailed logging
            images_path: Path to directory containing template images
            health_threshold: Health percentage threshold for potion usage
        """
        self.debug_mode = debug_mode
        self.state = AutomationState()
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE
        pyautogui.PAUSE = PYAUTOGUI_PAUSE
        
        # Initialize components
        self._initialize_components(images_path, health_threshold)
        
        if self.debug_mode:
            logger.debug("GameAutomation initialized successfully")
            
    def _initialize_components(self, images_path: Path | str | None, health_threshold: float) -> None:
        """Initialize all automation components.
        
        Args:
            images_path: Path to template images
            health_threshold: Health threshold for potions
        """
        # Core components
        self.screenshot_manager = ScreenshotManager(self.debug_mode)
        self.template_manager = TemplateManager(images_path, self.debug_mode)
        self.input_controller = InputController(self.debug_mode)
        self.click_controller = ClickController(self.debug_mode)
        self.automation_controller = AutomationController(self.debug_mode)
        
        # Specialized components
        self.health_detector = HealthDetector(self.template_manager, self.debug_mode)
        self.respawn_detector = RespawnDetector(
            self.template_manager, 
            self.click_controller, 
            self.debug_mode
        )
        self.potion_manager = PotionManager(self.input_controller, self.debug_mode)
        self.potion_manager.set_health_threshold(health_threshold)
        
        # Load templates
        try:
            self.template_manager.load_all_templates()
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            raise AutoSnakeError("Template loading failed", str(e)) from e
            
    def run_automation(self) -> None:
        """Main automation loop with respawn system."""
        print(SUCCESS_MESSAGES["automation_started"])
        self._print_automation_info()
        
        # Set up automation control
        self.state.automation_running = True
        self.automation_controller.set_automation_running(True)
        
        try:
            self._automation_loop()
        except KeyboardInterrupt:
            print("Automation stopped by user")
        except Exception as e:
            logger.error(f"Automation loop failed: {e}")
            raise AutoSnakeError("Automation failed", str(e)) from e
        finally:
            self.state.automation_running = False
            
    def _automation_loop(self) -> None:
        """Main automation loop implementation."""
        while self.state.automation_running and self.automation_controller.is_automation_running():
            self.state.loop_count += 1
            
            if self.debug_mode:
                logger.debug(f"Automation loop #{self.state.loop_count}")
                
            current_time = time.time()
            
            # Handle different automation phases
            if self._handle_post_respawn_healing(current_time):
                continue
                
            if self._handle_respawn_waiting(current_time):
                continue
                
            # Normal health monitoring
            if self._handle_health_monitoring():
                continue
                
            # Standard loop delay
            time.sleep(AUTOMATION_LOOP_DELAY)
            
    def _handle_post_respawn_healing(self, current_time: float) -> bool:
        """Handle post-respawn healing phase.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if in healing phase, False otherwise
        """
        if self.state.post_respawn_heal_time is None:
            return False
            
        elapsed_heal_time = current_time - self.state.post_respawn_heal_time
        
        if elapsed_heal_time < POST_RESPAWN_HEAL_DURATION:
            print(f"🩹 Post-respawn healing phase ({elapsed_heal_time:.1f}s/{POST_RESPAWN_HEAL_DURATION}s)")
            self.potion_manager.use_health_potion(0.0, force_heal=True)
            time.sleep(1.0)
            return True
        else:
            print("✅ Post-respawn healing completed - resuming normal monitoring")
            self.state.post_respawn_heal_time = None
            return False
            
    def _handle_respawn_waiting(self, current_time: float) -> bool:
        """Handle respawn waiting phase.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if in waiting phase, False otherwise
        """
        if self.state.respawn_wait_start is None:
            return False
            
        elapsed_wait_time = current_time - self.state.respawn_wait_start
        
        if self.debug_mode:
            logger.debug(f"DEBUG: current_time={current_time}, respawn_wait_start={self.state.respawn_wait_start}")
            logger.debug(f"DEBUG: elapsed_wait_time={elapsed_wait_time}, RESPAWN_WAIT_DURATION={RESPAWN_WAIT_DURATION}")
        
        if elapsed_wait_time < RESPAWN_WAIT_DURATION:
            remaining_time = RESPAWN_WAIT_DURATION - elapsed_wait_time
            print(f"⏳ Respawn wait: {remaining_time:.1f}s remaining (ensuring game stability)")
            time.sleep(1.0)
            return True
        else:
            print(f"✅ Respawn wait completed ({RESPAWN_WAIT_DURATION}s) - attempting to click respawn button...")
            return self._attempt_respawn_click(current_time)
            
    def _attempt_respawn_click(self, current_time: float) -> bool:
        """Attempt to click respawn button.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if respawn handling continues, False if normal loop should resume
        """
        try:
            screenshot = self.screenshot_manager.take_screenshot()
            screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)
            
            if self.respawn_detector.click_respawn_button(screenshot_cv):
                print("🎯 Respawn button clicked! Starting post-respawn healing...")
                self.state.respawn_wait_start = None
                self.state.is_dead = False
                self.state.empty_health_detected = False
                self.state.post_respawn_heal_time = current_time
                return True
            else:
                print("❌ Respawn button not found, extending wait...")
                self.state.respawn_wait_start = current_time  # Reset wait timer
                return True
                
        except Exception as e:
            logger.error(f"Error during respawn attempt: {e}")
            self.state.respawn_wait_start = current_time  # Reset wait timer
            return True
            
    def _handle_health_monitoring(self) -> bool:
        """Handle normal health monitoring and potion usage.
        
        Returns:
            True if special handling occurred, False for normal loop
        """
        try:
            # Take screenshot and analyze health
            screenshot = self.screenshot_manager.take_screenshot()
            screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)
            
            # Save debug screenshot if enabled
            if self.debug_mode:
                self.screenshot_manager.save_debug_screenshot(screenshot, DEBUG_SCREENSHOT_NAME)
            
            # Handle emergency healing phase if active
            if self.state.emergency_healing_active:
                return self._handle_emergency_healing_phase(screenshot_cv)
                
            # Check for empty health and trigger emergency healing
            if self.health_detector.is_health_empty(screenshot_cv):
                return self._handle_empty_health_detection(screenshot_cv)
                
            # Normal health monitoring - get health percentage and use potions if needed
            health_percent = self.health_detector.get_health_percentage(screenshot_cv)
            potion_result = self.potion_manager.use_health_potion(health_percent, emergency_mode=False)
            
            # Handle recovery from previous emergency/death states
            if (self.state.empty_health_detected or self.state.emergency_healing_active) and health_percent > 0.1:
                print(f"🎉 Character has recovered! Health: {health_percent:.1%} - returning to normal monitoring")
                self._handle_health_recovery()
                return False  # Exit to restart normal monitoring
                
            if self.debug_mode:
                if potion_result:
                    logger.debug("Health potion was used")
                else:
                    logger.debug("No health potion needed")
                    
            return False
            
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")
            return False
            
    def _handle_empty_health_detection(self, screenshot_cv: np.ndarray) -> bool:
        """Handle empty health detection - start emergency healing before confirming death.
        
        Args:
            screenshot_cv: OpenCV screenshot array
            
        Returns:
            True to continue special handling
        """
        if not self.state.emergency_healing_active and not self.state.is_dead:
            print("⚠️  " + ERROR_MESSAGES["empty_health_detected"])
            
            # Start emergency healing phase
            self.state.emergency_healing_active = True
            self.state.emergency_healing_attempts = 1
            self.state.emergency_healing_start_time = time.time()
            self.state.empty_health_detected = True
            
            # Use emergency potions immediately
            self.potion_manager.use_emergency_potions()
            
            if self.debug_mode:
                logger.debug(SUCCESS_MESSAGES["emergency_healing_started"])
                
        return True
        
    def _handle_emergency_healing_phase(self, screenshot_cv: np.ndarray) -> bool:
        """Handle the emergency healing phase after empty health detection.
        
        Args:
            screenshot_cv: OpenCV screenshot array
            
        Returns:
            True to continue emergency handling, False if resolved
        """
        current_time = time.time()
        
        # Check if emergency healing has timed out
        if (self.state.emergency_healing_start_time and 
            current_time - self.state.emergency_healing_start_time > EMERGENCY_HEALING_TIMEOUT):
            print("⏰ " + ERROR_MESSAGES["emergency_healing_timeout"])
            return self._confirm_character_death(screenshot_cv)
        
        # Check if we've exceeded max attempts
        if self.state.emergency_healing_attempts >= EMERGENCY_HEALING_MAX_ATTEMPTS:
            print(f"💊 {ERROR_MESSAGES['max_emergency_attempts']} ({EMERGENCY_HEALING_MAX_ATTEMPTS})")
            return self._confirm_character_death(screenshot_cv)
        
        # Wait a moment for potions to take effect, then check health again
        time.sleep(1.0)
        
        # Re-check health after emergency potions
        health_percent = self.health_detector.get_health_percentage(screenshot_cv)
        is_still_empty = self.health_detector.is_health_empty(screenshot_cv)
        
        if self.debug_mode:
            logger.debug(f"Emergency healing check: health={health_percent:.2%}, empty={is_still_empty}, attempt={self.state.emergency_healing_attempts}")
        
        print(f"🔍 Health check after emergency potions: {health_percent:.1%} ({'Empty' if is_still_empty else 'Detected'})")
        
        if not is_still_empty and health_percent > 0.05:  # Health recovered (>5%)
            print(f"✅ {SUCCESS_MESSAGES['emergency_healing_success']} Health now at {health_percent:.1%}")
            self._reset_emergency_healing_state()
            return False  # Return to normal monitoring
        
        # Still empty health - check for respawn button to confirm death
        button_found, _ = self.respawn_detector.detect_respawn_button(screenshot_cv)
        
        if button_found:
            print("🔄 Respawn button detected - character is confirmed dead!")
            return self._confirm_character_death(screenshot_cv)
        
        # No respawn button yet - try emergency healing again if attempts remaining
        if self.state.emergency_healing_attempts < EMERGENCY_HEALING_MAX_ATTEMPTS:
            self.state.emergency_healing_attempts += 1
            print(f"💊 Emergency healing attempt {self.state.emergency_healing_attempts}/{EMERGENCY_HEALING_MAX_ATTEMPTS} - health still critical")
            self.potion_manager.use_emergency_potions()
            return True
        
        # Max attempts reached but no respawn button - assume death
        print("⚠️  Max emergency attempts reached and no respawn button visible - assuming character death")
        return self._confirm_character_death(screenshot_cv)
    
    def _confirm_character_death(self, screenshot_cv: np.ndarray) -> bool:
        """Confirm character death and start respawn sequence.
        
        Args:
            screenshot_cv: OpenCV screenshot array
            
        Returns:
            True to continue death handling
        """
        if not self.state.is_dead:
            print("💀 " + SUCCESS_MESSAGES["death_confirmed"])
            self.state.is_dead = True
            self._reset_emergency_healing_state()
            
            current_time = time.time()
            
            # Always wait the full respawn duration - this is required for game stability
            self.state.respawn_wait_start = current_time
            
            if self.debug_mode:
                logger.debug(f"DEBUG: respawn_wait_start set to {current_time}")
                logger.debug(f"DEBUG: RESPAWN_WAIT_DURATION = {RESPAWN_WAIT_DURATION}")
            
            # Check for respawn button availability for informational purposes
            button_found, _ = self.respawn_detector.detect_respawn_button(screenshot_cv)
            
            if button_found:
                print(f"🔄 Respawn button detected! Waiting {RESPAWN_WAIT_DURATION}s before clicking...")
                print("   This delay ensures the game is ready for respawn interaction.")
            else:
                print(f"⏳ Starting respawn wait timer ({RESPAWN_WAIT_DURATION}s) - button will be checked later")
                print("   Games need time to process death state before respawn is available.")
                
        time.sleep(1.0)
        return True
    
    def _reset_emergency_healing_state(self) -> None:
        """Reset emergency healing state variables."""
        self.state.emergency_healing_active = False
        self.state.emergency_healing_attempts = 0
        self.state.emergency_healing_start_time = None
        
        if self.debug_mode:
            logger.debug("Emergency healing state reset")
        
    def _handle_health_recovery(self) -> None:
        """Handle recovery from empty health state."""
        print(SUCCESS_MESSAGES["health_restored"])
        self.state.empty_health_detected = False
        self.state.empty_health_count = 0
        self.state.last_empty_health_message = 0
        self.state.is_dead = False
        self.state.respawn_wait_start = None
        self.state.post_respawn_heal_time = None
        self._reset_emergency_healing_state()
        
    def _print_automation_info(self) -> None:
        """Print automation information and controls."""
        template_info = self.template_manager.get_template_info()
        key_bindings = self.input_controller.get_key_bindings()
        
        print("\nGame Automation - Health Monitoring Active")
        print("=========================================")
        print("Health bar templates loaded from images folder")
        print(f"Key {key_bindings['health_potion_key']}: Health Potion")
        print("Mana functionality: WIP (Work In Progress)")
        
        if self.debug_mode:
            print("Debug mode: ENABLED (higher CPU usage)")
        else:
            print("Debug mode: DISABLED (optimized for lower CPU usage)")
            
        print("\nFeatures:")
        print("- Smart health potion usage based on health level")
        print("- Empty health detection (stops potions when dead/incapacitated)")
        print("- Automatic revival detection and resumption")
        print("\nCommands:")
        print("- Press 'r' to start/restart automation")
        print("- Press 'q' to quit")
        
        if self.debug_mode:
            logger.debug(f"Templates loaded: {template_info['health_templates_loaded']}")
            
    def use_skill(self, skill_index: int = 0) -> None:
        """Use a skill by index.
        
        Args:
            skill_index: Index of skill to use (0-based)
        """
        self.input_controller.press_skill(skill_index)
        
    def set_health_threshold(self, threshold: float) -> None:
        """Set health threshold for potion usage.
        
        Args:
            threshold: Health threshold (0.0 to 1.0)
        """
        self.potion_manager.set_health_threshold(threshold)
        
    def get_automation_info(self) -> dict[str, Any]:
        """Get information about the automation system.
        
        Returns:
            Dictionary containing system information
        """
        return {
            "template_info": self.template_manager.get_template_info(),
            "key_bindings": self.input_controller.get_key_bindings(),
            "state": {
                "automation_running": self.state.automation_running,
                "is_dead": self.state.is_dead,
                "empty_health_detected": self.state.empty_health_detected,
                "loop_count": self.state.loop_count,
            },
            "debug_mode": self.debug_mode,
        }