"""Input control utilities for game automation.

This module provides keyboard input simulation and control functionality
for the automation system, including key press simulation and keyboard
event handling.
"""

import logging
import time
from typing import Any

import pyautogui
from pynput import keyboard as pynput_keyboard
from pynput.keyboard import Controller, Key

from auto_snake.constants import (
    DEFAULT_HEALTH_POTION_KEY,
    DEFAULT_MANA_POTION_KEY,
    DEFAULT_SKILL_KEYS,
    KEY_PRESS_DELAY,
    KEY_PRESS_DURATION,
    QUIT_KEY,
    START_KEY,
)
from auto_snake.exceptions import KeyPressError

logger = logging.getLogger(__name__)


class InputController:
    """Manages keyboard input simulation and event handling."""

    def __init__(self, debug_mode: bool = False) -> None:
        """Initialize the input controller.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.keyboard_controller = Controller()
        
        # Key bindings - can be customized
        self.health_potion_key = DEFAULT_HEALTH_POTION_KEY
        self.mana_potion_key = DEFAULT_MANA_POTION_KEY
        self.skill_keys = DEFAULT_SKILL_KEYS.copy()
        
        if self.debug_mode:
            logger.debug("InputController initialized")

    def press_key(self, key: str, duration: float = KEY_PRESS_DURATION) -> None:
        """Press and release a key after specified duration.
        
        Args:
            key: Key to press (string representation)
            duration: How long to hold the key in seconds
            
        Raises:
            KeyPressError: If key press simulation fails
        """
        if self.debug_mode:
            logger.debug(f"Pressing key '{key}' for {duration} seconds...")
            
        try:
            self.keyboard_controller.press(key)
            time.sleep(duration)
            self.keyboard_controller.release(key)
            time.sleep(KEY_PRESS_DELAY)
            
            if self.debug_mode:
                logger.debug(f"Key '{key}' pressed successfully")
                
        except Exception as e:
            error_msg = f"Failed to press key '{key}'"
            logger.error(f"{error_msg}: {e}")
            raise KeyPressError(key, str(e)) from e

    def press_health_potion(self) -> None:
        """Press the health potion key."""
        self.press_key(self.health_potion_key)

    def press_mana_potion(self) -> None:
        """Press the mana potion key."""
        self.press_key(self.mana_potion_key)

    def press_skill(self, skill_index: int = 0) -> None:
        """Press a skill key by index.
        
        Args:
            skill_index: Index of skill key to press (0-based)
            
        Raises:
            KeyPressError: If skill index is invalid
        """
        if not 0 <= skill_index < len(self.skill_keys):
            raise KeyPressError(
                f"skill_{skill_index}",
                f"Invalid skill index: {skill_index}. Available: 0-{len(self.skill_keys)-1}"
            )
            
        skill_key = self.skill_keys[skill_index]
        if self.debug_mode:
            logger.debug(f"Using skill {skill_index}: {skill_key}")
            
        self.press_key(skill_key)

    def press_skill_by_key(self, skill_key: str) -> None:
        """Press a specific skill key.
        
        Args:
            skill_key: The skill key to press
        """
        if self.debug_mode:
            logger.debug(f"Using skill key: {skill_key}")
            
        self.press_key(skill_key)

    def set_health_potion_key(self, key: str) -> None:
        """Set the health potion key binding.
        
        Args:
            key: New key for health potion
        """
        self.health_potion_key = key
        if self.debug_mode:
            logger.debug(f"Health potion key set to: {key}")

    def set_mana_potion_key(self, key: str) -> None:
        """Set the mana potion key binding.
        
        Args:
            key: New key for mana potion
        """
        self.mana_potion_key = key
        if self.debug_mode:
            logger.debug(f"Mana potion key set to: {key}")

    def set_skill_keys(self, keys: list[str]) -> None:
        """Set the skill key bindings.
        
        Args:
            keys: List of keys for skills
        """
        self.skill_keys = keys.copy()
        if self.debug_mode:
            logger.debug(f"Skill keys set to: {keys}")

    def get_key_bindings(self) -> dict[str, Any]:
        """Get current key bindings.
        
        Returns:
            Dictionary containing current key bindings
        """
        return {
            "health_potion_key": self.health_potion_key,
            "mana_potion_key": self.mana_potion_key,
            "skill_keys": self.skill_keys.copy(),
        }


class KeyboardListener:
    """Handles keyboard event listening for automation control."""

    def __init__(self, debug_mode: bool = False) -> None:
        """Initialize the keyboard listener.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.listener: pynput_keyboard.Listener | None = None
        self.callbacks: dict[str, callable] = {}
        
        if self.debug_mode:
            logger.debug("KeyboardListener initialized")

    def register_callback(self, key: str, callback: callable) -> None:
        """Register a callback for a specific key.
        
        Args:
            key: Key to listen for
            callback: Function to call when key is pressed
        """
        self.callbacks[key] = callback
        if self.debug_mode:
            logger.debug(f"Registered callback for key: {key}")

    def register_quit_callback(self, callback: callable) -> None:
        """Register callback for quit key.
        
        Args:
            callback: Function to call when quit key is pressed
        """
        self.register_callback(QUIT_KEY, callback)

    def register_start_callback(self, callback: callable) -> None:
        """Register callback for start key.
        
        Args:
            callback: Function to call when start key is pressed
        """
        self.register_callback(START_KEY, callback)

    def _on_key_press(self, key) -> bool | None:
        """Handle key press events.
        
        Args:
            key: The pressed key
            
        Returns:
            False to stop listener, None to continue
        """
        try:
            if hasattr(key, 'char') and key.char in self.callbacks:
                char = key.char
                if self.debug_mode:
                    logger.debug(f"Key '{char}' pressed, calling callback")
                    
                callback = self.callbacks[char]
                result = callback()
                
                # If callback returns False, stop the listener
                if result is False:
                    return False
                    
        except AttributeError:
            # Special keys (like ctrl, alt, etc.) don't have char attribute
            pass
        except Exception as e:
            logger.error(f"Error in key press handler: {e}")
            
        return None

    def start_listening(self) -> None:
        """Start listening for keyboard events."""
        if self.listener is not None:
            self.stop_listening()
            
        self.listener = pynput_keyboard.Listener(on_press=self._on_key_press)
        self.listener.start()
        
        if self.debug_mode:
            logger.debug("Keyboard listener started")

    def stop_listening(self) -> None:
        """Stop listening for keyboard events."""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            
        if self.debug_mode:
            logger.debug("Keyboard listener stopped")

    def wait_for_events(self) -> None:
        """Wait for keyboard events (blocking)."""
        if self.listener is not None:
            self.listener.join()


