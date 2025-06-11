"""Template management for game automation.

This module handles loading, validating, and managing template images used
for health bar detection, respawn button detection, and other UI elements.
"""

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from auto_warrior.constants import (
    DEFAULT_IMAGES_PATH,
    EMPTY_HEALTH_TEMPLATE,
    HEALTH_TEMPLATE_FILES,
    RESPAWN_BUTTON_TEMPLATE,
)
from auto_warrior.exceptions import TemplateLoadError

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages template images for automation operations."""

    def __init__(self, images_path: Path | str | None = None, debug_mode: bool = False) -> None:
        """Initialize the template manager.
        
        Args:
            images_path: Path to directory containing template images
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.images_path = Path(images_path) if images_path else DEFAULT_IMAGES_PATH
        
        # Template storage
        self.health_templates: dict[str, np.ndarray] = {}
        self.empty_health_template: np.ndarray | None = None
        self.respawn_button_template: np.ndarray | None = None
        
        if self.debug_mode:
            logger.debug(f"TemplateManager initialized with path: {self.images_path}")

    def load_all_templates(self) -> None:
        """Load all required templates for automation."""
        self.load_health_templates()
        self.load_respawn_templates()
        
        if self.debug_mode:
            logger.debug(f"Total templates loaded: {len(self.health_templates)}")
            
        if not self.health_templates:
            raise TemplateLoadError(
                str(self.images_path),
                "No health templates loaded! Check your images folder."
            )

    def load_health_templates(self) -> None:
        """Load health bar template images."""
        if self.debug_mode:
            logger.debug(f"Loading health templates from: {self.images_path}")
            logger.debug(f"Looking for templates: {list(HEALTH_TEMPLATE_FILES.values())}")

        for percentage, filename in HEALTH_TEMPLATE_FILES.items():
            filepath = self.images_path / filename
            
            if self.debug_mode:
                logger.debug(f"Checking file: {filepath}")

            try:
                template = self._load_template_image(filepath)
                if template is not None:
                    self.health_templates[percentage] = template
                    
                    if self.debug_mode:
                        logger.debug(
                            f"SUCCESS: Loaded health template: {percentage}% - {filename} "
                            f"(shape: {template.shape})"
                        )
                        
                    # Verify PIL compatibility
                    self._verify_pil_compatibility(filepath, filename)
                else:
                    self._handle_template_load_failure(filepath, filename, percentage)
                    
            except Exception as e:
                logger.error(f"Failed to load template {filename}: {e}")
                continue

    def load_respawn_templates(self) -> None:
        """Load empty health bar and respawn button templates."""
        if self.debug_mode:
            logger.debug("Loading respawn system templates...")
        
        # Load empty health bar template
        self._load_empty_health_template()
        
        # Load respawn button template
        self._load_respawn_button_template()

    def _load_empty_health_template(self) -> None:
        """Load the empty health bar template."""
        empty_health_path = self.images_path / EMPTY_HEALTH_TEMPLATE
        
        if empty_health_path.exists():
            self.empty_health_template = self._load_template_image(empty_health_path)
            
            if self.empty_health_template is not None:
                if self.debug_mode:
                    logger.debug(
                        f"SUCCESS: Loaded empty health template "
                        f"(shape: {self.empty_health_template.shape})"
                    )
            else:
                logger.error(f"Could not load {EMPTY_HEALTH_TEMPLATE}")
        else:
            logger.error(f"{EMPTY_HEALTH_TEMPLATE} not found")

    def _load_respawn_button_template(self) -> None:
        """Load the respawn button template."""
        respawn_path = self.images_path / RESPAWN_BUTTON_TEMPLATE
        
        if respawn_path.exists():
            self.respawn_button_template = self._load_template_image(respawn_path)
            
            if self.respawn_button_template is not None:
                if self.debug_mode:
                    logger.debug(
                        f"SUCCESS: Loaded respawn button template "
                        f"(shape: {self.respawn_button_template.shape})"
                    )
            else:
                logger.error(f"Could not load {RESPAWN_BUTTON_TEMPLATE}")
        else:
            logger.error(f"{RESPAWN_BUTTON_TEMPLATE} not found")

    def _load_template_image(self, filepath: Path) -> np.ndarray | None:
        """Load a template image using OpenCV.
        
        Args:
            filepath: Path to the template image file
            
        Returns:
            OpenCV image array or None if loading failed
        """
        try:
            # Primary method: OpenCV
            template = cv2.imread(str(filepath))
            if template is not None:
                return template
                
            # Fallback method: PIL + conversion
            return self._load_with_pil_fallback(filepath)
            
        except Exception as e:
            logger.error(f"Error loading template {filepath}: {e}")
            return None

    def _load_with_pil_fallback(self, filepath: Path) -> np.ndarray | None:
        """Load image using PIL as fallback method.
        
        Args:
            filepath: Path to the image file
            
        Returns:
            OpenCV image array or None if loading failed
        """
        try:
            pil_img = Image.open(filepath)
            template = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            if self.debug_mode:
                logger.debug(f"SUCCESS: Loaded via PIL fallback: {filepath}")
                
            return template
            
        except Exception as e:
            logger.error(f"PIL fallback also failed for {filepath}: {e}")
            return None

    def _verify_pil_compatibility(self, filepath: Path, filename: str) -> None:
        """Verify that PIL can also load the image.
        
        Args:
            filepath: Path to the image file
            filename: Name of the file for logging
        """
        if not self.debug_mode:
            return
            
        try:
            test_img = Image.open(filepath)
            logger.debug(f"PIL can also load {filename} (size: {test_img.size})")
        except Exception as e:
            logger.warning(f"PIL cannot load {filename}: {e}")

    def _handle_template_load_failure(
        self, 
        filepath: Path, 
        filename: str, 
        percentage: str
    ) -> None:
        """Handle template loading failure with detailed logging.
        
        Args:
            filepath: Path to the failed template
            filename: Name of the template file
            percentage: Health percentage this template represents
        """
        logger.error(f"Could not load {filename} - cv2.imread returned None")
        
        # Try PIL as backup
        template = self._load_with_pil_fallback(filepath)
        if template is not None:
            self.health_templates[percentage] = template
            logger.info(
                f"SUCCESS: Loaded via PIL: {percentage}% - {filename} "
                f"(shape: {template.shape})"
            )

    def get_health_template(self, percentage: str) -> np.ndarray | None:
        """Get a specific health template.
        
        Args:
            percentage: Health percentage as string (e.g., "20", "full")
            
        Returns:
            Template image array or None if not found
        """
        return self.health_templates.get(percentage)

    def get_all_health_templates(self) -> dict[str, np.ndarray]:
        """Get all loaded health templates.
        
        Returns:
            Dictionary mapping percentage strings to template arrays
        """
        return self.health_templates.copy()

    def get_empty_health_template(self) -> np.ndarray | None:
        """Get the empty health template.
        
        Returns:
            Empty health template array or None if not loaded
        """
        return self.empty_health_template

    def get_respawn_button_template(self) -> np.ndarray | None:
        """Get the respawn button template.
        
        Returns:
            Respawn button template array or None if not loaded
        """
        return self.respawn_button_template

    def has_health_templates(self) -> bool:
        """Check if any health templates are loaded.
        
        Returns:
            True if health templates are available, False otherwise
        """
        return len(self.health_templates) > 0

    def get_template_info(self) -> dict[str, Any]:
        """Get information about loaded templates.
        
        Returns:
            Dictionary containing template loading status and counts
        """
        return {
            "health_templates_count": len(self.health_templates),
            "health_templates_loaded": list(self.health_templates.keys()),
            "empty_health_loaded": self.empty_health_template is not None,
            "respawn_button_loaded": self.respawn_button_template is not None,
            "images_path": str(self.images_path),
        }

    def validate_templates(self) -> list[str]:
        """Validate all loaded templates and return any issues.
        
        Returns:
            List of validation error messages
        """
        issues = []
        
        if not self.has_health_templates():
            issues.append("No health templates loaded")
            
        if self.empty_health_template is None:
            issues.append("Empty health template not loaded")
            
        if self.respawn_button_template is None:
            issues.append("Respawn button template not loaded")
            
        # Validate template dimensions
        for percentage, template in self.health_templates.items():
            if template.size == 0:
                issues.append(f"Health template {percentage}% has zero size")
            elif len(template.shape) != 3:
                issues.append(f"Health template {percentage}% has invalid dimensions")
                
        return issues