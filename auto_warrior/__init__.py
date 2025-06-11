"""Auto Snake Game Automation Package.

This package provides automation tools for game health monitoring,
respawn detection, and potion usage in gaming environments.

Example:
    Basic usage:
    
    from auto_warrior import GameAutomation
    
    automation = GameAutomation(debug_mode=False)
    automation.run_automation()
"""

from auto_warrior.automation import GameAutomation
from auto_warrior.exceptions import (
    AutoSnakeError,
    ScreenshotError,
    TemplateLoadError,
    KeyPressError,
)

__version__ = "1.0.0"
__author__ = "Cyber-syntax"
__license__ = "BSD 3-Clause License"

__all__ = [
    "GameAutomation",
    "AutoSnakeError",
    "ScreenshotError", 
    "TemplateLoadError",
    "KeyPressError",
]