class AutomationController:
    """High-level controller for automation start/stop functionality."""

    def __init__(self, debug_mode: bool = False) -> None:
        """Initialize the automation controller.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.listener = KeyboardListener(debug_mode)
        self.automation_running = False
        self.main_running = True
        
        # Register default callbacks
        self.listener.register_quit_callback(self._on_quit)
        self.listener.register_start_callback(self._on_start_restart)
        
        if self.debug_mode:
            logger.debug("AutomationController initialized")

    def _on_quit(self) -> bool:
        """Handle quit key press.
        
        Returns:
            False to stop listener
        """
        if self.debug_mode:
            logger.debug("Quit key pressed")
        else:
            print("Quitting...")
            
        self.main_running = False
        self.automation_running = False
        return False

    def _on_start_restart(self) -> None:
        """Handle start/restart key press."""
        if not self.automation_running:
            if self.debug_mode:
                logger.debug("Start key pressed - starting automation")
            else:
                print("Starting automation...")
                
            self.automation_running = True
            # The actual automation logic should be handled by the caller
        else:
            if self.debug_mode:
                logger.debug("Start key pressed but automation already running")

    def start_listening(self) -> None:
        """Start listening for control keys."""
        self.listener.start_listening()
        print("Press 'r' to start automation, 'q' to quit")

    def stop_listening(self) -> None:
        """Stop listening for control keys."""
        self.listener.stop_listening()

    def is_automation_running(self) -> bool:
        """Check if automation should be running.
        
        Returns:
            True if automation should run, False otherwise
        """
        return self.automation_running

    def is_main_running(self) -> bool:
        """Check if main loop should continue.
        
        Returns:
            True if main should continue, False to exit
        """
        return self.main_running

    def set_automation_running(self, running: bool) -> None:
        """Set automation running state.
        
        Args:
            running: Whether automation should be running
        """
        self.automation_running = running

    def wait_for_events(self) -> None:
        """Wait for keyboard events (blocking)."""
        self.listener.wait_for_events()


class ClickController:
    """Handles mouse click operations for automation."""

    def __init__(self, debug_mode: bool = False) -> None:
        """Initialize the click controller.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        
        if self.debug_mode:
            logger.debug("ClickController initialized")

    def click_at_position(self, x: int, y: int, delay: float = 0.0) -> None:
        """Click at specific screen coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            delay: Delay after clicking in seconds
        """
        if self.debug_mode:
            logger.debug(f"Clicking at position ({x}, {y})")
            
        try:
            pyautogui.click(x, y)
            if delay > 0:
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"Failed to click at ({x}, {y}): {e}")
            raise KeyPressError(f"click_{x}_{y}", str(e)) from e

    def click_center_of_region(self, x: int, y: int, width: int, height: int, delay: float = 0.0) -> None:
        """Click at the center of a rectangular region.
        
        Args:
            x: Top-left X coordinate of region
            y: Top-left Y coordinate of region
            width: Width of region
            height: Height of region
            delay: Delay after clicking in seconds
        """
        center_x = x + width // 2
        center_y = y + height // 2
        self.click_at_position(center_x, center_y, delay)