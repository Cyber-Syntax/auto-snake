"""Main entry point for C++ enhanced automation system."""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from auto_snake.constants import DEFAULT_HEALTH_THRESHOLD
from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation
from auto_snake.threading_automation import MultiThreadedGameAutomation


def setup_logging(debug_mode: bool = False, log_file: Optional[str] = None):
    """Setup logging configuration."""
    level = logging.DEBUG if debug_mode else logging.INFO

    format_str = "%(asctime)s - %(threadName)-15s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format=format_str, handlers=handlers)

    # Reduce noise from some modules
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


def signal_handler(signum, frame, automation=None):
    """Handle interrupt signals gracefully."""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")

    if automation and hasattr(automation, "thread_state"):
        automation.thread_state.stop()

    print("✅ Automation stopped")
    sys.exit(0)


def print_banner():
    """Print application banner."""
    print("🚀 C++ Enhanced Multi-Core Game Automation")
    print("=" * 60)
    print("High-performance automation with true parallelism")
    print("Developed by: Cyber-syntax")
    print("=" * 60)


def print_system_info():
    """Print system and environment information."""
    import multiprocessing
    import platform

    print("\n🔍 System Information:")
    print(f"   Platform: {platform.system()} {platform.release()}")
    print(f"   Python: {platform.python_version()}")
    print(f"   CPU cores: {multiprocessing.cpu_count()}")

    try:
        import cv2

        print(f"   OpenCV: {cv2.__version__}")
    except ImportError:
        print("   OpenCV: Not available")

    try:
        import numpy as np

        print(f"   NumPy: {np.__version__}")
    except ImportError:
        print("   NumPy: Not available")

    try:
        import automation_core

        print("   C++ Extensions: ✅ Available")
    except ImportError:
        print("   C++ Extensions: ❌ Not available")


def run_diagnostics(automation):
    """Run comprehensive diagnostics."""
    print("\n🔧 Running System Diagnostics...")
    print("-" * 40)

    # C++ diagnostics
    if hasattr(automation, "run_cpp_diagnostics"):
        print("Running C++ extension tests...")
        diagnostics = automation.run_cpp_diagnostics()

        print(f"   Tests passed: {diagnostics['tests_passed']}")
        print(f"   Tests failed: {diagnostics['tests_failed']}")

        if diagnostics["errors"]:
            print("   Errors:")
            for error in diagnostics["errors"]:
                print(f"     - {error}")

        if diagnostics["tests_passed"] > 0 and diagnostics["tests_failed"] == 0:
            print("   ✅ All C++ tests passed!")
        else:
            print("   ⚠️  Some C++ tests failed")

    # Performance benchmark
    if hasattr(automation, "benchmark_performance_comparison"):
        print("\nRunning performance benchmark...")
        benchmark = automation.benchmark_performance_comparison(iterations=3)

        if "error" not in benchmark:
            print(f"   C++ average: {benchmark['cpp_avg_time_ms']:.2f}ms")
            print(f"   Python average: {benchmark['python_avg_time_ms']:.2f}ms")
            print(f"   Speedup: {benchmark['speedup_factor']:.1f}x")
            print(f"   Improvement: {benchmark['performance_improvement']}")
        else:
            print(f"   Benchmark failed: {benchmark['error']}")

    print("-" * 40)


def validate_templates_directory(templates_path: Path) -> bool:
    """Validate that templates directory exists and contains templates."""
    if not templates_path.exists():
        print(f"❌ Templates directory not found: {templates_path}")
        print("   Please create the templates directory and add template images")
        return False

    template_files = list(templates_path.glob("*.png")) + list(templates_path.glob("*.jpg"))

    if not template_files:
        print(f"⚠️  No template images found in: {templates_path}")
        print("   Please add template images (.png or .jpg) to the templates directory")
        return False

    print(f"✅ Found {len(template_files)} template files in: {templates_path}")
    return True


