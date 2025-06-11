"""Screenshot utilities for game automation.

This module provides cross-platform screenshot functionality with proper
error handling and support for both Linux (scrot) and other platforms.
"""

import logging
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pyautogui
from PIL import Image

from auto_warrior.constants import (
    SCREENSHOT_DELAY,
    SCREENSHOT_TIMEOUT,
    TEMP_SCREENSHOT_PREFIX,
)
from auto_warrior.exceptions import ScreenshotError

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Manages screenshot operations across different platforms."""

    def __init__(self, debug_mode: bool = False) -> None:
        """Initialize the screenshot manager.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.platform = platform.system()
        
        if self.debug_mode:
            logger.debug(f"ScreenshotManager initialized for platform: {self.platform}")

    def take_screenshot(self) -> Image.Image:
        """Take a screenshot using the best available method.
        
        Returns:
            PIL Image object containing the screenshot
            
        Raises:
            ScreenshotError: If screenshot capture fails
        """
        if self.platform == "Linux":
            return self._take_screenshot_linux()
        return self._take_screenshot_default()

    def _take_screenshot_linux(self) -> Image.Image:
        """Take screenshot using scrot on Linux systems.
        
        Returns:
            PIL Image object containing the screenshot
            
        Raises:
            ScreenshotError: If scrot screenshot fails
        """
        try:
            # Create temporary file for screenshot
            timestamp = int(time.time())
            tmp_path = Path(f"/tmp/{TEMP_SCREENSHOT_PREFIX}{timestamp}.png")
            
            # Use scrot to capture screenshot
            cmd = ["scrot", str(tmp_path)]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=SCREENSHOT_TIMEOUT
            )
            
            if result.returncode != 0:
                error_details = f"scrot stderr: {result.stderr}, stdout: {result.stdout}"
                raise ScreenshotError(
                    "scrot command failed", 
                    f"Return code: {result.returncode}, {error_details}"
                )
            
            # Wait for file to be written
            time.sleep(SCREENSHOT_DELAY)
            
            # Validate screenshot file
            self._validate_screenshot_file(tmp_path)
            
            # Load image with PIL
            screenshot = Image.open(tmp_path)
            
            if self.debug_mode:
                logger.debug(f"scrot screenshot successful, size: {screenshot.size}")
            
            return screenshot
            
        except subprocess.TimeoutExpired as e:
            raise ScreenshotError("Screenshot timeout", str(e)) from e
        except Exception as e:
            raise ScreenshotError("Screenshot capture failed", str(e)) from e
        finally:
            # Clean up temporary file
            self._cleanup_temp_file(tmp_path)

    def _take_screenshot_default(self) -> Image.Image:
        """Take screenshot using PyAutoGUI (default method).
        
        Returns:
            PIL Image object containing the screenshot
            
        Raises:
            ScreenshotError: If PyAutoGUI screenshot fails
        """
        try:
            screenshot = pyautogui.screenshot()
            
            if self.debug_mode:
                logger.debug(f"PyAutoGUI screenshot successful, size: {screenshot.size}")
            
            return screenshot
            
        except Exception as e:
            raise ScreenshotError("PyAutoGUI screenshot failed", str(e)) from e

    def _validate_screenshot_file(self, file_path: Path) -> None:
        """Validate that screenshot file exists and has content.
        
        Args:
            file_path: Path to the screenshot file
            
        Raises:
            ScreenshotError: If file validation fails
        """
        if not file_path.exists():
            raise ScreenshotError(f"Screenshot file not created: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ScreenshotError(f"Screenshot file is empty: {file_path}")

    def _cleanup_temp_file(self, file_path: Path) -> None:
        """Clean up temporary screenshot file.
        
        Args:
            file_path: Path to the temporary file to remove
        """
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            if self.debug_mode:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

    def screenshot_to_cv2(self, screenshot: Image.Image) -> np.ndarray:
        """Convert PIL screenshot to OpenCV format.
        
        Args:
            screenshot: PIL Image object
            
        Returns:
            OpenCV image array in BGR format
        """
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def save_debug_screenshot(self, screenshot: Image.Image, filename: str) -> None:
        """Save screenshot for debugging purposes.
        
        Args:
            screenshot: PIL Image object to save
            filename: Name of the file to save
        """
        if not self.debug_mode:
            return
            
        try:
            screenshot_cv = self.screenshot_to_cv2(screenshot)
            cv2.imwrite(filename, screenshot_cv)
            logger.debug(f"Debug screenshot saved as {filename}")
        except Exception as e:
            logger.warning(f"Failed to save debug screenshot: {e}")

    def save_debug_regions(
        self, 
        screenshot_cv: np.ndarray, 
        template_size: tuple[int, int],
        prefix: str = "debug_region"
    ) -> None:
        """Save multiple regions of screenshot for debugging.
        
        Args:
            screenshot_cv: OpenCV image array
            template_size: Size of template (height, width)
            prefix: Prefix for debug region files
        """
        if not self.debug_mode:
            return
            
        try:
            th, tw = template_size
            height, width = screenshot_cv.shape[:2]
            
            # Define test regions
            regions = [
                (0, 0, tw * 3, th * 3),  # Top-left corner
                (width // 4, height // 4, tw * 3, th * 3),  # Quarter screen
                (width // 2, height // 2, tw * 3, th * 3),  # Center
            ]
            
            for i, (x, y, w, h) in enumerate(regions):
                # Ensure region is within image bounds
                x = max(0, min(x, width - w))
                y = max(0, min(y, height - h))
                w = min(w, width - x)
                h = min(h, height - y)
                
                region = screenshot_cv[y:y + h, x:x + w]
                filename = f"{prefix}_{i}.png"
                cv2.imwrite(filename, region)
                logger.debug(f"Saved test region {i} as {filename}")
                
        except Exception as e:
            logger.warning(f"Failed to save debug regions: {e}")