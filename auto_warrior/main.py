
"""Main entry point for the auto-snake game automation system.

This module provides the command-line interface and main execution logic
for the game automation system with proper argument parsing, multiprocessing,
and error handling.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import NoReturn
import multiprocessing as mp

# Add the parent directory to sys.path for local imports when running as a standalone script
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
    """Configure logging for the application."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        if debug_mode
        else "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.basicConfig(level=log_level, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
    # Silence verbose external libs when not debugging
    if not debug_mode:
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("cv2").setLevel(logging.WARNING)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Auto Snake Game Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                      # Run with default settings
  %(prog)s --debug              # Enable debug mode
  %(prog)s --images-path ./img  # Use custom images directory
  %(prog)s --health-threshold 0.3
Version: {VERSION}
Author: {AUTHOR}
License: {LICENSE}
"""
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--images-path",
        type=Path,
        metavar="PATH",
        help="Directory containing template images (default: ./images)",
    )
    parser.add_argument(
        "--health-threshold",
        type=float,
        default=DEFAULT_HEALTH_THRESHOLD,
        metavar="THRESHOLD",
        help=f"Health threshold for potion usage (0.0–1.0, default: {DEFAULT_HEALTH_THRESHOLD})",
    )
    parser.add_argument(
        "--no-respawn-wait",
        action="store_true",
        help="Skip respawn safety delay",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command line arguments."""
    if not 0.0 <= args.health_threshold <= 1.0:
        raise ValueError(f"Health threshold must be between 0.0 and 1.0, got {args.health_threshold}")
    if args.images_path and not args.images_path.is_dir():
        raise ValueError(f"Images path is not a directory: {args.images_path}")


def print_startup_banner(args: argparse.Namespace) -> None:
    """Print application startup banner."""
    print(f"Auto Snake Game Automation v{VERSION}")
    print(f"Author: {AUTHOR}    License: {LICENSE}")
    print("=" * 60)
    print(f"Debug mode: {'ENABLED' if args.debug else 'DISABLED'}")
    print(f"Health threshold: {args.health_threshold:.1%}")
    print(f"Respawn wait delay: {'OFF' if args.no_respawn_wait else 'ON'}")
    print(f"Images path: {args.images_path or './images'}")
    print("=" * 60)


def run_automation_with_controller(automation: GameAutomation) -> None:
    """
    Run automation in a child process and listen for 'r' (restart) and 'q' (quit)
    commands from the keyboard controller in the main process.
    """
    controller = AutomationController(automation.debug_mode)

    # Multiprocessing primitives
    stop_event = mp.Event()
    proc: mp.Process | None = None

    def start_worker():
        nonlocal proc
        if proc and proc.is_alive():
            print("⚠️ Automation already running.")
            return
        stop_event.clear()
        proc = mp.Process(
            target=automation._automation_worker,  # worker entrypoint
            args=(automation.command_queue, automation.status_queue, stop_event, automation.init_params),
            daemon=True,
        )
        proc.start()
        print("🚀 Automation started.")

    def stop_worker():
        if proc and proc.is_alive():
            stop_event.set()
            proc.join(timeout=5.0)
            if proc.is_alive():
                proc.terminate()
            print("🛑 Automation stopped.")

    try:
        controller.start_listening()
        print("Press 'r' to (re)start, 'q' to quit.")

        while controller.is_main_running():
            if controller.is_automation_running():
                # User pressed 'r'
                start_worker()
                controller.set_automation_running(False)

            # if controller.is_quit_requested():
            #     # User pressed 'q'
            #     stop_worker()
            #     break

            # Optional: handle dynamic threshold changes
            # e.g. controller could push commands into automation.command_queue

            time.sleep(MAIN_LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n❎ Shutdown requested via Ctrl+C.")

    finally:
        stop_worker()
        controller.stop_listening()


def main() -> None:
    parser = create_argument_parser()
    args = parser.parse_args()
    try:
        validate_arguments(args)
        setup_logging(args.debug)
        print_startup_banner(args)

        # Instantiate automation (but do not call run_automation directly)
        automation = GameAutomation(
            debug_mode=args.debug,
            images_path=args.images_path,
            health_threshold=args.health_threshold,
        )

        run_automation_with_controller(automation)

    except ValueError as ve:
        print(f"Argument error: {ve}", file=sys.stderr)
        sys.exit(1)
    except AutoSnakeError as ae:
        logging.error(f"Automation error: {ae}")
        print(f"Automation error: {ae}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        logging.exception("Unexpected error")
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(99)


def cli_entry_point() -> NoReturn:
    main()
    sys.exit(0)


if __name__ == "__main__":
    main()