def main():
    """Main entry point for C++ enhanced automation."""
    parser = argparse.ArgumentParser(
        description="C++ Enhanced Multi-Core Game Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with default settings
  %(prog)s --debug --threads 4               # Debug mode with 4 threads
  %(prog)s --health-threshold 0.2            # Lower health threshold
  %(prog)s --templates ./my_templates        # Custom templates directory
  %(prog)s --diagnostics-only                # Run diagnostics and exit
  %(prog)s --fallback-threading              # Force Python threading fallback
  %(prog)s --benchmark                       # Run performance benchmark
        """,
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument(
        "--templates",
        type=Path,
        default=Path("templates"),
        help="Path to templates directory (default: templates)",
    )

    parser.add_argument(
        "--health-threshold",
        type=float,
        default=DEFAULT_HEALTH_THRESHOLD,
        help=f"Health threshold for potion usage (default: {DEFAULT_HEALTH_THRESHOLD})",
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Number of detection threads (default: auto-detect)",
    )

    parser.add_argument("--log-file", type=str, help="Log file path (default: console only)")

    parser.add_argument("--diagnostics-only", action="store_true", help="Run diagnostics and exit")

    parser.add_argument(
        "--benchmark", action="store_true", help="Run performance benchmark and exit"
    )

    parser.add_argument(
        "--fallback-threading",
        action="store_true",
        help="Force use of Python threading (disable C++ extensions)",
    )

    parser.add_argument(
        "--no-validation", action="store_true", help="Skip template directory validation"
    )

    parser.add_argument(
        "--system-info", action="store_true", help="Print system information and exit"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug, args.log_file)

    # Print banner
    print_banner()

    # Print system info if requested or in debug mode
    if args.system_info or args.debug:
        print_system_info()
        if args.system_info:
            return 0

    # Validate health threshold
    if not 0.0 <= args.health_threshold <= 1.0:
        print(f"❌ Invalid health threshold: {args.health_threshold}")
        print("   Health threshold must be between 0.0 and 1.0")
        return 1

    # Validate templates directory
    if not args.no_validation and not validate_templates_directory(args.templates):
        return 1

    # Determine number of threads
    max_threads = args.threads
    if max_threads is None:
        import multiprocessing

        max_threads = min(multiprocessing.cpu_count(), 4)

    print("\n⚙️  Configuration:")
    print(f"   Templates directory: {args.templates}")
    print(f"   Health threshold: {args.health_threshold * 100}%")
    print(f"   Detection threads: {max_threads}")
    print(f"   Debug mode: {args.debug}")
    print(f"   Log file: {args.log_file or 'Console only'}")

    # Initialize automation
    try:
        if args.fallback_threading:
            print("\n🧵 Using Python threading fallback...")
            automation = MultiThreadedGameAutomation(
                debug_mode=args.debug,
                images_path=args.templates,
                health_threshold=args.health_threshold,
                max_detection_threads=max_threads,
            )
        else:
            print("\n🚀 Initializing C++ enhanced automation...")
            automation = CppEnhancedAutomation(
                debug_mode=args.debug,
                images_path=args.templates,
                health_threshold=args.health_threshold,
                max_detection_threads=max_threads,
            )

            # Show C++ availability
            stats = automation.get_performance_stats()
            if stats.get("cpp_available", False):
                print("   ✅ C++ extensions loaded successfully")
            else:
                print("   ⚠️  C++ extensions not available, using threading fallback")

    except Exception as e:
        logging.error(f"Failed to initialize automation: {e}")
        print(f"❌ Initialization failed: {e}")
        return 1

    # Setup signal handlers
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, automation))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, automation))

    # Run diagnostics if requested
    if args.diagnostics_only or args.debug:
        run_diagnostics(automation)
        if args.diagnostics_only:
            return 0

    # Run benchmark if requested
    if args.benchmark:
        if hasattr(automation, "benchmark_performance_comparison"):
            print("\n⚡ Running detailed performance benchmark...")
            benchmark = automation.benchmark_performance_comparison(iterations=10)

            if "error" not in benchmark:
                print(f"\n📊 Benchmark Results ({benchmark['iterations']} iterations):")
                print(f"   C++ average time: {benchmark['cpp_avg_time_ms']:.3f}ms")
                print(f"   Python average time: {benchmark['python_avg_time_ms']:.3f}ms")
                print(f"   Speedup factor: {benchmark['speedup_factor']:.2f}x")
                print(f"   Performance improvement: {benchmark['performance_improvement']}")

                if benchmark["cpp_faster"]:
                    print("   🏆 C++ extensions provide significant performance improvement!")
                else:
                    print("   ⚠️  C++ extensions not faster (check installation)")
            else:
                print(f"   ❌ Benchmark failed: {benchmark['error']}")

        return 0

    # Print usage instructions
    print("\n📋 Controls:")
    print("   Press Ctrl+C to stop automation gracefully")
    print("   Press 'q' to quit (if supported by automation)")
    print("   Check log output for detailed status information")

    print("\n🎯 Automation will:")
    print("   🩺 Monitor health continuously")
    print(f"   💊 Use potions when health < {args.health_threshold * 100}%")
    print("   ⚠️  Handle emergency healing situations")
    print("   💀 Detect and handle character death/respawn")
    print("   📊 Provide performance statistics")

    # Start automation
    print("\n🎮 Starting automation...")
    print("=" * 60)

    try:
        start_time = time.time()
        automation.run_automation()

    except KeyboardInterrupt:
        print("\n⏹️  Automation stopped by user")

    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)
        print(f"\n❌ Automation failed: {e}")
        return 1

    finally:
        runtime = time.time() - start_time if "start_time" in locals() else 0

        print("\n" + "=" * 60)
        print("🏁 Automation Session Complete")
        print(f"   Runtime: {runtime:.1f} seconds")

        # Print final performance report
        if hasattr(automation, "print_performance_report"):
            automation.print_performance_report()

        # Print final statistics
        if hasattr(automation, "get_performance_stats"):
            stats = automation.get_performance_stats()
            print("\n📈 Final Statistics:")
            print(f"   Screenshots processed: {stats.get('screenshots_processed', 0)}")
            print(f"   Detections processed: {stats.get('detections_processed', 0)}")
            print(f"   Actions executed: {stats.get('actions_executed', 0)}")

            if stats.get("cpp_available", False):
                print(f"   C++ usage: {stats.get('cpp_usage_percentage', 0):.1f}%")
                print(f"   Template cache hit rate: {stats.get('template_cache_hit_rate', 0):.1f}%")

        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
