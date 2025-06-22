"""Ultra-fast health detection with optimized multiprocessing architecture.

This implementation provides sub-50ms health detection response times using
dedicated processes for health monitoring, emergency actions, and coordination.
"""

import argparse
import logging
import multiprocessing as mp
import queue
import signal
import sys
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_warrior.automation import GameAutomation
from auto_warrior.constants import (
    AUTHOR,
    CRITICAL_HEALTH_THRESHOLD,
    DEFAULT_HEALTH_THRESHOLD,
    LICENSE,
    LOW_HEALTH_THRESHOLD,
    VERSION,
)
from auto_warrior.exceptions import AutoSnakeError


class Priority(IntEnum):
    """Action priority levels for emergency response."""

    EMERGENCY_HEALTH = 1  # Critical health (0-15%)
    CRITICAL_HEALTH = 2  # Critical health (15-20%)
    LOW_HEALTH = 3  # Low health (20-40%)
    MEDIUM_HEALTH = 4  # Medium health (40-70%)
    MANA_POTION = 5  # Mana management
    SKILL_USAGE = 6  # Skill usage
    NORMAL_MONITORING = 7  # Normal monitoring tasks


@dataclass
class HealthAction:
    """Health-related action with priority and timing."""

    priority: Priority
    action_type: str
    health_percentage: float
    timestamp: float
    is_emergency: bool = False


@dataclass
class PerformanceStats:
    """Performance monitoring statistics."""

    health_fps: float = 0.0
    action_response_time: float = 0.0
    emergency_count: int = 0
    total_health_checks: int = 0
    avg_template_match_time: float = 0.0


