"""Configuration constants for the auto_warrior package.

This module contains all configuration constants used throughout the
automation system, including timing, thresholds, and key bindings.
"""

from pathlib import Path

# Version information
VERSION = "1.0.0"
AUTHOR = "Cyber-syntax"
LICENSE = "BSD 3-Clause License"

# File and directory paths
repo_dir = Path(__file__).parent.parent
DEFAULT_IMAGES_PATH = repo_dir / "auto_warrior/images"
HEALTH_TEMPLATE_FILES = {
    "20": "20_health_bar.png",
    "40": "40_health_bar.png",
    "50": "50_health_bar.png",
    "70": "70_health_bar.png",
    "90": "90_health_bar.png",
    "full": "full_health_bar.png",
}
EMPTY_HEALTH_TEMPLATE = "empty_health_bar.png"

# Mana template files
MANA_TEMPLATE_FILES = {
    "20": "20_mana_bar.png",
    "40": "40_mana_bar.png",
    "50": "50_mana_bar.png",
    "70": "70_mana_bar.png",
    "90": "90_mana_bar.png",
    "full": "full_mana_bar.png",
}

RESPAWN_BUTTON_TEMPLATE = "respawn_button.png"

# TODO: Delete unnecessary imports
# Some of them must be local variables

# Health monitoring thresholds
DEFAULT_HEALTH_THRESHOLD = 0.9  # Use health potion when below 90%
CRITICAL_HEALTH_THRESHOLD = 0.20  # Critical health level (20%)
LOW_HEALTH_THRESHOLD = 0.40  # Low health level (40%)
MEDIUM_HEALTH_THRESHOLD = 0.70  # Medium health level (70%)
HIGH_HEALTH_THRESHOLD = 0.9  # High health level (90%)
EMPTY_HEALTH_THRESHOLD = 0.01  # Consider health empty below 1%

# Template matching confidence thresholds (for TM_SQDIFF_NORMED: lower values = better match)
MIN_TEMPLATE_CONFIDENCE = 0.2  # Maximum difference for template matching (lower = stricter)
EMPTY_HEALTH_CONFIDENCE = (
    0.1  # Maximum difference for empty health detection (lower to reduce false positives)
)
MANA_TEMPLATE_CONFIDENCE = 0.1  # Low difference threshold for robust mana detection
RESPAWN_BUTTON_CONFIDENCE = 0.1  # Maximum difference threshold for respawn button detection

# Timing constants (in seconds)
KEY_PRESS_DURATION = 0.1  # Duration to hold key press
KEY_PRESS_DELAY = 0.1  # Delay after key release
POTION_EFFECT_WAIT = 1.5  # Wait time for potion effect
MULTIPLE_POTION_DELAY = 0.3  # Delay between multiple potion presses
POST_RESPAWN_POTION_DELAY = 0.5  # Longer delay for post-respawn healing
POST_RESPAWN_WAIT = 2.0  # Wait time after post-respawn healing


# Respawn system timing
RESPAWN_WAIT_DURATION = 7.5  # Wait time before clicking respawn button
POST_RESPAWN_HEAL_DURATION = 3.0  # Duration of post-respawn healing phase
CLICK_RESPAWN_DELAY = 1.0  # Wait time after clicking respawn button
# Respawn retry system
RESPAWN_MAX_ATTEMPTS = 3
RESPAWN_RETRY_DELAYS = [3.0, 5.0, 10.0]
RESPAWN_FAILURE_MESSAGE = (
    "❌ Respawn system failed after maximum attempts. Please restart the script manually."
)


# Automation loop timing
AUTOMATION_LOOP_DELAY = 2.0  # Standard delay between automation checks
MAIN_LOOP_DELAY = 0.1  # Delay in main command loop
SCREENSHOT_DELAY = 0.05  # Delay to ensure screenshot file is written

# Key bindings
DEFAULT_HEALTH_POTION_KEY = "1"  # Key for health potion
DEFAULT_MANA_POTION_KEY = "2"  # Key for mana potion (WIP)
DEFAULT_SKILL_KEYS = ["3", "4"]  # Keys for skills
QUIT_KEY = "q"  # Key to quit automation
START_KEY = "r"  # Key to start/restart automation

# Potion usage based on health level
POTION_USAGE_MAP = {
    "critical": 6,  # Use 6 potions for critical health (≤20%)
    "low": 5,  # Use 5 potions for low health (≤40%)
    "medium": 3,  # Use 3 potions for medium health (≤70%)
    "high": 2,  # Use 2 potions for high health (≤90%)
    "post_respawn": 2,  # Use 2 potions after respawn
}

# Screenshot settings
SCREENSHOT_TIMEOUT = 5  # Timeout for screenshot operations
TEMP_SCREENSHOT_PREFIX = "screenshot_"  # Prefix for temporary screenshot files
DEBUG_SCREENSHOT_NAME = "debug_screenshot.png"  # Debug screenshot filename
DEBUG_REGION_PREFIX = "debug_region_"  # Prefix for debug region files

# PyAutoGUI safety settings
PYAUTOGUI_FAILSAFE = True  # Enable PyAutoGUI failsafe
PYAUTOGUI_PAUSE = 0.1  # Default pause between PyAutoGUI operations

# Template matching methods
TEMPLATE_MATCH_METHODS = {
    "CCOEFF_NORMED": "cv2.TM_CCOEFF_NORMED",
    "CCORR_NORMED": "cv2.TM_CCORR_NORMED",
    "SQDIFF_NORMED": "cv2.TM_SQDIFF_NORMED",  # best one
}

# Debug settings
DEBUG_TEST_REGIONS_COUNT = 3  # Number of test regions to save in debug mode
DEBUG_REGION_MULTIPLIER = 3  # Multiplier for debug region size

# Error messages
ERROR_MESSAGES = {
    "no_templates": "CRITICAL ERROR: No health templates loaded! Check your images folder.",
    "screenshot_failed": "Screenshot capture failed",
    "template_load_failed": "Failed to load template",
    "key_press_failed": "Failed to press key",
    "empty_health_detected": "EMPTY HEALTH BAR DETECTED",
    "respawn_button_not_found": "Respawn button not found, extending wait...",
}

# Success messages
SUCCESS_MESSAGES = {
    "template_loaded": "SUCCESS: Loaded health template",
    "respawn_clicked": "Respawn button clicked! Starting post-respawn healing...",
    "health_restored": "Health restored! Character has been revived - resuming normal automation...",
    "automation_started": "Starting automation... Press 'q' to quit",
    "death_confirmed": "Character death confirmed ",
}

# Mana system constants (Work In Progress)
# These will be used when mana functionality is implemented
DEFAULT_MANA_THRESHOLD = 0.5  # Use mana potion when below 50%
MANA_COLOR_RANGE_LOWER = [100, 100, 100]  # Blue lower bound for mana detection
MANA_COLOR_RANGE_UPPER = [130, 255, 255]  # Blue upper bound for mana detection
