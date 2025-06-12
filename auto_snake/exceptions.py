"""Custom exceptions for the auto_snake package.

This module defines specific exception types for different error conditions
that can occur during game automation operations.
"""


class AutoSnakeError(Exception):
    """Base exception class for all auto_snake related errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        """Initialize the exception.
        
        Args:
            message: The main error message
            details: Optional additional details about the error
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ScreenshotError(AutoSnakeError):
    """Raised when screenshot capture fails."""

    def __init__(self, message: str = "Screenshot capture failed", details: str | None = None) -> None:
        """Initialize screenshot error.
        
        Args:
            message: Error message describing the screenshot failure
            details: Additional details about the failure
        """
        super().__init__(message, details)


class TemplateLoadError(AutoSnakeError):
    """Raised when template image loading fails."""

    def __init__(self, template_path: str, details: str | None = None) -> None:
        """Initialize template load error.
        
        Args:
            template_path: Path to the template that failed to load
            details: Additional details about the failure
        """
        message = f"Failed to load template: {template_path}"
        super().__init__(message, details)
        self.template_path = template_path


class KeyPressError(AutoSnakeError):
    """Raised when key press simulation fails."""

    def __init__(self, key: str, details: str | None = None) -> None:
        """Initialize key press error.
        
        Args:
            key: The key that failed to be pressed
            details: Additional details about the failure
        """
        message = f"Failed to press key: {key}"
        super().__init__(message, details)
        self.key = key


class TemplateMatchError(AutoSnakeError):
    """Raised when template matching operations fail."""

    def __init__(self, template_name: str, details: str | None = None) -> None:
        """Initialize template match error.
        
        Args:
            template_name: Name of the template that failed to match
            details: Additional details about the failure
        """
        message = f"Template matching failed for: {template_name}"
        super().__init__(message, details)
        self.template_name = template_name


class ConfigurationError(AutoSnakeError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, config_key: str, details: str | None = None) -> None:
        """Initialize configuration error.
        
        Args:
            config_key: The configuration key that is invalid
            details: Additional details about the configuration issue
        """
        message = f"Configuration error for key: {config_key}"
        super().__init__(message, details)
        self.config_key = config_key