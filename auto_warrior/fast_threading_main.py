"""Fast health detection using threading for lighter resource usage.

This implementation uses threading for faster health detection while maintaining
compatibility with systems that prefer threading over multiprocessing.
"""

import argparse
import logging
import queue
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_warrior.automation import GameAutomation
from auto_warrior.constants import (
    VERSION, AUTHOR, LICENSE,
    DEFAULT_HEALTH_THRESHOLD,
    CRITICAL_HEALTH_THRESHOLD
)
from auto_warrior.exceptions import AutoSnakeError


class FastThreadedHealthMonitor:
    """Fast health monitoring using threading for lighter resource usage."""
    
    def __init__(self, debug_mode: bool = False, images_path = None):
        self.debug_mode = debug_mode
        self.images_path = images_path
        
        # Shared state with thread locks
        self._health_lock = threading.RLock()
        self._health_data = {
            'percentage': 1.0,
            'is_critical': False,
            'is_emergency': False,
            'last_update': time.time(),
            'fps': 0.0
        }
        
        # Emergency coordination
        self.emergency_event = threading.Event()
        self.stop_event = threading.Event()
        
        # Action queues
        self.emergency_queue = queue.Queue(maxsize=10)
        self.action_queue = queue.Queue(maxsize=30)
        
        # Thread handles
        self.health_thread = None
        self.emergency_thread = None
        
        # Performance tracking
        self.performance_stats = {
            'total_checks': 0,
            'emergency_count': 0,
            'avg_response_time': 0.0
        }
    
    def start_monitoring(self) -> None:
        """Start fast threaded health monitoring."""
        print("🚀 Starting Fast Threaded Health Monitoring")
        print(f"   Target Health Monitor FPS: 15-20")
        print(f"   Emergency Response Target: <100ms")
        print("=" * 50)
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(
            target=self._health_monitor_worker,
            name="HealthMonitor",
            daemon=True
        )
        self.health_thread.start()
        
        # Start emergency handler thread
        self.emergency_thread = threading.Thread(
            target=self._emergency_handler_worker,
            name="EmergencyHandler", 
            daemon=True
        )
        self.emergency_thread.start()
        
        time.sleep(0.5)  # Allow threads to initialize
        print("✅ Health monitoring threads started")
    
    def _health_monitor_worker(self) -> None:
        """Worker thread for health monitoring at ~15-20 FPS."""
        from auto_warrior.health import HealthDetector
        from auto_warrior.screenshot import ScreenshotManager
        from auto_warrior.templates import TemplateManager
        
        # Initialize components
        screenshot_manager = ScreenshotManager(self.debug_mode, use_live_capture=True)
        template_manager = TemplateManager(self.images_path, self.debug_mode)
        template_manager.load_all_templates()
        health_detector = HealthDetector(template_manager, self.debug_mode)
        
        print(f"🩺 Health Monitor Thread Started (ID: {threading.get_ident()})")
        
        monitor_count = 0
        fps_measurements = []
        target_interval = 1/15.0  # 15 FPS target for threading
        
        while not self.stop_event.is_set():
            try:
                cycle_start = time.time()
                
                # Fast screenshot and health detection
                if screenshot_manager.live_capture:
                    screenshot_cv = screenshot_manager.live_capture.capture_live()
                else:
                    screenshot = screenshot_manager.take_screenshot()
                    screenshot_cv = screenshot_manager.screenshot_to_cv2(screenshot)
                
                health_percentage = health_detector.get_health_percentage(screenshot_cv)
                
                # Analyze health status
                is_emergency = health_percentage <= 0.15
                is_critical = health_percentage <= CRITICAL_HEALTH_THRESHOLD
                
                # Update shared state with lock
                with self._health_lock:
                    self._health_data.update({
                        'percentage': health_percentage,
                        'is_emergency': is_emergency,
                        'is_critical': is_critical,
                        'last_update': time.time()
                    })
                
                # Handle emergency situations
                if is_emergency:
                    self.emergency_event.set()
                    self._queue_emergency_health_action(health_percentage)
                elif is_critical:
                    self._queue_critical_health_action(health_percentage)
                else:
                    self.emergency_event.clear()
                
                monitor_count += 1
                self.performance_stats['total_checks'] = monitor_count
                
                # Calculate FPS
                if monitor_count % 15 == 0:  # Every 15 cycles (1 second at 15 FPS)
                    current_time = time.time()
                    fps_measurements.append(current_time)
                    
                    if len(fps_measurements) > 5:
                        fps_measurements.pop(0)
                        
                    if len(fps_measurements) >= 2:
                        time_span = fps_measurements[-1] - fps_measurements[0]
                        fps = (len(fps_measurements) - 1) / time_span if time_span > 0 else 0
                        
                        with self._health_lock:
                            self._health_data['fps'] = fps
                    
                    if self.debug_mode:
                        print(f"🩺 Health Monitor: {fps:.1f} FPS | Health: {health_percentage:.1%}")
                
                # Maintain timing
                elapsed = time.time() - cycle_start
                sleep_time = max(0.001, target_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                if self.debug_mode:
                    print(f"❌ Health monitor error: {e}")
                time.sleep(0.05)
    
    def _emergency_handler_worker(self) -> None:
        """Worker thread for handling emergency health actions."""
        from auto_warrior.potion import PotionManager
        from auto_warrior.input_control import InputController
        from auto_warrior.templates import TemplateManager
        
        # Initialize components
        input_controller = InputController(self.debug_mode)
        template_manager = TemplateManager(self.images_path, self.debug_mode)
        template_manager.load_all_templates()
        potion_manager = PotionManager(input_controller, self.debug_mode)
        
        print(f"🚨 Emergency Handler Thread Started (ID: {threading.get_ident()})")
        
        emergency_count = 0
        response_times = []
        
        while not self.stop_event.is_set():
            try:
                # Wait for emergency actions
                action = self.emergency_queue.get(timeout=0.1)
                
                response_start = time.time()
                
                if action['type'] == 'emergency_heal':
                    emergency_count += 1
                    print(f"🚨 EMERGENCY HEAL #{emergency_count}! Health: {action['health']:.1%}")
                    
                    # Use emergency healing
                    potion_manager.use_health_potion(action['health'], force_heal=True)
                
                elif action['type'] == 'critical_heal':
                    print(f"⚠️ Critical heal - Health: {action['health']:.1%}")
                    potion_manager.use_health_potion(action['health'])
                
                # Track response time
                response_time = (time.time() - response_start) * 1000
                response_times.append(response_time)
                
                if len(response_times) > 20:
                    response_times.pop(0)
                
                avg_response = sum(response_times) / len(response_times)
                self.performance_stats['emergency_count'] = emergency_count
                self.performance_stats['avg_response_time'] = avg_response
                
                if self.debug_mode:
                    print(f"💊 Response time: {response_time:.1f}ms (avg: {avg_response:.1f}ms)")
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.debug_mode:
                    print(f"❌ Emergency handler error: {e}")
                time.sleep(0.01)
    
    def _queue_emergency_health_action(self, health_percentage: float) -> None:
        """Queue emergency health action."""
        action = {
            'type': 'emergency_heal',
            'health': health_percentage,
            'timestamp': time.time()
        }
        
        try:
            self.emergency_queue.put_nowait(action)
        except queue.Full:
            # Remove oldest emergency action to make room
            try:
                self.emergency_queue.get_nowait()
                self.emergency_queue.put_nowait(action)
            except queue.Empty:
                pass
    
    def _queue_critical_health_action(self, health_percentage: float) -> None:
        """Queue critical health action."""
        action = {
            'type': 'critical_heal',
            'health': health_percentage,
            'timestamp': time.time()
        }
        
        try:
            self.emergency_queue.put_nowait(action)
        except queue.Full:
            pass  # Skip if queue full for non-emergency
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        with self._health_lock:
            return {
                **self._health_data.copy(),
                'performance': self.performance_stats.copy()
            }
    
    def is_emergency(self) -> bool:
        """Check if there's a health emergency."""
        return self.emergency_event.is_set()
    
    def stop_monitoring(self) -> None:
        """Stop all monitoring threads."""
        print("🛑 Stopping threaded health monitoring...")
        
        self.stop_event.set()
        
        # Wait for threads to finish
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=2)
        
        if self.emergency_thread and self.emergency_thread.is_alive():
            self.emergency_thread.join(timeout=2)
        
        print("✅ All monitoring threads stopped")


