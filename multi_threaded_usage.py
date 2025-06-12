"""Example usage of multi-threaded automation (without C++ extensions)."""

import logging
import time

from auto_snake.constants import DEFAULT_HEALTH_THRESHOLD
from auto_snake.threading_automation import MultiThreadedGameAutomation

# Configure logging for multi-threading visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)-15s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("threading_automation.log")],
)


def main():
    """Run multi-threaded automation example."""

    print("🧵 Multi-Threaded Game Automation")
    print("=" * 60)
    print("🚀 Features:")
    print("   ✅ Concurrent screenshot capture")
    print("   ✅ Parallel health detection threads")
    print("   ✅ Parallel respawn detection threads")
    print("   ✅ Centralized action execution")
    print("   ✅ Thread-safe state management")
    print("   ✅ Performance monitoring")
    print("   ✅ Graceful thread shutdown")
    print("=" * 60)

    # Initialize multi-threaded automation
    automation = MultiThreadedGameAutomation(
        debug_mode=True,  # Enable debug logging
        images_path=None,  # Use default path (auto_snake/images)
        health_threshold=DEFAULT_HEALTH_THRESHOLD,
        max_detection_threads=2,  # Optimal for most systems without C++
    )

    print(f"Health threshold: {DEFAULT_HEALTH_THRESHOLD * 100}%")
    print(f"Screenshot queue size: {automation.screenshot_queue.maxsize}")
    print("Detection threads: 2 (Health + Respawn)")

    print("\n📊 Initial Queue Status:")
    queue_status = automation.get_queue_status()
    print(f"   Screenshot queue: {queue_status['screenshot_queue_size']}")
    print(f"   Detection queue: {queue_status['detection_queue_size']}")
    print(f"   Action queue: {queue_status['action_queue_size']}")

    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop automation")
    print("The automation will:")
    print("  📸 Capture screenshots continuously (10 FPS)")
    print("  🩺 Monitor health in parallel")
    print("  💀 Detect respawn situations")
    print("  💊 Execute healing actions")
    print("  📈 Log performance metrics")
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
        # Print performance statistics
        print("\n📊 Final Performance Statistics:")
        stats = automation.get_performance_stats()

        print(f"   Runtime: {stats['runtime_seconds']:.1f}s")
        print(f"   Screenshots processed: {stats['screenshots_processed']}")
        print(f"   Detections processed: {stats['detections_processed']}")
        print(f"   Actions executed: {stats['actions_executed']}")

        if stats["runtime_seconds"] > 0:
            print(f"   Screenshots/sec: {stats['screenshots_per_second']:.1f}")
            print(f"   Detections/sec: {stats['detections_per_second']:.1f}")
            print(f"   Actions/sec: {stats['actions_per_second']:.1f}")

        # Final queue status
        final_queue_status = automation.get_queue_status()
        print("\n📊 Final Queue Status:")
        print(f"   Screenshot queue: {final_queue_status['screenshot_queue_size']}")
        print(f"   Detection queue: {final_queue_status['detection_queue_size']}")
        print(f"   Action queue: {final_queue_status['action_queue_size']}")


def demo_custom_actions():
    """Demonstrate adding custom actions to the automation."""

    print("\n🎯 Custom Actions Demo")
    print("-" * 40)

    automation = MultiThreadedGameAutomation(
        debug_mode=True, health_threshold=0.6, max_detection_threads=2
    )

    print("Adding custom actions...")

    # Add various custom actions with different priorities
    automation.add_custom_action(
        action_type="skill_use",
        priority=8,  # Low priority
        params={"skill_key": "1"},
    )

    automation.add_custom_action(action_type="skill_use", priority=8, params={"skill_key": "2"})

    automation.add_custom_action(
        action_type="emergency_heal",
        priority=2,  # High priority
        params={"force_heal": True},
    )

    print("✅ Custom actions added to queue")

    # Show queue status
    queue_status = automation.get_queue_status()
    print(f"Action queue size: {queue_status['action_queue_size']}")

    # Get performance stats
    stats = automation.get_performance_stats()
    print(f"Thread state: {stats['thread_state']}")


