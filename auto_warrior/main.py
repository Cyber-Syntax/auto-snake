"""Main entry point for the auto-snake game automation system.

This module provides the command-line interface and main execution logic
for the game automation system with proper argument parsing and error handling.

Example:
    Run with default settings:
    
    python -m auto_warrior.main
    
    Run with debug mode enabled:
    
    python -m auto_warrior.main --debug
    
    Run with custom images path:
    
    python -m auto_warrior.main --images-path /path/to/images
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import NoReturn

# Add the parent directory to sys.path for local imports when running as standalone script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_warrior.automation import GameAutomation
from auto_warrior.constants import (
    AUTHOR,
    DEFAULT_HEALTH_THRESHOLD,
    LICENSE,
    MAIN_LOOP_DELAY,
    VERSION,
)
from auto_warrior.exceptions import AutoSnakeError
from auto_warrior.input_control import AutomationController


def setup_logging(debug_mode: bool) -> None:
    """Configure logging for the application.
    
    Args:
        debug_mode: Whether to enable debug level logging
    """
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if debug_mode:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Set specific logger levels
    if not debug_mode:
        # Reduce noise from external libraries
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("cv2").setLevel(logging.WARNING)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Auto Snake Game Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                                    # Run with default settings
  %(prog)s --debug                            # Enable debug mode
  %(prog)s --images-path ./custom_images      # Use custom images directory
  %(prog)s --health-threshold 0.3             # Set health threshold to 30%%

Version: {VERSION}
Author: {AUTHOR}
License: {LICENSE}

For more information, visit: https://github.com/cyber-syntax/auto-snake
        """
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed logging (increases CPU usage)"
    )
    
    parser.add_argument(
        "--images-path",
        type=Path,
        metavar="PATH",
        help="Path to directory containing template images (default: ./images)"
    )
    
    parser.add_argument(
        "--health-threshold",
        type=float,
        default=DEFAULT_HEALTH_THRESHOLD,
        metavar="THRESHOLD",
        help=f"Health percentage threshold for potion usage (0.0-1.0, default: {DEFAULT_HEALTH_THRESHOLD})"
    )
    
    parser.add_argument(
        "--no-respawn-wait",
        action="store_true",
        help="Click respawn button immediately when available (skip safety delay)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}"
    )
    
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Raises:
        ValueError: If arguments are invalid
    """
    # Validate health threshold
    if not 0.0 <= args.health_threshold <= 1.0:
        raise ValueError(
            f"Health threshold must be between 0.0 and 1.0, got {args.health_threshold}"
        )
    
    # Validate images path if provided
    if args.images_path is not None:
        if not args.images_path.exists():
            raise ValueError(f"Images path does not exist: {args.images_path}")
        if not args.images_path.is_dir():
            raise ValueError(f"Images path is not a directory: {args.images_path}")


def print_startup_banner(args: argparse.Namespace) -> None:
    """Print application startup banner.
    
    Args:
        args: Parsed command line arguments
    """
    print(f"Auto Snake Game Automation v{VERSION}")
    print(f"Author: {AUTHOR}")
    print(f"License: {LICENSE}")
    print("=" * 50)
    
    print("\nStarting Game Automation System...")
    print(f"Debug mode: {'ENABLED' if args.debug else 'DISABLED'}")
    print(f"Health threshold: {args.health_threshold:.1%}")
    print(f"Respawn wait: {'DISABLED' if args.no_respawn_wait else 'ENABLED (7.5s safety delay)'}")
    
    if args.images_path:
        print(f"Images path: {args.images_path}")
    else:
        print("Images path: ./images (default)")
    
    print("\nSafety Notice:")
    print("This tool is for educational purposes only.")
    print("Please ensure you comply with game terms of service.")
    print("=" * 50)


def run_automation_with_controller(automation: GameAutomation) -> None:
    """Run automation with keyboard control.
    
    Args:
        automation: GameAutomation instance to run
    """
    controller = AutomationController(automation.debug_mode)
    
    try:
        controller.start_listening()
        
        # Main control loop
        while controller.is_main_running():
            if controller.is_automation_running():
                try:
                    automation.run_automation()
                except Exception as e:
                    logging.error(f"Automation error: {e}")
                    print(f"Error in automation: {e}")
                    print("Press 'r' to restart or 'q' to quit")
                finally:
                    controller.set_automation_running(False)
            
            time.sleep(MAIN_LOOP_DELAY)
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    finally:
        controller.stop_listening()


def main() -> None:
    """Main entry point for the application."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Validate arguments
        validate_arguments(args)
        
        # Setup logging
        setup_logging(args.debug)
        
        # Print startup information
        print_startup_banner(args)
        
        # Create automation instance
        automation = GameAutomation(
            debug_mode=args.debug,
            images_path=args.images_path,
            health_threshold=args.health_threshold
        )
        
        # Run automation with controller
        run_automation_with_controller(automation)
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except AutoSnakeError as e:
        logging.error(f"Automation error: {e}")
        print(f"Automation error: {e}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested")
        sys.exit(0)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def cli_entry_point() -> NoReturn:
    """CLI entry point that never returns."""
    main()
    sys.exit(0)


if __name__ == "__main__":
    main()