class FastHealthMonitor:
    """Ultra-fast health monitoring with sub-50ms emergency response."""

    def __init__(self, debug_mode: bool = False, images_path: Optional[Path] = None):
        self.debug_mode = debug_mode
        self.images_path = images_path

        # Multiprocessing setup
        self.manager = mp.Manager()

        # Shared state
        self.health_data = self.manager.dict(
            {
                "percentage": 1.0,
                "is_critical": False,
                "is_emergency": False,
                "is_empty": False,
                "last_update": time.time(),
                "monitor_count": 0,
                "consecutive_empty_count": 0,
                "last_heal_time": 0.0,
            }
        )

        self.performance_stats = self.manager.dict(
            {
                "health_fps": 0.0,
                "action_response_time": 0.0,
                "emergency_count": 0,
                "total_checks": 0,
                "avg_match_time": 0.0,
            }
        )

        # Events for coordination
        self.stop_event = mp.Event()
        self.emergency_event = mp.Event()
        self.health_recovered_event = mp.Event()

        # High-priority queues
        self.emergency_queue = mp.Queue(maxsize=20)  # Emergency actions only
        self.action_queue = mp.Queue(maxsize=50)  # All other actions

        # Process handles
        self.health_monitor_process = None
        self.emergency_handler_process = None
        self.action_processor_process = None

        # Performance tracking
        self.start_time = time.time()

    def start_fast_monitoring(self) -> None:
        """Start the ultra-fast health monitoring system."""
        print("🚀 Starting Ultra-Fast Health Monitoring System")
        print("   Target Health Monitor FPS: 25-30")
        print("   Emergency Response Target: <30ms")
        print("   Template Matching Optimization: Enabled")
        print("=" * 60)

        # Start health monitor (highest priority)
        self.health_monitor_process = mp.Process(
            target=self._health_monitor_worker, daemon=True, name="HealthMonitor"
        )
        self.health_monitor_process.start()

        # Start emergency handler (immediate response)
        self.emergency_handler_process = mp.Process(
            target=self._emergency_handler_worker, daemon=True, name="EmergencyHandler"
        )
        self.emergency_handler_process.start()

        # Start general action processor
        self.action_processor_process = mp.Process(
            target=self._action_processor_worker, daemon=True, name="ActionProcessor"
        )
        self.action_processor_process.start()

        # Allow processes to initialize
        time.sleep(1.0)
        print("✅ All monitoring processes started successfully")

    def _health_monitor_worker(self) -> None:
        """Dedicated worker for ultra-fast health monitoring at 25+ FPS."""
        # Import here to avoid multiprocessing issues
        from auto_warrior.health import HealthDetector
        from auto_warrior.screenshot import ScreenshotManager
        from auto_warrior.templates import TemplateManager

        # Initialize components with optimization
        screenshot_manager = ScreenshotManager(self.debug_mode, use_live_capture=True)
        template_manager = TemplateManager(self.images_path, self.debug_mode)
        template_manager.load_all_templates()
        health_detector = HealthDetector(template_manager, self.debug_mode)

        print(f"🩺 Health Monitor Worker Started (PID: {mp.current_process().pid})")

        # Performance tracking
        monitor_count = 0
        fps_window = []
        template_match_times = []
        target_interval = 1 / 25.0  # 25 FPS target

        while not self.stop_event.is_set():
            cycle_start = time.time()

            try:
                # Fast screenshot capture with timing
                screenshot_start = time.time()

                if screenshot_manager.live_capture:
                    screenshot_cv = screenshot_manager.live_capture.capture_live()
                else:
                    screenshot = screenshot_manager.take_screenshot()
                    screenshot_cv = screenshot_manager.screenshot_to_cv2(screenshot)

                screenshot_time = time.time() - screenshot_start

                # Fast health detection with timing
                detection_start = time.time()

                # Check for empty health first (most critical)
                is_health_empty = health_detector.is_health_empty(screenshot_cv)
                if is_health_empty:
                    health_percentage = 0.0  # Override to 0% if empty detected
                    # Track consecutive empty detections
                    consecutive_empty = self.health_data.get("consecutive_empty_count", 0) + 1
                    self.health_data["consecutive_empty_count"] = consecutive_empty

                    # If we've been empty for too long, consider character dead
                    if consecutive_empty >= 5:  # 5 consecutive empty detections (~0.2 seconds)
                        is_emergency = False  # Stop emergency healing
                        is_critical = False  # Character is likely dead
                    else:
                        is_emergency = True
                        is_critical = True
                else:
                    # Reset consecutive empty count when health is detected
                    self.health_data["consecutive_empty_count"] = 0
                    health_percentage = health_detector.get_health_percentage(screenshot_cv)
                    # Immediate health analysis
                    is_emergency = health_percentage <= 0.15  # 15% emergency threshold
                    is_critical = health_percentage <= CRITICAL_HEALTH_THRESHOLD

                detection_time = time.time() - detection_start

                # Track template matching performance
                template_match_times.append(detection_time)
                if len(template_match_times) > 100:  # Keep last 100 measurements
                    template_match_times.pop(0)

                # Update shared state immediately
                current_time = time.time()
                self.health_data.update(
                    {
                        "percentage": health_percentage,
                        "is_emergency": is_emergency,
                        "is_critical": is_critical,
                        "is_empty": is_health_empty,
                        "last_update": current_time,
                        "monitor_count": monitor_count,
                    }
                )

                # Handle emergency situations immediately
                if is_emergency:
                    # Check if we're stuck in healing loop (empty health for too long)
                    last_heal_time = self.health_data.get("last_heal_time", 0.0)
                    if is_health_empty and (current_time - last_heal_time > 3.0):
                        # Stop emergency healing after 3 seconds of failed attempts
                        consecutive_empty = self.health_data.get("consecutive_empty_count", 0)
                        if consecutive_empty >= 10:  # ~0.4 seconds of empty health
                            print("💀 Character appears to be dead - stopping emergency healing")
                            self.emergency_event.clear()
                        else:
                            self.emergency_event.set()
                            self._queue_emergency_action(health_percentage, current_time)
                            self.health_data["last_heal_time"] = current_time
                    else:
                        self.emergency_event.set()
                        self._queue_emergency_action(health_percentage, current_time)
                        self.health_data["last_heal_time"] = current_time

                elif is_critical:
                    self._queue_critical_action(health_percentage, current_time)

                elif health_percentage <= LOW_HEALTH_THRESHOLD:
                    self._queue_normal_action(health_percentage, current_time)

                else:
                    # Clear emergency state for good health
                    self.emergency_event.clear()
                    if health_percentage > 0.8:  # 80% recovery threshold
                        self.health_recovered_event.set()

                monitor_count += 1

                # Calculate and update FPS every 25 iterations (1 second at 25 FPS)
                if monitor_count % 25 == 0:
                    current_fps = self._calculate_fps(fps_window, current_time)
                    avg_match_time = sum(template_match_times) / len(template_match_times)

                    self.performance_stats.update(
                        {
                            "health_fps": current_fps,
                            "total_checks": monitor_count,
                            "avg_match_time": avg_match_time * 1000,  # Convert to ms
                        }
                    )

                    if self.debug_mode:
                        print(
                            f"🩺 Health Monitor: {current_fps:.1f} FPS | "
                            f"Health: {health_percentage:.1%} | "
                            f"Match Time: {avg_match_time * 1000:.1f}ms"
                        )

                # Precise timing control for consistent FPS
                cycle_time = time.time() - cycle_start
                sleep_time = max(0.001, target_interval - cycle_time)
                time.sleep(sleep_time)

                # Track FPS
                fps_window.append(current_time)
                if len(fps_window) > 30:  # Keep last 30 measurements
                    fps_window.pop(0)

            except Exception as e:
                if self.debug_mode:
                    print(f"❌ Health monitor error: {e}")
                time.sleep(0.01)  # Brief pause on error

    def _queue_emergency_action(self, health_percentage: float, timestamp: float) -> None:
        """Queue emergency health action with highest priority."""
        action = HealthAction(
            priority=Priority.EMERGENCY_HEALTH,
            action_type="emergency_heal",
            health_percentage=health_percentage,
            timestamp=timestamp,
            is_emergency=True,
        )

        try:
            self.emergency_queue.put_nowait(action)
        except queue.Full:
            # Emergency queue full - clear oldest and add new
            try:
                self.emergency_queue.get_nowait()
                self.emergency_queue.put_nowait(action)
            except queue.Empty:
                pass

    def _queue_critical_action(self, health_percentage: float, timestamp: float) -> None:
        """Queue critical health action."""
        action = HealthAction(
            priority=Priority.CRITICAL_HEALTH,
            action_type="critical_heal",
            health_percentage=health_percentage,
            timestamp=timestamp,
        )

        try:
            self.action_queue.put_nowait(action)
        except queue.Full:
            pass  # Skip if queue full for non-emergency

    def _queue_normal_action(self, health_percentage: float, timestamp: float) -> None:
        """Queue normal health action."""
        if health_percentage <= LOW_HEALTH_THRESHOLD:
            action = HealthAction(
                priority=Priority.LOW_HEALTH,
                action_type="low_heal",
                health_percentage=health_percentage,
                timestamp=timestamp,
            )

            try:
                self.action_queue.put_nowait(action)
            except queue.Full:
                pass

    def _emergency_handler_worker(self) -> None:
        """Dedicated worker for handling emergency health actions with minimal latency."""
        from auto_warrior.input_control import InputController
        from auto_warrior.potion import PotionManager
        from auto_warrior.templates import TemplateManager

        # Initialize emergency response components
        input_controller = InputController(self.debug_mode)
        template_manager = TemplateManager(self.images_path, self.debug_mode)
        template_manager.load_all_templates()
        potion_manager = PotionManager(input_controller, self.debug_mode)

        print(f"🚨 Emergency Handler Worker Started (PID: {mp.current_process().pid})")

        emergency_count = 0
        response_times = []

        while not self.stop_event.is_set():
            try:
                # Wait for emergency actions with minimal timeout
                action = self.emergency_queue.get(timeout=0.05)

                response_start = time.time()

                if action.action_type == "emergency_heal":
                    emergency_count += 1

                    # Check if character might be dead (repeated 0% health)
                    if action.health_percentage == 0.0 and emergency_count > 5:
                        print("💀 Repeated emergency heals at 0% health - character may be dead")
                        # Continue healing but warn user
                        print(
                            f"🚨 EMERGENCY HEAL #{emergency_count}! Health: {action.health_percentage:.1%} (Death suspected)"
                        )
                    else:
                        print(
                            f"🚨 EMERGENCY HEAL #{emergency_count}! Health: {action.health_percentage:.1%}"
                        )

                    # Use maximum healing immediately
                    potion_manager.use_health_potion(action.health_percentage, force_heal=True)

                # Track response time
                response_time = (time.time() - response_start) * 1000  # Convert to ms
                response_times.append(response_time)

                if len(response_times) > 50:  # Keep last 50 measurements
                    response_times.pop(0)

                avg_response_time = sum(response_times) / len(response_times)

                self.performance_stats.update(
                    {"action_response_time": avg_response_time, "emergency_count": emergency_count}
                )

                if self.debug_mode:
                    print(
                        f"💊 Emergency response time: {response_time:.1f}ms (avg: {avg_response_time:.1f}ms)"
                    )

            except queue.Empty:
                continue
            except Exception as e:
                if self.debug_mode:
                    print(f"❌ Emergency handler error: {e}")
                time.sleep(0.01)

    def _action_processor_worker(self) -> None:
        """Worker for processing non-emergency health and other actions."""
        from auto_warrior.input_control import InputController
        from auto_warrior.potion import PotionManager
        from auto_warrior.templates import TemplateManager

        # Initialize components
        input_controller = InputController(self.debug_mode)
        template_manager = TemplateManager(self.images_path, self.debug_mode)
        template_manager.load_all_templates()
        potion_manager = PotionManager(input_controller, self.debug_mode)

        print(f"⚡ Action Processor Worker Started (PID: {mp.current_process().pid})")

        while not self.stop_event.is_set():
            try:
                # Process non-emergency actions
                action = self.action_queue.get(timeout=0.1)
                
                #TODO: Implement character respawn logic
                # confirm character is alive before performing actions
                if not self.character.is_alive():
                    print("💀 Character is dead!")
                    # call respawn module to revive
                    self.character.respawn()
                    continue

                if action.action_type == "critical_heal":
                    print(f"⚠️ Critical heal - Health: {action.health_percentage:.1%}")
                    potion_manager.use_health_potion(action.health_percentage)
                #FIX: this is called when the health is empty
                # so fix this by checking the empty and verify character is dead or not
                # use the respawn module to respawn the character etc.
                elif action.action_type == "low_heal":
                    print(f"💊 Low health heal - Health: {action.health_percentage:.1%}")                    
                    potion_manager.use_health_potion(action.health_percentage)
                    
                    

            except queue.Empty:
                continue
            except Exception as e:
                if self.debug_mode:
                    print(f"❌ Action processor error: {e}")
                time.sleep(0.01)

    def _calculate_fps(self, fps_window: list, current_time: float) -> float:
        """Calculate current FPS from timing window."""
        if len(fps_window) < 2:
            return 0.0

        time_span = current_time - fps_window[0]
        if time_span <= 0:
            return 0.0

        return len(fps_window) / time_span

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status and performance metrics."""
        health_status = dict(self.health_data)
        performance = dict(self.performance_stats)

        return {
            **health_status,
            "performance": performance,
            "uptime": time.time() - self.start_time,
            "is_emergency_active": self.emergency_event.is_set(),
        }

    def is_emergency(self) -> bool:
        """Check if there's a current health emergency."""
        return self.emergency_event.is_set()

    def stop_monitoring(self) -> None:
        """Stop all monitoring processes gracefully."""
        print("🛑 Stopping ultra-fast health monitoring...")

        self.stop_event.set()

        # Stop processes with timeout
        processes = [
            ("Health Monitor", self.health_monitor_process),
            ("Emergency Handler", self.emergency_handler_process),
            ("Action Processor", self.action_processor_process),
        ]

        for name, process in processes:
            if process and process.is_alive():
                process.join(timeout=2)
                if process.is_alive():
                    print(f"⚠️ Force terminating {name} process")
                    process.terminate()
                    process.join(timeout=1)

        print("✅ All monitoring processes stopped")


