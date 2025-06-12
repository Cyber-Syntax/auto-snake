"""Multi-threaded automation system for improved performance."""

import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from auto_snake.automation import AutomationState, GameAutomation
from auto_snake.constants import (
    ACTION_TIMEOUT,
    AUTOMATION_LOOP_DELAY,
    DETECTION_THREAD_COUNT,
    DETECTION_TIMEOUT,
    PERFORMANCE_LOG_INTERVAL,
    PRIORITY_EMERGENCY_HEAL,
    PRIORITY_NORMAL_HEAL,
    PRIORITY_RESPAWN,
    SCREENSHOT_QUEUE_SIZE,
    SCREENSHOT_THREAD_DELAY,
    SCREENSHOT_TIMEOUT,
)
from auto_snake.exceptions import AutoSnakeError

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result from a detection operation."""

    timestamp: float
    health_percentage: float
    is_health_empty: bool
    respawn_needed: bool
    emergency_healing_needed: bool
    screenshot_id: int
    processing_time_ms: float = 0.0


@dataclass
class ActionRequest:
    """Request for an action to be performed."""

    action_type: str  # 'health_potion', 'emergency_heal', 'respawn_click', 'skill_use'
    priority: int  # Lower number = higher priority
    params: Dict[str, Any]
    timestamp: float


class ThreadSafeState:
    """Thread-safe state management for automation."""

    def __init__(self):
        self._lock = threading.RLock()
        self._state = AutomationState()
        self._running = True

    def __getattr__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        with self._lock:
            return getattr(self._state, name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            with self._lock:
                setattr(self._state, name, value)

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def stop(self):
        with self._lock:
            self._running = False
            self._state.automation_running = False

    def get_state_dict(self) -> Dict[str, Any]:
        """Get a snapshot of the current state."""
        with self._lock:
            return {
                "automation_running": self._state.automation_running,
                "loop_count": self._state.loop_count,
                "is_dead": self._state.is_dead,
                "emergency_healing_active": self._state.emergency_healing_active,
                "empty_health_detected": self._state.empty_health_detected,
                "respawn_wait_start": self._state.respawn_wait_start,
                "post_respawn_heal_time": self._state.post_respawn_heal_time,
            }


class ScreenshotThread(threading.Thread):
    """Dedicated thread for continuous screenshot capture."""

    def __init__(
        self,
        screenshot_manager,
        screenshot_queue: queue.Queue,
        thread_state: ThreadSafeState,
        debug_mode: bool = False,
    ):
        super().__init__(name="ScreenshotThread", daemon=True)
        self.screenshot_manager = screenshot_manager
        self.screenshot_queue = screenshot_queue
        self.thread_state = thread_state
        self.debug_mode = debug_mode
        self.screenshot_counter = 0
        self.error_count = 0
        self.last_error_time = 0

    def run(self):
        """Main screenshot capture loop."""
        logger.info("Screenshot thread started")

        while self.thread_state.is_running():
            try:
                start_time = time.time()

                # Capture screenshot
                screenshot = self.screenshot_manager.take_screenshot()
                screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)

                self.screenshot_counter += 1

                # Create screenshot package
                screenshot_data = {
                    "screenshot": screenshot,
                    "screenshot_cv": screenshot_cv,
                    "timestamp": start_time,
                    "id": self.screenshot_counter,
                }

                # Add to queue (non-blocking)
                try:
                    self.screenshot_queue.put_nowait(screenshot_data)
                except queue.Full:
                    # Remove oldest screenshot if queue is full
                    try:
                        self.screenshot_queue.get_nowait()
                        self.screenshot_queue.put_nowait(screenshot_data)
                    except queue.Empty:
                        pass

                # Control capture rate
                elapsed = time.time() - start_time
                sleep_time = max(0, SCREENSHOT_THREAD_DELAY - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

                if self.debug_mode and self.screenshot_counter % 50 == 0:
                    logger.debug(
                        f"Screenshot thread: captured {self.screenshot_counter} screenshots"
                    )

                # Reset error count on success
                self.error_count = 0

            except Exception as e:
                self.error_count += 1
                current_time = time.time()

                # Log error only once per minute to avoid spam
                if current_time - self.last_error_time > 60:
                    logger.error(f"Screenshot thread error #{self.error_count}: {e}")
                    self.last_error_time = current_time

                # Exponential backoff on errors
                error_delay = min(0.5 * (2 ** min(self.error_count, 5)), 5.0)
                time.sleep(error_delay)

        logger.info(f"Screenshot thread stopped after {self.screenshot_counter} screenshots")


class HealthDetectionThread(threading.Thread):
    """Dedicated thread for health monitoring and detection."""

    def __init__(
        self,
        health_detector,
        screenshot_queue: queue.Queue,
        detection_queue: queue.Queue,
        thread_state: ThreadSafeState,
        debug_mode: bool = False,
    ):
        super().__init__(name="HealthDetectionThread", daemon=True)
        self.health_detector = health_detector
        self.screenshot_queue = screenshot_queue
        self.detection_queue = detection_queue
        self.thread_state = thread_state
        self.debug_mode = debug_mode
        self.processed_count = 0

    def run(self):
        """Main health detection loop."""
        logger.info("Health detection thread started")

        while self.thread_state.is_running():
            try:
                # Get latest screenshot with timeout
                try:
                    screenshot_data = self.screenshot_queue.get(timeout=SCREENSHOT_TIMEOUT)
                except queue.Empty:
                    continue

                # Perform health detection
                start_time = time.time()
                screenshot_cv = screenshot_data["screenshot_cv"]

                health_percentage = self.health_detector.get_health_percentage(screenshot_cv)
                is_health_empty = self.health_detector.is_health_empty(screenshot_cv)

                processing_time = (time.time() - start_time) * 1000

                # Create detection result
                result = DetectionResult(
                    timestamp=screenshot_data["timestamp"],
                    health_percentage=health_percentage,
                    is_health_empty=is_health_empty,
                    respawn_needed=False,  # Will be set by respawn detection
                    emergency_healing_needed=is_health_empty,
                    screenshot_id=screenshot_data["id"],
                    processing_time_ms=processing_time,
                )

                # Send result to main thread
                try:
                    self.detection_queue.put_nowait(result)
                except queue.Full:
                    # Remove oldest result if queue is full
                    try:
                        self.detection_queue.get_nowait()
                        self.detection_queue.put_nowait(result)
                    except queue.Empty:
                        pass

                self.processed_count += 1

                if self.debug_mode and self.processed_count % 100 == 0:
                    logger.debug(
                        f"Health detection: processed {self.processed_count} screenshots, "
                        f"avg processing time: {processing_time:.2f}ms"
                    )

            except Exception as e:
                logger.error(f"Health detection thread error: {e}")
                time.sleep(0.1)

        logger.info(
            f"Health detection thread stopped after processing {self.processed_count} screenshots"
        )


class RespawnDetectionThread(threading.Thread):
    """Dedicated thread for respawn detection."""

    def __init__(
        self,
        respawn_detector,
        screenshot_queue: queue.Queue,
        detection_queue: queue.Queue,
        thread_state: ThreadSafeState,
        debug_mode: bool = False,
    ):
        super().__init__(name="RespawnDetectionThread", daemon=True)
        self.respawn_detector = respawn_detector
        self.screenshot_queue = screenshot_queue
        self.detection_queue = detection_queue
        self.thread_state = thread_state
        self.debug_mode = debug_mode
        self.processed_count = 0

    def run(self):
        """Main respawn detection loop."""
        logger.info("Respawn detection thread started")

        while self.thread_state.is_running():
            try:
                # Get screenshot (with shorter timeout since health detection is primary)
                try:
                    screenshot_data = self.screenshot_queue.get(timeout=DETECTION_TIMEOUT)
                except queue.Empty:
                    continue

                screenshot_cv = screenshot_data["screenshot_cv"]

                # Check for respawn button
                respawn_needed = self.respawn_detector.detect_respawn_button(screenshot_cv)

                if respawn_needed:
                    # Create high-priority detection result for respawn
                    result = DetectionResult(
                        timestamp=screenshot_data["timestamp"],
                        health_percentage=0.0,
                        is_health_empty=True,
                        respawn_needed=True,
                        emergency_healing_needed=False,
                        screenshot_id=screenshot_data["id"],
                    )

                    # Send urgent result
                    try:
                        self.detection_queue.put_nowait(result)
                    except queue.Full:
                        # For respawn, we force the queue
                        try:
                            self.detection_queue.get_nowait()
                            self.detection_queue.put_nowait(result)
                        except queue.Empty:
                            pass

                    if self.debug_mode:
                        logger.debug("Respawn button detected!")

                self.processed_count += 1

            except Exception as e:
                logger.error(f"Respawn detection thread error: {e}")
                time.sleep(0.1)

        logger.info(
            f"Respawn detection thread stopped after processing {self.processed_count} screenshots"
        )


class MultiThreadedGameAutomation(GameAutomation):
    """Multi-threaded version of GameAutomation for improved performance."""

    def __init__(
        self,
        debug_mode: bool = False,
        images_path: Path | str | None = None,
        health_threshold: float = 0.3,
        max_detection_threads: int = DETECTION_THREAD_COUNT,
    ):
        """Initialize multi-threaded automation.

        Args:
            debug_mode: Enable debug logging
            images_path: Path to template images
            health_threshold: Health threshold for potion usage
            max_detection_threads: Maximum number of detection threads
        """
        super().__init__(debug_mode, images_path, health_threshold)

        # Thread-safe state
        self.thread_state = ThreadSafeState()

        # Thread communication queues
        self.screenshot_queue = queue.Queue(maxsize=SCREENSHOT_QUEUE_SIZE)
        self.detection_queue = queue.Queue(maxsize=50)
        self.action_queue = queue.PriorityQueue(maxsize=100)

        # Threads
        self.screenshot_thread = None
        self.health_detection_thread = None
        self.respawn_detection_thread = None
        self.thread_pool = ThreadPoolExecutor(max_workers=max_detection_threads)

        # Performance tracking
        self.performance_stats = {
            "screenshots_processed": 0,
            "detections_processed": 0,
            "actions_executed": 0,
            "start_time": None,
            "last_performance_log": 0,
        }

    def run_automation(self) -> None:
        """Run multi-threaded automation."""
        print("🚀 Starting multi-threaded automation system...")
        self._print_automation_info()

        self.performance_stats["start_time"] = time.time()
        self.performance_stats["last_performance_log"] = time.time()

        try:
            self._start_threads()
            self._main_coordination_loop()
        except KeyboardInterrupt:
            print("\n⏹️  Automation stopped by user")
        except Exception as e:
            logger.error(f"Multi-threaded automation failed: {e}")
            raise AutoSnakeError("Multi-threaded automation failed", str(e)) from e
        finally:
            self._stop_threads()
            self._print_performance_stats()

    def _start_threads(self):
        """Start all worker threads."""
        logger.info("Starting worker threads...")

        # Screenshot capture thread
        self.screenshot_thread = ScreenshotThread(
            self.screenshot_manager, self.screenshot_queue, self.thread_state, self.debug_mode
        )
        self.screenshot_thread.start()

        # Health detection thread
        self.health_detection_thread = HealthDetectionThread(
            self.health_detector,
            self.screenshot_queue,
            self.detection_queue,
            self.thread_state,
            self.debug_mode,
        )
        self.health_detection_thread.start()

        # Respawn detection thread
        self.respawn_detection_thread = RespawnDetectionThread(
            self.respawn_detector,
            self.screenshot_queue,
            self.detection_queue,
            self.thread_state,
            self.debug_mode,
        )
        self.respawn_detection_thread.start()

        # Allow threads to initialize
        time.sleep(1.0)
        logger.info("All worker threads started successfully")

    def _main_coordination_loop(self):
        """Main coordination loop that processes detection results and executes actions."""
        logger.info("Starting main coordination loop")

        while self.thread_state.is_running() and self.automation_controller.is_automation_running():
            try:
                # Process detection results
                self._process_detection_results()

                # Execute pending actions
                self._execute_pending_actions()

                # Handle timing-based logic (respawn waits, etc.)
                self._handle_timing_logic()

                # Log performance stats periodically
                self._log_performance_stats()

                # Brief sleep to prevent busy waiting
                time.sleep(AUTOMATION_LOOP_DELAY / 2)  # Faster response time

            except Exception as e:
                logger.error(f"Main coordination loop error: {e}")
                time.sleep(0.1)

        logger.info("Main coordination loop stopped")

    def _process_detection_results(self):
        """Process results from detection threads."""
        try:
            while True:
                result = self.detection_queue.get_nowait()
                self.performance_stats["detections_processed"] += 1

                # Handle respawn detection (highest priority)
                if result.respawn_needed:
                    self._handle_respawn_detection(result)
                    continue

                # Handle emergency healing
                if (
                    result.emergency_healing_needed
                    and not self.thread_state.emergency_healing_active
                ):
                    self._handle_emergency_healing_detection(result)
                    continue

                # Handle normal health monitoring
                self._handle_health_monitoring_result(result)

        except queue.Empty:
            pass  # No more results to process

    def _handle_respawn_detection(self, result: DetectionResult):
        """Handle respawn detection result."""
        if not self.thread_state.is_dead:
            print("💀 Character death detected - initiating respawn sequence")
            self.thread_state.is_dead = True
            self.thread_state.respawn_wait_start = time.time()

            # Queue respawn action
            action = ActionRequest(
                action_type="respawn_click",
                priority=PRIORITY_RESPAWN,
                params={"result": result},
                timestamp=result.timestamp,
            )
            self.action_queue.put((action.priority, time.time(), action))

    def _handle_emergency_healing_detection(self, result: DetectionResult):
        """Handle emergency healing detection."""
        print("⚠️  Emergency healing needed!")
        self.thread_state.emergency_healing_active = True
        self.thread_state.emergency_healing_start_time = time.time()

        # Queue emergency healing action
        action = ActionRequest(
            action_type="emergency_heal",
            priority=PRIORITY_EMERGENCY_HEAL,
            params={"result": result},
            timestamp=result.timestamp,
        )
        self.action_queue.put((action.priority, time.time(), action))

    def _handle_health_monitoring_result(self, result: DetectionResult):
        """Handle normal health monitoring result."""
        if result.health_percentage < self.potion_manager.health_threshold:
            # Queue health potion action
            action = ActionRequest(
                action_type="health_potion",
                priority=PRIORITY_NORMAL_HEAL,
                params={"health_percentage": result.health_percentage},
                timestamp=result.timestamp,
            )
            self.action_queue.put((action.priority, time.time(), action))

    def _execute_pending_actions(self):
        """Execute pending actions from the action queue."""
        try:
            while True:
                priority, queued_time, action = self.action_queue.get_nowait()

                # Check if action is too old (avoid stale actions)
                if time.time() - queued_time > ACTION_TIMEOUT:
                    if self.debug_mode:
                        logger.debug(f"Skipping stale action: {action.action_type}")
                    continue

                self._execute_action(action)
                self.performance_stats["actions_executed"] += 1

        except queue.Empty:
            pass  # No more actions to execute

    def _execute_action(self, action: ActionRequest):
        """Execute a specific action."""
        try:
            if action.action_type == "health_potion":
                self.potion_manager.use_health_potion(
                    action.params["health_percentage"], emergency_mode=False
                )

            elif action.action_type == "emergency_heal":
                self.potion_manager.use_emergency_potions()

            elif action.action_type == "respawn_click":
                self._attempt_respawn_click(time.time())

            elif action.action_type == "skill_use":
                self.use_skill(action.params.get("skill_key", "1"))

            if self.debug_mode:
                logger.debug(f"Executed action: {action.action_type}")

        except Exception as e:
            logger.error(f"Failed to execute action {action.action_type}: {e}")

    def _handle_timing_logic(self):
        """Handle timing-based logic like respawn waits."""
        current_time = time.time()

        # Handle post-respawn healing
        if self.thread_state.post_respawn_heal_time:
            if self._handle_post_respawn_healing(current_time):
                return

        # Handle respawn waiting
        if self.thread_state.respawn_wait_start:
            self._handle_respawn_waiting(current_time)

    def _log_performance_stats(self):
        """Log performance statistics periodically."""
        current_time = time.time()
        if current_time - self.performance_stats["last_performance_log"] > PERFORMANCE_LOG_INTERVAL:
            if self.debug_mode:
                runtime = current_time - self.performance_stats["start_time"]
                logger.info(
                    f"Performance: {self.performance_stats['screenshots_processed']} screenshots, "
                    f"{self.performance_stats['detections_processed']} detections, "
                    f"{self.performance_stats['actions_executed']} actions in {runtime:.1f}s"
                )
            self.performance_stats["last_performance_log"] = current_time

    def _stop_threads(self):
        """Stop all worker threads."""
        logger.info("Stopping worker threads...")

        # Signal threads to stop
        self.thread_state.stop()

        # Wait for threads to finish
        threads = [
            self.screenshot_thread,
            self.health_detection_thread,
            self.respawn_detection_thread,
        ]

        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)
                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not stop gracefully")

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        logger.info("All worker threads stopped")

    def _print_performance_stats(self):
        """Print performance statistics."""
        if self.performance_stats["start_time"]:
            runtime = time.time() - self.performance_stats["start_time"]

            print("\n📊 Multi-threading Performance Stats:")
            print(f"   Runtime: {runtime:.1f}s")
            print(f"   Screenshots processed: {self.performance_stats['screenshots_processed']}")
            print(f"   Detections processed: {self.performance_stats['detections_processed']}")
            print(f"   Actions executed: {self.performance_stats['actions_executed']}")

            if runtime > 0:
                print(
                    f"   Screenshots/sec: {self.performance_stats['screenshots_processed'] / runtime:.1f}"
                )
                print(
                    f"   Detections/sec: {self.performance_stats['detections_processed'] / runtime:.1f}"
                )
                print(f"   Actions/sec: {self.performance_stats['actions_executed'] / runtime:.1f}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        runtime = 0
        if self.performance_stats["start_time"]:
            runtime = time.time() - self.performance_stats["start_time"]

        return {
            "runtime_seconds": runtime,
            "screenshots_processed": self.performance_stats["screenshots_processed"],
            "detections_processed": self.performance_stats["detections_processed"],
            "actions_executed": self.performance_stats["actions_executed"],
            "screenshots_per_second": self.performance_stats["screenshots_processed"]
            / max(runtime, 1),
            "detections_per_second": self.performance_stats["detections_processed"]
            / max(runtime, 1),
            "actions_per_second": self.performance_stats["actions_executed"] / max(runtime, 1),
            "thread_state": self.thread_state.get_state_dict()
            if hasattr(self.thread_state, "get_state_dict")
            else {},
        }

    def add_custom_action(self, action_type: str, priority: int, params: Dict[str, Any]):
        """Add a custom action to the queue."""
        action = ActionRequest(
            action_type=action_type, priority=priority, params=params, timestamp=time.time()
        )
        try:
            self.action_queue.put((action.priority, time.time(), action))
            if self.debug_mode:
                logger.debug(f"Added custom action: {action_type} with priority {priority}")
        except queue.Full:
            logger.warning(f"Action queue full, could not add action: {action_type}")

    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue sizes for monitoring."""
        return {
            "screenshot_queue_size": self.screenshot_queue.qsize(),
            "detection_queue_size": self.detection_queue.qsize(),
            "action_queue_size": self.action_queue.qsize(),
        }
