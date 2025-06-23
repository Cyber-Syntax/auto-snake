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
from multiprocessing import Queue, Event, Manager, Process
import multiprocessing
import numpy as np
import pyautogui
import queue

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
from auto_warrior.health import HealthDetector
from auto_warrior.input_control import (
    AutomationController,
    ClickController,
    InputController,
)
from auto_warrior.mana import ManaDetector
from auto_warrior.potion import PotionManager
from auto_warrior.respawn import RespawnDetector
from auto_warrior.screenshot import ScreenshotManager
from auto_warrior.skills import SkillManager
from auto_warrior.templates import TemplateManager

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
    death_time: float | None = None
    respawn_wait_start: float | None = None
    post_respawn_heal_time: float | None = None
    respawn_attempt_count: int = 0
    respawn_last_attempt_time: float | None = None

    # Skills system
    last_skill_usage_time: float = 0.0
    skills_used_count: int = 0

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
        mana_threshold: float = 0.5,
    ) -> None:
        """Initialize the game automation system.

        Args:
            debug_mode: Whether to enable debug mode for detailed logging
            images_path: Path to directory containing template images
            health_threshold: Health percentage threshold for potion usage
            mana_threshold: Mana percentage threshold for potion usage
        """
        self.debug_mode = debug_mode
        self.state = AutomationState()
        self.automation_process = None  # FIX: Initialize to None
        self.command_queue = multiprocessing.Queue()
        self.status_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        
        self._health_queue = multiprocessing.Queue(maxsize=1)
        self._health_results = multiprocessing.Manager().dict({'is_empty': False, 'hp': 1.0})
        self._health_stop = multiprocessing.Event()

        self._health_proc = multiprocessing.Process(
            target=self.health_worker,
            args=(
                self._health_queue,
                self._health_results,
                self._health_stop,
                str(images_path),
                debug_mode,
            ),
            daemon=True,
        )
        self._health_proc.start()

        # Configure PyAutoGUI
        pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE
        pyautogui.PAUSE = PYAUTOGUI_PAUSE

        # Store initialization parameters
        self.init_params = {
            "debug_mode": debug_mode,
            "images_path": images_path,
            "health_threshold": health_threshold,
            "mana_threshold": mana_threshold,
        }

        # Initialize components
        # self._initialize_components(images_path, health_threshold, mana_threshold)

        if self.debug_mode:
            logger.debug("GameAutomation initialized successfully")

    @staticmethod
    def health_worker(frame_queue: Queue, result_dict: dict, stop_event: Event,
                        template_path: str, debug: bool):
        """
        Pulls frames from frame_queue, runs HealthDetector on them,
        and writes {'is_empty': bool, 'hp': float} into result_dict.
        Exits when it sees stop_event.set() or a None frame.
        """
        tm = TemplateManager(template_path, debug)
        detector = HealthDetector(tm, debug)
    
        while not stop_event.is_set():
            try:
                frame = frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
    
            if frame is None:
                break
    
            # Priority detection: empty check first
            empty = detector.is_health_empty(frame)
            hp    = detector.get_health_percentage(frame) if not empty else 0.0
    
            result_dict['is_empty'] = empty
            result_dict['hp']       = hp
    
            if debug:
                logger.debug(f"[HealthWorker] empty={empty}, hp={hp:.2%}")
    
    def _initialize_components(
        self,
        images_path: Path | str | None,
        health_threshold: float,
        mana_threshold: float,
    ) -> None:
        """Initialize all automation components.

        Args:
            images_path: Path to template images
            health_threshold: Health threshold for potions
            mana_threshold: Mana threshold for potions
        """
        # Core components
        self.screenshot_manager = ScreenshotManager(self.debug_mode)
        self.template_manager = TemplateManager(images_path, self.debug_mode)
        self.input_controller = InputController(self.debug_mode)
        self.click_controller = ClickController(self.debug_mode)
        self.automation_controller = AutomationController(self.debug_mode)

        # Specialized components
        self.health_detector = HealthDetector(self.template_manager, self.debug_mode)
        self.mana_detector = ManaDetector(self.template_manager, self.debug_mode)
        self.respawn_detector = RespawnDetector(
            self.template_manager, self.click_controller, self.debug_mode
        )
        self.potion_manager = PotionManager(self.input_controller, self.debug_mode)
        self.potion_manager.set_health_threshold(health_threshold)
        self.potion_manager.set_mana_threshold(mana_threshold)
        self.skill_manager = SkillManager(self.input_controller)

        # Load templates
        try:
            self.template_manager.load_all_templates()
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            raise AutoSnakeError("Template loading failed", str(e)) from e

    def run_automation(self) -> None:
        """Start the automation process."""
        if self.automation_process and self.automation_process.is_alive():
            print("Automation is already running")
            return

        self.stop_event.clear()
        self.automation_process = multiprocessing.Process(
            target=self._automation_worker,
            args=(
                self.command_queue,
                self.status_queue,
                self.stop_event,
                self.init_params,
            ),
        )
        self.automation_process.start()
        print(SUCCESS_MESSAGES["automation_started"])

    def stop_automation(self) -> None:
        """Stop the automation process gracefully."""
        if self.automation_process and self.automation_process.is_alive():
            self.stop_event.set()
            self.automation_process.join(timeout=5.0)
            if self.automation_process.is_alive():
                self.automation_process.terminate()
            print("Automation stopped")

    def _automation_worker(
        self,
        command_queue: multiprocessing.Queue,
        status_queue: multiprocessing.Queue,
        stop_event: multiprocessing.Event,
        init_params: dict,
    ) -> None:
        """Worker function running in separate process."""
        # Initialize components within the process
        self.state = AutomationState()
        self._initialize_components(
            init_params["images_path"],
            init_params["health_threshold"],
            init_params["mana_threshold"],
        )
        self._print_automation_info()

        try:
            self._automation_loop(command_queue, stop_event)
        except Exception as e:
            logger.error(f"Automation worker failed: {e}")
        finally:
            logger.info("Automation worker exiting")

    def _automation_loop(
        self, command_queue: multiprocessing.Queue, stop_event: multiprocessing.Event
    ) -> None:
        """Main automation loop adapted for multiprocessing."""
        self.state.automation_running = True
        self.automation_controller.set_automation_running(True)

        while not stop_event.is_set() and self.state.automation_running:
            # Process commands from queue
            self._process_commands(command_queue)

            self.state.loop_count += 1
            current_time = time.time()

            # Handle different automation phases
            if self._handle_post_respawn_healing(current_time):
                continue

            if self._handle_respawn_waiting(current_time):
                continue

            # Normal health and mana monitoring
            if self._handle_health_and_mana_monitoring():
                continue

            # Handle skill usage
            self._handle_skill_usage()

            # Standard loop delay with stop check
            self._safe_sleep(AUTOMATION_LOOP_DELAY, stop_event)

        self.state.automation_running = False

    def _process_commands(self, command_queue: multiprocessing.Queue) -> None:
        """Process commands from the main thread."""
        try:
            while not command_queue.empty():
                command, *args = command_queue.get_nowait()
                if command == "set_health_threshold":
                    self.set_health_threshold(*args)
                elif command == "set_mana_threshold":
                    self.set_mana_threshold(*args)
                elif command == "use_skill":
                    self.use_skill(*args)
                # Add other commands as needed
        except Exception as e:
            logger.error(f"Error processing commands: {e}")

    def _safe_sleep(self, duration: float, stop_event: multiprocessing.Event) -> None:
        """Sleep with periodic checks for stop signal."""
        end_time = time.time() + duration
        while time.time() < end_time and not stop_event.is_set():
            time.sleep(0.1)  # Check every 100ms

    def use_skill(self, skill_id: int) -> None:
        """Thread-safe skill usage."""
        try:
            if self.skill_manager.use_skill(skill_id):
                self.state.last_skill_usage_time = time.time()
                self.state.skills_used_count += 1
        except Exception as e:
            logger.error(f"Error using skill: {e}")

    def _handle_skill_usage(self) -> None:
        """Handle automatic skill usage based on availability and cooldowns."""
        try:
            # Get all ready skills
            ready_skills = self.skill_manager.get_ready_skills()

            if not ready_skills:
                return

            current_time = time.time()

            # Only use skills if enough time has passed since last skill usage
            # This prevents skill spam and allows for better coordination
            time_since_last_skill = current_time - self.state.last_skill_usage_time
            if time_since_last_skill < 3.0:  # 3 second minimum between skill usages
                return

            # Use available skills (prioritize by ID for consistent order)
            used_skills = []
            for skill in sorted(ready_skills, key=lambda s: s.config.id):
                if self.skill_manager.use_skill(skill.config.id):
                    used_skills.append(skill.config.id)
                    self.state.last_skill_usage_time = current_time
                    self.state.skills_used_count += 1

                    if self.debug_mode:
                        logger.debug(
                            f"Auto-used skill {skill.config.id} (key: {skill.config.key})"
                        )

                    # Only use one skill at a time to avoid conflicts
                    break

            if used_skills:
                print(f"🔥 Used skill(s): {used_skills}")

        except Exception as e:
            logger.error(f"Error in skill usage handling: {e}")

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
            print(
                f"⏳ Respawn wait: {remaining_time:.1f}s remaining (ensuring game stability)"
            )
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
                print(
                    "🛑 Automation stopped. Please check the game and restart when ready."
                )
                self.state.automation_running = False
                return False

            # Increment attempt counter and record time
            self.state.respawn_attempt_count += 1
            self.state.respawn_last_attempt_time = current_time

            print(
                f"🔍 DEBUG: Incremented attempt count to {self.state.respawn_attempt_count}"
            )
            print(
                f"🔄 Respawn attempt #{self.state.respawn_attempt_count}/{RESPAWN_MAX_ATTEMPTS}"
            )

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
                verify_screenshot_cv = self.screenshot_manager.screenshot_to_cv2(
                    verify_screenshot
                )

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
                print(
                    "🛑 Automation stopped. Please check the game and restart when ready."
                )
                self.state.automation_running = False
                return False

        except Exception as e:
            logger.error(
                f"Error during respawn attempt #{self.state.respawn_attempt_count}: {e}"
            )
            print(
                f"⚠️ Exception during respawn attempt #{self.state.respawn_attempt_count}"
            )
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
                print(
                    "🛑 Automation stopped. Please check the game and restart when ready."
                )
                self.state.automation_running = False
                return False


    
    def _handle_health_and_mana_monitoring(self) -> bool:
        """Handle normal health and mana monitoring with potion usage.

        Returns:
            True if special handling occurred, False for normal loop
        """
        try:
            # Fast screenshot capture with timing
            screenshot_start = time.time()

            #TODO: make sure using live capture?
            if self.screenshot_manager.live_capture:
                screenshot_cv = self.screenshot_manager.live_capture.capture_live()
            else:
                screenshot = self.screenshot_manager.take_screenshot()
                screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)
                
            # Save debug screenshot if enabled
            if self.debug_mode:
                self.screenshot_manager.save_debug_screenshot(
                    screenshot, DEBUG_SCREENSHOT_NAME
                )

            # Check for empty health first (critical check)
            is_empty = self.health_detector.is_health_empty(screenshot_cv)
            if self.debug_mode:
                logger.debug(f"Empty health check result: {is_empty}")

            if is_empty:
                if self.debug_mode:
                    logger.debug("Empty health detected - triggering emergency handler")
                return self._handle_empty_health_detection(screenshot_cv)

            # Skip potion usage if character is confirmed dead
            if self.state.is_dead:
                if self.debug_mode:
                    logger.debug("Character is dead - skipping health/mana monitoring")
                return True  # Continue to respawn handling

            # Get health and mana percentages
            # new async detection
            try:
                self._health_queue.put_nowait(screenshot_cv)
            except Full:
                # worker is still busy with previous frame; that's fine
                pass
            
            is_empty = self._health_results['is_empty']
            hp       = self._health_results['hp']
            
            health_percent = self.health_detector.get_health_percentage(screenshot_cv)
            if self.debug_mode:
                logger.debug(f"Health percentage: {health_percent:.2%}")

            mana_percent = self.mana_detector.get_mana_percentage(screenshot_cv)
            if self.debug_mode:
                logger.debug(f"Mana percentage: {mana_percent:.2%}")

            # Use both potions as needed
            potion_results = self.potion_manager.use_both_potions(
                health_percent, mana_percent
            )

            # Handle recovery from previous emergency/death states
            if (self.state.empty_health_detected) and health_percent > 0.1:
                print(
                    f"🎉 Character has recovered! Health: {health_percent:.1%} - returning to normal monitoring"
                )
                self._handle_health_recovery()
                return False  # Exit to restart normal monitoring

            if self.debug_mode:
                health_result = potion_results.get("health", False)
                mana_result = potion_results.get("mana", False)
                if health_result:
                    logger.debug("Health potion was used")
                if mana_result:
                    logger.debug("Mana potion was used")
                if not health_result and not mana_result:
                    logger.debug("No potions needed")

            return False

        except Exception as e:
            logger.error(f"Error in health and mana monitoring: {e}")
            return False

    def _handle_empty_health_detection(self, screenshot_cv: np.ndarray) -> bool:
        """Handle empty health detection and trigger death confirmation.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            True to continue special handling
        """
        if self.debug_mode:
            logger.debug(
                f"_handle_empty_health_detection called, is_dead={self.state.is_dead}"
            )

        if not self.state.is_dead:
            print("⚠️  " + ERROR_MESSAGES["empty_health_detected"])
            self.state.empty_health_detected = True

            if self.debug_mode:
                logger.debug("Confirming character death...")

            # Confirm character death and start respawn process
            death_confirmed = self.confirm_character_death(screenshot_cv)
            if death_confirmed:
                print("💀 Character death confirmed - starting respawn process...")
                return True
            else:
                # False alarm - reset empty health detection
                self.state.empty_health_detected = False
                print("ℹ️  False alarm - character still alive")
                if self.debug_mode:
                    logger.debug(
                        "Death confirmation failed - continuing normal monitoring"
                    )
                return False
        else:
            if self.debug_mode:
                logger.debug("Character already dead - continuing death handling")

        return True

    def confirm_character_death(self, screenshot_cv: np.ndarray) -> bool:
        """Confirm character death and start respawn sequence.

        Args:
            screenshot_cv: OpenCV screenshot array

        Returns:
            True if death confirmed, False if character still alive
        """
        # If already dead, no need to confirm again
        if self.state.is_dead:
            return True

        print("💀 " + SUCCESS_MESSAGES["death_confirmed"])
        self.state.is_dead = True
        self.state.death_time = time.time()

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
            print(
                "   Games need time to process death state before respawn is available."
            )

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
            logger.debug(
                f"Templates loaded: {template_info['health_templates_loaded']}"
            )

    def use_skill(self, skill_id: int) -> bool:
        """Use a specific skill by ID.

        Args:
            skill_id: ID of skill to use

        Returns:
            True if skill was used successfully, False otherwise
        """
        try:
            result = self.skill_manager.use_skill(skill_id)
            if result:
                self.state.last_skill_usage_time = time.time()
                self.state.skills_used_count += 1
            return result
        except Exception as e:
            logger.error(f"Error using skill {skill_id}: {e}")
            return False

    def get_skill_status(self, skill_id: int) -> dict[str, Any]:
        """Get status of a specific skill.

        Args:
            skill_id: ID of skill to check

        Returns:
            Dictionary containing skill status information
        """
        return self.skill_manager.get_skill_status(skill_id)

    def get_all_skills_status(self) -> dict[int, dict[str, Any]]:
        """Get status of all skills.

        Returns:
            Dictionary mapping skill IDs to their status information
        """
        return self.skill_manager.get_all_skills_status()

    def set_health_threshold(self, threshold: float) -> None:
        """Set health threshold for potion usage.

        Args:
            threshold: Health threshold (0.0 to 1.0)
        """
        self.potion_manager.set_health_threshold(threshold)

    def set_mana_threshold(self, threshold: float) -> None:
        """Set mana threshold for potion usage.

        Args:
            threshold: Mana threshold (0.0 to 1.0)
        """
        self.potion_manager.set_mana_threshold(threshold)

    def get_mana_status(self) -> dict[str, Any]:
        """Get current mana status.

        Returns:
            Dictionary containing mana information
        """
        try:
            screenshot = self.screenshot_manager.take_screenshot()
            screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)
            return self.mana_detector.get_mana_bar_info(screenshot_cv)
        except Exception as e:
            logger.error(f"Error getting mana status: {e}")
            return {"error": str(e)}

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
                "last_skill_usage_time": self.state.last_skill_usage_time,
                "skills_used_count": self.state.skills_used_count,
            },
            "skills_status": self.get_all_skills_status(),
            "potion_thresholds": self.potion_manager.get_thresholds(),
            "debug_mode": self.debug_mode,
        }
