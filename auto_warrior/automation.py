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

import numpy as np
import pyautogui

from auto_warrior.constants import (
    AUTOMATION_LOOP_DELAY,
    DEBUG_SCREENSHOT_NAME,
    DEFAULT_HEALTH_THRESHOLD,
    ERROR_MESSAGES,
    POST_RESPAWN_HEAL_DURATION,
    PYAUTOGUI_FAILSAFE,
    PYAUTOGUI_PAUSE,
    RESPAWN_FAILURE_MESSAGE,
    RESPAWN_MAX_ATTEMPTS,
    RESPAWN_RETRY_DELAYS,
    RESPAWN_WAIT_DURATION,
    SUCCESS_MESSAGES,
)
from auto_warrior.exceptions import AutoSnakeError
from auto_warrior.input_control import AutomationController, ClickController, InputController
from auto_warrior.potion import PotionManager
from auto_warrior.screenshot import ScreenshotManager
from auto_warrior.templates import TemplateManager
from auto_warrior.health import HealthDetector
from auto_warrior.respawn import RespawnDetector

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AutomationState:
    """State management for automation system."""

    # Health monitoring
    empty_health_detected: bool = False
    empty_health_count: int = 0
    last_empty_health_message: float = 0.0

    # Respawn system
    is_dead: bool = False
    respawn_wait_start: float | None = None
    post_respawn_heal_time: float | None = None
    respawn_attempt_count: int = 0
    respawn_last_attempt_time: float | None = None

    # Loop control
    automation_running: bool = False
    loop_count: int = 0