def stress_test():
    """Run a stress test to evaluate threading performance."""

    print("\n🔥 Threading Stress Test")
    print("-" * 40)

    automation = MultiThreadedGameAutomation(
        debug_mode=False,  # Reduce logging overhead
        health_threshold=0.4,
        max_detection_threads=4,  # Use more threads for stress test
    )

    print("Running 30-second stress test...")
    print("This will test thread performance under load")

    start_time = time.time()
    test_duration = 30  # seconds

    # Simulate high activity by adding many actions
    action_count = 0

    try:
        while time.time() - start_time < test_duration:
            # Add actions rapidly
            automation.add_custom_action(
                action_type="health_potion", priority=5, params={"health_percentage": 0.5}
            )
            action_count += 1

            # Brief pause to simulate realistic workload
            time.sleep(0.01)

            # Show progress every 5 seconds
            elapsed = time.time() - start_time
            if elapsed % 5 < 0.02:  # Approximately every 5 seconds
                queue_status = automation.get_queue_status()
                print(
                    f"   {elapsed:.0f}s: Added {action_count} actions, "
                    f"Queue: {queue_status['action_queue_size']}"
                )

    except KeyboardInterrupt:
        print("\nStress test interrupted")

    # Final statistics
    total_time = time.time() - start_time
    stats = automation.get_performance_stats()

    print("\n📊 Stress Test Results:")
    print(f"   Duration: {total_time:.1f}s")
    print(f"   Actions added: {action_count}")
    print(f"   Actions/sec added: {action_count / total_time:.1f}")
    print("   Final queue sizes:")

    final_queues = automation.get_queue_status()
    for queue_name, size in final_queues.items():
        print(f"     {queue_name}: {size}")


def compare_thread_counts():
    """Compare performance with different thread counts."""

    print("\n⚖️  Thread Count Comparison")
    print("-" * 40)

    thread_counts = [1, 2, 3, 4]
    results = {}

    for thread_count in thread_counts:
        print(f"Testing with {thread_count} detection threads...")

        automation = MultiThreadedGameAutomation(
            debug_mode=False, max_detection_threads=thread_count
        )

        # Simulate some workload
        start_time = time.time()

        # Add actions for 5 seconds
        actions_added = 0
        while time.time() - start_time < 5:
            automation.add_custom_action(
                action_type="health_potion", priority=5, params={"health_percentage": 0.3}
            )
            actions_added += 1
            time.sleep(0.001)  # Small delay

        test_time = time.time() - start_time
        stats = automation.get_performance_stats()

        results[thread_count] = {
            "actions_per_second": actions_added / test_time,
            "test_duration": test_time,
            "final_queue_size": automation.get_queue_status()["action_queue_size"],
        }

        print(
            f"   {actions_added} actions in {test_time:.2f}s "
            f"({actions_added / test_time:.1f} actions/sec)"
        )

    print("\n📊 Thread Count Comparison Results:")
    for threads, result in results.items():
        print(f"   {threads} threads: {result['actions_per_second']:.1f} actions/sec")

    # Find optimal thread count
    best_threads = max(results.keys(), key=lambda k: results[k]["actions_per_second"])
    print(f"\n🏆 Optimal thread count: {best_threads}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "demo":
            demo_custom_actions()
        elif command == "stress":
            stress_test()
        elif command == "compare":
            compare_thread_counts()
        elif command == "help":
            print("Available commands:")
            print("  python multi_threaded_usage.py        - Run main automation")
            print("  python multi_threaded_usage.py demo   - Demo custom actions")
            print("  python multi_threaded_usage.py stress - Run stress test")
            print("  python multi_threaded_usage.py compare - Compare thread counts")
            print("  python multi_threaded_usage.py help   - Show this help")
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' for available commands")
    else:
        main()
