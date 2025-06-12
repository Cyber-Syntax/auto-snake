"""Example usage of C++ enhanced automation."""

import logging
import time

from auto_snake.constants import DEFAULT_HEALTH_THRESHOLD
from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation

# Configure logging to see all thread activity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("automation.log")],
)


def main():
    """Run C++ enhanced automation example."""

    print("🎮 C++ Enhanced Game Automation")
    print("=" * 60)
    print("🚀 Features:")
    print("   ✅ True parallelism with GIL released")
    print("   ✅ Concurrent screenshot capture (10 FPS)")
    print("   ✅ Parallel health detection")
    print("   ✅ Parallel respawn detection")
    print("   ✅ Multi-template matching")
    print("   ✅ Batch screenshot processing")
    print("   ✅ Template caching")
    print("   ✅ Performance monitoring")
    print("   ✅ Fallback to threading if C++ unavailable")
    print("=" * 60)

    # Initialize C++ enhanced automation
    automation = CppEnhancedAutomation(
        debug_mode=True,  # Enable debug logging
        images_path=None,  # Use default path (auto_snake/images)
        health_threshold=DEFAULT_HEALTH_THRESHOLD,
        max_detection_threads=4,  # Use more threads with C++ extensions
    )

    print(f"Health threshold: {DEFAULT_HEALTH_THRESHOLD * 100}%")

    # Run diagnostics
    print("\n🔧 Running C++ diagnostics...")
    diagnostics = automation.run_cpp_diagnostics()

    if diagnostics["cpp_available"]:
        print(f"   Tests passed: {diagnostics['tests_passed']}")
        print(f"   Tests failed: {diagnostics['tests_failed']}")
        if diagnostics["errors"]:
            print("   Errors:")
            for error in diagnostics["errors"]:
                print(f"     - {error}")
    else:
        print("   C++ extensions not available - using Python fallback")

    # Performance benchmark
    if diagnostics["cpp_available"]:
        print("\n⚡ Running performance benchmark...")
        benchmark = automation.benchmark_performance_comparison(iterations=5)

        if "error" not in benchmark:
            print(f"   C++ average time: {benchmark['cpp_avg_time_ms']:.2f}ms")
            print(f"   Python average time: {benchmark['python_avg_time_ms']:.2f}ms")
            print(f"   Speedup factor: {benchmark['speedup_factor']:.1f}x")
            print(f"   Performance improvement: {benchmark['performance_improvement']}")
        else:
            print(f"   Benchmark failed: {benchmark['error']}")

    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop automation")
    print("The automation will:")
    print("  🩺 Monitor health continuously")
    print("  💊 Use potions when health is low")
    print("  ⚠️  Detect emergency situations")
    print("  💀 Handle character death and respawn")
    print("  📊 Show performance statistics on exit")
    print("=" * 60)

    try:
        # Run the automation
        automation.run_automation()

    except KeyboardInterrupt:
        print("\n⏹️  Automation stopped by user")

    except Exception as e:
        print(f"\n❌ Automation failed: {e}")
        logging.error(f"Automation error: {e}", exc_info=True)

    finally:
        # Print detailed performance report
        automation.print_performance_report()

        # Show queue status
        queue_status = automation.get_queue_status()
        print("\n📊 Final Queue Status:")
        print(f"   Screenshot queue: {queue_status['screenshot_queue_size']}")
        print(f"   Detection queue: {queue_status['detection_queue_size']}")
        print(f"   Action queue: {queue_status['action_queue_size']}")


def demo_custom_actions():
    """Demonstrate custom action functionality."""

    print("\n🎯 Custom Actions Demo")
    print("-" * 30)

    automation = CppEnhancedAutomation(
        debug_mode=True, health_threshold=0.5, max_detection_threads=2
    )

    # Add some custom actions
    automation.add_custom_action("skill_use", priority=8, params={"skill_key": "1"})
    automation.add_custom_action("skill_use", priority=8, params={"skill_key": "2"})
    automation.add_custom_action("custom_heal", priority=3, params={"potion_count": 3})

    print("Added custom actions to queue")
    print(f"Queue status: {automation.get_queue_status()}")

    # Clear template cache
    automation.clear_template_cache()
    print("Template cache cleared")


def analyze_performance():
    """Analyze automation performance over time."""

    print("\n📈 Performance Analysis")
    print("-" * 30)

    automation = CppEnhancedAutomation(debug_mode=False)

    # Simulate some usage
    start_time = time.time()

    # Simulate processing for a few seconds
    for i in range(10):
        automation.performance_stats["screenshots_processed"] += 10
        automation.performance_stats["detections_processed"] += 8
        automation.performance_stats["actions_executed"] += 2
        time.sleep(0.1)

    # Get performance stats
    stats = automation.get_performance_stats()

    print(f"Runtime: {stats['runtime_seconds']:.1f}s")
    print(f"Screenshots/sec: {stats['screenshots_per_second']:.1f}")
    print(f"Detections/sec: {stats['detections_per_second']:.1f}")
    print(f"Actions/sec: {stats['actions_per_second']:.1f}")

    if stats.get("cpp_available", False):
        print(f"C++ usage: {stats['cpp_usage_percentage']:.1f}%")
        print(f"Cache hit rate: {stats['template_cache_hit_rate']:.1f}%")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            demo_custom_actions()
        elif sys.argv[1] == "analyze":
            analyze_performance()
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python cpp_enhanced_usage.py        - Run main automation")
            print("  python cpp_enhanced_usage.py demo   - Demo custom actions")
            print("  python cpp_enhanced_usage.py analyze - Analyze performance")
            print("  python cpp_enhanced_usage.py help   - Show this help")
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Use 'help' for available commands")
    else:
        main()