class GameAutomation:
    """Main automation class for game health monitoring and respawn management."""

    def __init__(
        self,
        debug_mode: bool = False,
        images_path: Path | str | None = None,
        health_threshold: float = DEFAULT_HEALTH_THRESHOLD,
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

    def _initialize_components(
        self, images_path: Path | str | None, health_threshold: float
    ) -> None:
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
            self.template_manager, self.click_controller, self.debug_mode
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
            print(
                f"🩹 Post-respawn healing phase ({elapsed_heal_time:.1f}s/{POST_RESPAWN_HEAL_DURATION}s)"
            )
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
            logger.debug(
                f"DEBUG: current_time={current_time}, respawn_wait_start={self.state.respawn_wait_start}"
            )
            logger.debug(
                f"DEBUG: elapsed_wait_time={elapsed_wait_time}, RESPAWN_WAIT_DURATION={RESPAWN_WAIT_DURATION}"
            )

        if elapsed_wait_time < RESPAWN_WAIT_DURATION:
            remaining_time = RESPAWN_WAIT_DURATION - elapsed_wait_time
            print(f"⏳ Respawn wait: {remaining_time:.1f}s remaining (ensuring game stability)")
            time.sleep(1.0)
            return True
        else:
            print(
                f"✅ Respawn wait completed ({RESPAWN_WAIT_DURATION}s) - attempting to click respawn button..."
            )
            return self._attempt_respawn_click(current_time)

    def _attempt_respawn_click(self, current_time: float) -> bool:
        """Attempt to click respawn button with retry logic.

        Args:
            current_time: Current timestamp

        Returns:
            True if respawn handling continues, False if automation should stop
        """
        print(
            f"🔍 DEBUG: _attempt_respawn_click called, current attempt count: {self.state.respawn_attempt_count}"
        )
        try:
            # Check if we need to wait between retry attempts
            if (
                self.state.respawn_last_attempt_time is not None
                and self.state.respawn_attempt_count > 0
                and self.state.respawn_attempt_count < len(RESPAWN_RETRY_DELAYS)
            ):
                delay_index = self.state.respawn_attempt_count - 1
                required_delay = RESPAWN_RETRY_DELAYS[delay_index]
                elapsed_since_last = current_time - self.state.respawn_last_attempt_time

                if elapsed_since_last < required_delay:
                    remaining_delay = required_delay - elapsed_since_last
                    print(
                        f"⏳ Waiting {remaining_delay:.1f}s before respawn attempt #{self.state.respawn_attempt_count + 1}"
                    )
                    time.sleep(1.0)
                    return True

            # Check if we've exceeded maximum attempts
            if self.state.respawn_attempt_count >= RESPAWN_MAX_ATTEMPTS:
                print(
                    f"🔍 DEBUG: Max attempts reached ({self.state.respawn_attempt_count} >= {RESPAWN_MAX_ATTEMPTS})"
                )
                print(RESPAWN_FAILURE_MESSAGE)
                print("🛑 Automation stopped. Please check the game and restart when ready.")
                self.state.automation_running = False
                return False

            # Increment attempt counter and record time
            self.state.respawn_attempt_count += 1
            self.state.respawn_last_attempt_time = current_time

            print(f"🔍 DEBUG: Incremented attempt count to {self.state.respawn_attempt_count}")
            print(f"🔄 Respawn attempt #{self.state.respawn_attempt_count}/{RESPAWN_MAX_ATTEMPTS}")

            # Take screenshot and convert to OpenCV format
            screenshot = self.screenshot_manager.take_screenshot()
            screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)

            # Try to click respawn button
            button_clicked = self.respawn_detector.click_respawn_button(screenshot_cv)

            if button_clicked:
                print("🔄 Respawn button click attempted, verifying effectiveness...")
                # Wait a moment for the click to take effect
                time.sleep(2.0)

                # Take another screenshot to verify if respawn was successful
                verify_screenshot = self.screenshot_manager.take_screenshot()
                verify_screenshot_cv = self.screenshot_manager.screenshot_to_cv2(verify_screenshot)

                # Check if respawn button is still visible (indicates click failed/game frozen)
                button_still_visible, _ = self.respawn_detector.detect_respawn_button(
                    verify_screenshot_cv
                )

                if not button_still_visible:
                    print(
                        "🎯 Respawn successful! Button disappeared - starting post-respawn healing..."
                    )
                    # Reset respawn attempt tracking on success
                    self.state.respawn_attempt_count = 0
                    self.state.respawn_last_attempt_time = None
                    self.state.respawn_wait_start = None
                    self.state.is_dead = False
                    self.state.empty_health_detected = False
                    self.state.post_respawn_heal_time = current_time
                    return True
                else:
                    print(
                        f"❌ Respawn attempt #{self.state.respawn_attempt_count} failed - button still visible (game may be frozen)"
                    )
            else:
                print(
                    f"❌ Respawn attempt #{self.state.respawn_attempt_count} failed - button not found"
                )

            # Handle failed attempt
            if self.state.respawn_attempt_count < RESPAWN_MAX_ATTEMPTS:
                delay_index = self.state.respawn_attempt_count - 1
                next_delay = (
                    RESPAWN_RETRY_DELAYS[delay_index]
                    if delay_index < len(RESPAWN_RETRY_DELAYS)
                    else RESPAWN_RETRY_DELAYS[-1]
                )
                print(f"⏳ Will retry in {next_delay}s...")
                return True
            else:
                print(f"❌ All {RESPAWN_MAX_ATTEMPTS} respawn attempts failed!")
                print(RESPAWN_FAILURE_MESSAGE)
                print("🛑 Automation stopped. Please check the game and restart when ready.")
                self.state.automation_running = False
                return False

        except Exception as e:
            logger.error(f"Error during respawn attempt #{self.state.respawn_attempt_count}: {e}")
            print(f"⚠️ Exception during respawn attempt #{self.state.respawn_attempt_count}")
            if self.state.respawn_attempt_count < RESPAWN_MAX_ATTEMPTS:
                delay_index = self.state.respawn_attempt_count - 1
                next_delay = (
                    RESPAWN_RETRY_DELAYS[delay_index]
                    if delay_index < len(RESPAWN_RETRY_DELAYS)
                    else RESPAWN_RETRY_DELAYS[-1]
                )
                print(f"⏳ Will retry in {next_delay}s due to exception...")
                return True
            else:
                print(
                    f"❌ Exception occurred and maximum attempts ({RESPAWN_MAX_ATTEMPTS}) reached!"
                )
                print(RESPAWN_FAILURE_MESSAGE)
                print("🛑 Automation stopped. Please check the game and restart when ready.")
                self.state.automation_running = False
                return False

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

            # Normal health monitoring - get health percentage and use potions if needed
            health_percent = self.health_detector.get_health_percentage(screenshot_cv)
            potion_result = self.potion_manager.use_health_potion(
                health_percent
            )

            # Handle recovery from previous emergency/death states
            if (
                self.state.empty_health_detected
            ) and health_percent > 0.1:
                print(
                    f"🎉 Character has recovered! Health: {health_percent:.1%} - returning to normal monitoring"
                )
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
        """Handle empty health detection .

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            True to continue special handling
        """
        if not self.state.is_dead:
            print("⚠️  " + ERROR_MESSAGES["empty_health_detected"])

            self.state.empty_health_detected = True

        return True

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

            current_time = time.time()

            # Always wait the full respawn duration - this is required for game stability
            self.state.respawn_wait_start = current_time

            if self.debug_mode:
                logger.debug(f"DEBUG: respawn_wait_start set to {current_time}")
                logger.debug(f"DEBUG: RESPAWN_WAIT_DURATION = {RESPAWN_WAIT_DURATION}")

            # Check for respawn button availability for informational purposes
            button_found, _ = self.respawn_detector.detect_respawn_button(screenshot_cv)

            if button_found:
                print(
                    f"🔄 Respawn button detected! Waiting {RESPAWN_WAIT_DURATION}s before clicking..."
                )
                print("   This delay ensures the game is ready for respawn interaction.")
            else:
                print(
                    f"⏳ Starting respawn wait timer ({RESPAWN_WAIT_DURATION}s) - button will be checked later"
                )
                print("   Games need time to process death state before respawn is available.")

        time.sleep(1.0)
        return True


    def _handle_health_recovery(self) -> None:
        """Handle recovery from empty health state."""
        print(SUCCESS_MESSAGES["health_restored"])
        self.state.empty_health_detected = False
        self.state.empty_health_count = 0
        self.state.last_empty_health_message = 0
        self.state.is_dead = False
        self.state.respawn_wait_start = None
        self.state.post_respawn_heal_time = None

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