class OptimizedGameAutomation(GameAutomation):
    """Game automation enhanced with ultra-fast health monitoring."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize fast health monitor
        self.fast_health_monitor = FastHealthMonitor(
            debug_mode=self.debug_mode, images_path=self.template_manager.images_path
        )

        self.last_status_print = time.time()

    def run_automation(self) -> None:
        """Run optimized automation with ultra-fast health detection."""
        try:
            print("🎮 Starting Optimized Game Automation...")

            # Start ultra-fast health monitoring
            self.fast_health_monitor.start_fast_monitoring()

            print("⏱️ Initialization complete - entering main automation loop")
            print("💡 Health monitoring running at 25+ FPS in dedicated processes")
            print("🚨 Emergency response time: <30ms")
            print("=" * 60)

            # Main automation loop (reduced frequency since health is handled separately)
            while True:
                loop_start = time.time()

                # Get fast health status
                health_status = self.fast_health_monitor.get_health_status()

                # Only do heavy operations if not in emergency
                if not self.fast_health_monitor.is_emergency():
                    self._handle_non_critical_automation(health_status)

                # Print status less frequently
                if time.time() - self.last_status_print >= 3.0:
                    self._print_optimized_status(health_status)
                    self.last_status_print = time.time()

                # Dynamic loop timing based on emergency status
                if self.fast_health_monitor.is_emergency():
                    time.sleep(0.1)  # 10 FPS during emergency
                else:
                    time.sleep(0.3)  # 3.3 FPS for normal operations

                # Performance logging
                if self.debug_mode:
                    loop_time = time.time() - loop_start
                    if loop_time > 0.5:  # Log slow loops
                        print(f"⚠️ Slow main loop: {loop_time * 1000:.1f}ms")

        except KeyboardInterrupt:
            print("\n🛑 Automation stopped by user")
        except Exception as e:
            print(f"❌ Automation error: {e}")
            if self.debug_mode:
                import traceback

                traceback.print_exc()
        finally:
            self.fast_health_monitor.stop_monitoring()

    def _handle_non_critical_automation(self, health_status: Dict[str, Any]) -> None:
        """Handle non-critical automation tasks (mana, skills, respawn detection)."""
        try:
            # Only take screenshot if not in emergency (saves CPU)
            screenshot = self.screenshot_manager.take_screenshot()
            screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)

            # Mana monitoring (less critical than health)
            mana_percent = self.mana_detector.get_mana_percentage(screenshot_cv)
            if mana_percent < 0.4:  # 40% mana threshold
                self.potion_manager.use_mana_potion(mana_percent)

            # Skill usage (when health is safe)
            if health_status.get("percentage", 0) > 0.5:  # Only use skills when health >50%
                self._handle_skill_usage()

            # Respawn detection (important but not time-critical)
            # Check for respawn button if health has been empty for a while
            if health_status.get("consecutive_empty_count", 0) >= 10:
                from auto_warrior.input_control import ClickController
                from auto_warrior.respawn import RespawnDetector

                click_controller = ClickController(self.debug_mode)
                respawn_detector = RespawnDetector(
                    self.template_manager, click_controller, self.debug_mode
                )

                # Try to click respawn button
                respawn_clicked = respawn_detector.click_respawn_button(screenshot_cv)
                if respawn_clicked:
                    print("🔄 Respawn button clicked - character should revive soon")
                    # Reset emergency counters
                    self.fast_health_monitor.health_data["consecutive_empty_count"] = 0
                    time.sleep(2.0)  # Wait for respawn

        except Exception as e:
            if self.debug_mode:
                print(f"❌ Non-critical automation error: {e}")

    def _print_optimized_status(self, health_status: Dict[str, Any]) -> None:
        """Print optimized status with performance metrics."""
        health_pct = health_status.get("percentage", 0) * 100
        performance = health_status.get("performance", {})

        fps = performance.get("health_fps", 0)
        response_time = performance.get("action_response_time", 0)
        emergency_count = performance.get("emergency_count", 0)
        match_time = performance.get("avg_match_time", 0)

        # Status icon based on health
        if health_status.get("is_emergency"):
            icon = "🚨"
            status = "EMERGENCY"
        elif health_status.get("is_critical"):
            icon = "⚠️"
            status = "CRITICAL"
        elif health_pct < 70:
            icon = "💛"
            status = "LOW"
        else:
            icon = "💚"
            status = "GOOD"

        print(
            f"{icon} Health: {health_pct:.1f}% ({status}) | "
            f"Monitor: {fps:.1f} FPS | "
            f"Response: {response_time:.1f}ms | "
            f"Match: {match_time:.1f}ms | "
            f"Emergencies: {emergency_count}"
        )


def main() -> None:
    """Main entry point for optimized automation."""
    parser = argparse.ArgumentParser(
        description="Auto Snake - Ultra-Fast Health Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Ultra-Fast Health Detection Features:
  • 25+ FPS dedicated health monitoring
  • <30ms emergency response time
  • Multiprocessing for true parallelism
  • Priority-based action system
  • Real-time performance monitoring

Examples:
  %(prog)s                              # Run with default settings
  %(prog)s --debug                      # Enable debug mode with detailed logging
  %(prog)s --health-threshold 0.8       # Set health threshold to 80%%
  %(prog)s --images-path ./my_images    # Use custom images directory

Version: {VERSION}
Author: {AUTHOR}
License: {LICENSE}
        """,
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with detailed performance logging"
    )

    parser.add_argument(
        "--images-path",
        type=Path,
        metavar="PATH",
        help="Path to directory containing template images",
    )

    parser.add_argument(
        "--health-threshold",
        type=float,
        default=DEFAULT_HEALTH_THRESHOLD,
        metavar="THRESHOLD",
        help=f"Health threshold for normal potion usage (0.0-1.0, default: {DEFAULT_HEALTH_THRESHOLD})",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # Validate arguments
    if args.health_threshold and not 0.0 <= args.health_threshold <= 1.0:
        print("❌ Health threshold must be between 0.0 and 1.0")
        sys.exit(1)

    if args.images_path and not args.images_path.exists():
        print(f"❌ Images path does not exist: {args.images_path}")
        sys.exit(1)

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # Print startup banner
    print(f"Auto Snake Ultra-Fast Health Detection v{VERSION}")
    print(f"Author: {AUTHOR}")
    print(f"License: {LICENSE}")
    print("=" * 60)
    print(f"🎯 Health Threshold: {args.health_threshold:.1%}")
    print(f"🐛 Debug Mode: {'ENABLED' if args.debug else 'DISABLED'}")
    if args.images_path:
        print(f"📁 Images Path: {args.images_path}")
    print("=" * 60)

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Graceful shutdown requested...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create optimized automation
        automation = OptimizedGameAutomation(
            debug_mode=args.debug,
            images_path=args.images_path,
            health_threshold=args.health_threshold,
        )

        # Run optimized automation
        automation.run_automation()

    except AutoSnakeError as e:
        print(f"❌ Automation error: {e}")
        if e.details:
            print(f"Details: {e.details}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