class ThreadedGameAutomation(GameAutomation):
    """Game automation with fast threaded health monitoring."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fast_health_monitor = FastThreadedHealthMonitor(
            debug_mode=self.debug_mode,
            images_path=self.template_manager.images_path
        )
        
        self.last_status_print = time.time()
    
    def run_automation(self) -> None:
        """Run automation with fast threaded health monitoring."""
        try:
            print("🎮 Starting Threaded Game Automation...")
            
            # Start fast health monitoring
            self.fast_health_monitor.start_monitoring()
            
            print("⏱️ Initialization complete - entering main automation loop")
            print("💡 Health monitoring running at 15+ FPS in dedicated threads")
            print("🚨 Emergency response time: <100ms")
            print("=" * 50)
            
            # Main automation loop
            while True:
                # Get health status
                health_status = self.fast_health_monitor.get_health_status()
                
                # Handle non-critical tasks
                if not self.fast_health_monitor.is_emergency():
                    self._handle_non_critical_tasks(health_status)
                
                # Print status
                if time.time() - self.last_status_print >= 4.0:
                    self._print_status(health_status)
                    self.last_status_print = time.time()
                
                # Adaptive timing
                sleep_time = 0.15 if self.fast_health_monitor.is_emergency() else 0.4
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 Automation stopped by user")
        finally:
            self.fast_health_monitor.stop_monitoring()
    
    def _handle_non_critical_tasks(self, health_status: Dict[str, Any]) -> None:
        """Handle mana, skills, and other non-critical tasks."""
        try:
            # Take screenshot for other analyses
            screenshot = self.screenshot_manager.take_screenshot()
            screenshot_cv = self.screenshot_manager.screenshot_to_cv2(screenshot)
            
            # Mana management
            mana_percent = self.mana_detector.get_mana_percentage(screenshot_cv)
            if mana_percent < 0.5:
                self.potion_manager.use_mana_potion(mana_percent)
            
            # Skill usage (only when health is safe)
            if health_status.get('percentage', 0) > 0.6:
                self._handle_skill_usage()
                
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Non-critical task error: {e}")
    
    def _print_status(self, health_status: Dict[str, Any]) -> None:
        """Print current status with performance info."""
        health_pct = health_status.get('percentage', 0) * 100
        performance = health_status.get('performance', {})
        
        fps = health_status.get('fps', 0)
        emergency_count = performance.get('emergency_count', 0)
        response_time = performance.get('avg_response_time', 0)
        
        # Status emoji
        if health_status.get('is_emergency'):
            icon = "🚨"
        elif health_status.get('is_critical'):
            icon = "⚠️"
        elif health_pct < 70:
            icon = "💛"
        else:
            icon = "💚"
        
        print(f"{icon} Health: {health_pct:.1f}% | "
              f"Monitor: {fps:.1f} FPS | "
              f"Response: {response_time:.1f}ms | "
              f"Emergencies: {emergency_count}")


def main() -> None:
    """Main entry point for threaded automation."""
    parser = argparse.ArgumentParser(description="Auto Snake - Fast Threaded Health Detection")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--images-path", type=Path, help="Images directory path")
    parser.add_argument("--health-threshold", type=float, default=DEFAULT_HEALTH_THRESHOLD)
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    print(f"Auto Snake Fast Threaded Detection v{VERSION}")
    print("=" * 50)
    
    try:
        automation = ThreadedGameAutomation(
            debug_mode=args.debug,
            images_path=args.images_path,
            health_threshold=args.health_threshold
        )
        
        automation.run_automation()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()