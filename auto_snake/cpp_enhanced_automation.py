"""Enhanced automation using C++ extensions for true parallelism."""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

# Import the C++ extension
try:
    import automation_core

    CPP_AVAILABLE = True
    print("🚀 C++ extensions loaded successfully - True parallelism enabled!")
except ImportError as e:
    CPP_AVAILABLE = False
    print(f"⚠️  C++ extensions not available: {e}")
    print("   Falling back to Python threading...")

from auto_snake.constants import (
    CPP_BATCH_SIZE,
    CPP_BENCHMARK_ITERATIONS,
    CPP_EMPTY_HEALTH_THRESHOLD,
    CPP_TEMPLATE_MATCH_THRESHOLD,
)
from auto_snake.threading_automation import MultiThreadedGameAutomation

logger = logging.getLogger(__name__)


class CppEnhancedAutomation(MultiThreadedGameAutomation):
    """Automation with C++ extensions for maximum performance."""

    def __init__(self, *args, **kwargs):
        """Initialize C++ enhanced automation."""
        super().__init__(*args, **kwargs)
        self.cpp_available = CPP_AVAILABLE

        # Performance tracking
        self.cpp_stats = {
            "cpp_calls": 0,
            "cpp_time_saved": 0.0,
            "python_fallback_calls": 0,
            "cpp_errors": 0,
            "template_cache_hits": 0,
            "template_cache_misses": 0,
        }

        # Template cache for C++ operations
        self._template_cache = {}
        self._template_cache_lock = threading.RLock() if CPP_AVAILABLE else None

        if self.cpp_available:
            logger.info("C++ enhanced automation initialized")
            self._benchmark_cpp_performance()
        else:
            logger.warning("C++ extensions not available, using threading fallback")

    def _benchmark_cpp_performance(self):
        """Benchmark C++ extension performance on startup."""
        try:
            # Create a small test image and template
            test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            test_template = np.random.randint(0, 255, (20, 20, 3), dtype=np.uint8)

            start_time = time.time()
            result = automation_core.benchmark_template_matching(
                test_image, test_template, CPP_BENCHMARK_ITERATIONS
            )
            benchmark_time = time.time() - start_time

            if result:
                avg_time = result.get("avg_time_ms", 0)
                logger.info(
                    f"C++ benchmark: {CPP_BENCHMARK_ITERATIONS} iterations in "
                    f"{benchmark_time * 1000:.2f}ms, avg: {avg_time:.3f}ms per operation"
                )
            else:
                logger.warning("C++ benchmark returned no results")

        except Exception as e:
            logger.error(f"C++ benchmark failed: {e}")
            self.cpp_stats["cpp_errors"] += 1

    def _detect_health_cpp(self, screenshot_cv: np.ndarray) -> Dict[str, Any]:
        """Use C++ extension for health detection with true parallelism."""
        if not self.cpp_available:
            return self._detect_health_python_fallback(screenshot_cv)

        try:
            # Load template images as numpy arrays
            health_template = self._get_template_array("health_bar")
            empty_template = self._get_template_array("empty_health")

            if health_template is None or empty_template is None:
                self.cpp_stats["python_fallback_calls"] += 1
                return self._detect_health_python_fallback(screenshot_cv)

            start_time = time.time()

            # Call C++ function with GIL released
            result = automation_core.detect_health_parallel(
                screenshot_cv, health_template, empty_template, self.potion_manager.health_threshold
            )

            cpp_time = time.time() - start_time
            self.cpp_stats["cpp_calls"] += 1

            # Calculate potential time saved vs Python
            python_est_time = cpp_time * 3  # Estimate Python would be 3x slower
            self.cpp_stats["cpp_time_saved"] += python_est_time - cpp_time

            if self.debug_mode:
                logger.debug(
                    f"C++ health detection: {cpp_time * 1000:.2f}ms, "
                    f"health: {result.get('health_percentage', 0) * 100:.1f}%"
                )

            return result

        except Exception as e:
            logger.error(f"C++ health detection failed: {e}")
            self.cpp_stats["cpp_errors"] += 1
            self.cpp_stats["python_fallback_calls"] += 1
            return self._detect_health_python_fallback(screenshot_cv)

    def _detect_multiple_templates_cpp(
        self, screenshot_cv: np.ndarray, template_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Use C++ for multiple template matching in parallel."""
        if not self.cpp_available:
            return self._detect_templates_python_fallback(screenshot_cv, template_names)

        try:
            templates = []
            thresholds = []
            valid_names = []

            for name in template_names:
                template_array = self._get_template_array(name)
                if template_array is not None:
                    templates.append(template_array)
                    thresholds.append(self._get_template_threshold(name))
                    valid_names.append(name)

            if not templates:
                self.cpp_stats["python_fallback_calls"] += 1
                return []

            start_time = time.time()

            # Call C++ multi-template matching
            results = automation_core.multi_template_match(screenshot_cv, templates, thresholds)

            cpp_time = time.time() - start_time
            self.cpp_stats["cpp_calls"] += 1

            # Enhance results with template names
            enhanced_results = []
            for i, result in enumerate(results):
                if i < len(valid_names):
                    result["template_name"] = valid_names[i]
                enhanced_results.append(result)

            if self.debug_mode:
                found_count = sum(1 for r in enhanced_results if r.get("found", False))
                logger.debug(
                    f"C++ multi-template matching: {cpp_time * 1000:.2f}ms for "
                    f"{len(templates)} templates, {found_count} found"
                )

            return enhanced_results

        except Exception as e:
            logger.error(f"C++ template matching failed: {e}")
            self.cpp_stats["cpp_errors"] += 1
            self.cpp_stats["python_fallback_calls"] += 1
            return self._detect_templates_python_fallback(screenshot_cv, template_names)

    def _batch_process_screenshots_cpp(self, screenshots: List[np.ndarray]) -> List[Dict[str, Any]]:
        """Process multiple screenshots in parallel using C++."""
        if not self.cpp_available or len(screenshots) < 2:
            return [self._process_single_screenshot(sc) for sc in screenshots]

        try:
            health_template = self._get_template_array("health_bar")
            respawn_template = self._get_template_array("respawn_button")

            if health_template is None or respawn_template is None:
                self.cpp_stats["python_fallback_calls"] += 1
                return [self._process_single_screenshot(sc) for sc in screenshots]

            start_time = time.time()

            # Process screenshots in batches to manage memory
            all_results = []
            batch_size = CPP_BATCH_SIZE

            for i in range(0, len(screenshots), batch_size):
                batch = screenshots[i : i + batch_size]

                # Call C++ batch processing
                batch_results = automation_core.batch_process_screenshots(
                    batch, health_template, respawn_template, self.potion_manager.health_threshold
                )

                all_results.extend(batch_results)

            cpp_time = time.time() - start_time
            self.cpp_stats["cpp_calls"] += 1

            logger.info(
                f"C++ batch processing: {cpp_time * 1000:.2f}ms for "
                f"{len(screenshots)} screenshots ({len(screenshots) / cpp_time:.1f} fps)"
            )

            return all_results

        except Exception as e:
            logger.error(f"C++ batch processing failed: {e}")
            self.cpp_stats["cpp_errors"] += 1
            self.cpp_stats["python_fallback_calls"] += 1
            return [self._process_single_screenshot(sc) for sc in screenshots]

    def _get_template_array(self, template_name: str) -> Optional[np.ndarray]:
        """Get template as numpy array for C++ processing with caching."""
        if not self.cpp_available:
            return None

        # Check cache first
        with self._template_cache_lock:
            if template_name in self._template_cache:
                self.cpp_stats["template_cache_hits"] += 1
                return self._template_cache[template_name]

        self.cpp_stats["template_cache_misses"] += 1

        try:
            template_path = self.template_manager.get_template_path(template_name)
            if template_path and template_path.exists():
                template = cv2.imread(str(template_path))
                if template is not None:
                    # Cache the template
                    with self._template_cache_lock:
                        self._template_cache[template_name] = template
                    return template
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")

        return None

    def _get_template_threshold(self, template_name: str) -> float:
        """Get appropriate threshold for template matching."""
        threshold_map = {
            "health_bar": CPP_TEMPLATE_MATCH_THRESHOLD,
            "empty_health": CPP_EMPTY_HEALTH_THRESHOLD,
            "respawn_button": 0.8,
            "mana_bar": 0.7,
        }
        return threshold_map.get(template_name, CPP_TEMPLATE_MATCH_THRESHOLD)

    def _detect_health_python_fallback(self, screenshot_cv: np.ndarray) -> Dict[str, Any]:
        """Python fallback for health detection."""
        start_time = time.time()

        health_percentage = self.health_detector.get_health_percentage(screenshot_cv)
        is_empty = self.health_detector.is_health_empty(screenshot_cv)

        processing_time = (time.time() - start_time) * 1000

        return {
            "health_percentage": health_percentage,
            "is_empty": is_empty,
            "is_critical": health_percentage < self.potion_manager.health_threshold,
            "processing_time_ms": processing_time,
            "health_bar_found": health_percentage > 0,
            "health_location": (0, 0),
        }

    def _detect_templates_python_fallback(
        self, screenshot_cv: np.ndarray, template_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Python fallback for template matching."""
        results = []
        for i, name in enumerate(template_names):
            try:
                # Use existing template matching logic
                found_location = self.template_manager.find_template(screenshot_cv, name)
                confidence = 0.8 if found_location else 0.0

                results.append(
                    {
                        "found": found_location is not None,
                        "confidence": confidence,
                        "template_id": i,
                        "template_name": name,
                        "location": found_location if found_location else (0, 0),
                        "max_val": confidence,
                        "processing_time_ms": 0.0,
                    }
                )
            except Exception as e:
                logger.error(f"Error matching template {name}: {e}")
                results.append(
                    {
                        "found": False,
                        "confidence": 0.0,
                        "template_id": i,
                        "template_name": name,
                        "location": (0, 0),
                        "max_val": 0.0,
                        "processing_time_ms": 0.0,
                    }
                )

        return results

    def _process_single_screenshot(self, screenshot_cv: np.ndarray) -> Dict[str, Any]:
        """Process a single screenshot (fallback method)."""
        health_result = self._detect_health_python_fallback(screenshot_cv)

        # Add respawn detection
        try:
            respawn_found = self.respawn_detector.detect_respawn_button(screenshot_cv)
        except Exception as e:
            logger.error(f"Error in respawn detection: {e}")
            respawn_found = False

        return {
            "health_found": not health_result["is_empty"],
            "health_confidence": health_result["health_percentage"],
            "respawn_found": respawn_found,
            "respawn_confidence": 0.8 if respawn_found else 0.0,
        }

    def clear_template_cache(self):
        """Clear the template cache."""
        if self.cpp_available and self._template_cache_lock:
            with self._template_cache_lock:
                self._template_cache.clear()
                logger.info("Template cache cleared")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics including C++ metrics."""
        base_stats = super().get_performance_stats()

        cpp_percentage = 0
        total_calls = self.cpp_stats["cpp_calls"] + self.cpp_stats["python_fallback_calls"]
        if total_calls > 0:
            cpp_percentage = (self.cpp_stats["cpp_calls"] / total_calls) * 100

        cache_hit_rate = 0
        total_cache_requests = (
            self.cpp_stats["template_cache_hits"] + self.cpp_stats["template_cache_misses"]
        )
        if total_cache_requests > 0:
            cache_hit_rate = (self.cpp_stats["template_cache_hits"] / total_cache_requests) * 100

        cpp_stats = {
            "cpp_available": self.cpp_available,
            "cpp_calls": self.cpp_stats["cpp_calls"],
            "python_fallback_calls": self.cpp_stats["python_fallback_calls"],
            "cpp_usage_percentage": cpp_percentage,
            "cpp_errors": self.cpp_stats["cpp_errors"],
            "cpp_time_saved_seconds": self.cpp_stats["cpp_time_saved"],
            "template_cache_hits": self.cpp_stats["template_cache_hits"],
            "template_cache_misses": self.cpp_stats["template_cache_misses"],
            "template_cache_hit_rate": cache_hit_rate,
            "templates_cached": len(self._template_cache) if self.cpp_available else 0,
        }

        return {**base_stats, **cpp_stats}

    def print_performance_report(self):
        """Print detailed performance report."""
        stats = self.get_performance_stats()

        print("\n🏎️  C++ Enhanced Performance Report:")
        print(f"   {'=' * 50}")
        print(f"   C++ Extensions Available: {'✅' if stats['cpp_available'] else '❌'}")

        if stats["cpp_available"]:
            print(f"   C++ Calls: {stats['cpp_calls']}")
            print(f"   Python Fallback Calls: {stats['python_fallback_calls']}")
            print(f"   C++ Usage: {stats['cpp_usage_percentage']:.1f}%")
            print(f"   C++ Errors: {stats['cpp_errors']}")
            print(f"   Time Saved by C++: {stats['cpp_time_saved_seconds']:.3f}s")
            print(f"   Template Cache Hit Rate: {stats['template_cache_hit_rate']:.1f}%")
            print(f"   Templates Cached: {stats['templates_cached']}")

        print(f"   {'=' * 50}")

        # Print base threading stats
        if hasattr(super(), "_print_performance_stats"):
            super()._print_performance_stats()

    def run_cpp_diagnostics(self) -> Dict[str, Any]:
        """Run C++ extension diagnostics."""
        diagnostics = {
            "cpp_available": self.cpp_available,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
        }

        if not self.cpp_available:
            diagnostics["errors"].append("C++ extensions not available")
            return diagnostics

        # Test 1: Basic template matching
        try:
            test_image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
            test_template = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

            result = automation_core.multi_template_match(
                test_image, [test_template], [0.5], cv2.TM_CCOEFF_NORMED
            )

            if result and len(result) == 1:
                diagnostics["tests_passed"] += 1
                logger.info("✅ C++ template matching test passed")
            else:
                diagnostics["tests_failed"] += 1
                diagnostics["errors"].append("Template matching returned unexpected result")

        except Exception as e:
            diagnostics["tests_failed"] += 1
            diagnostics["errors"].append(f"Template matching test failed: {e}")

        # Test 2: Health detection
        try:
            test_screenshot = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
            test_health_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
            test_empty_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)

            result = automation_core.detect_health_parallel(
                test_screenshot, test_health_template, test_empty_template, 0.3
            )

            if (
                result
                and "health_percentage" in result
                and "is_empty" in result
                and "processing_time_ms" in result
            ):
                diagnostics["tests_passed"] += 1
                logger.info("✅ C++ health detection test passed")
            else:
                diagnostics["tests_failed"] += 1
                diagnostics["errors"].append("Health detection returned incomplete result")

        except Exception as e:
            diagnostics["tests_failed"] += 1
            diagnostics["errors"].append(f"Health detection test failed: {e}")

        # Test 3: Batch processing
        try:
            test_screenshots = [
                np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8) for _ in range(3)
            ]
            test_health_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
            test_respawn_template = np.random.randint(0, 255, (50, 150, 3), dtype=np.uint8)

            results = automation_core.batch_process_screenshots(
                test_screenshots, test_health_template, test_respawn_template, 0.3
            )

            if results and len(results) == 3:
                diagnostics["tests_passed"] += 1
                logger.info("✅ C++ batch processing test passed")
            else:
                diagnostics["tests_failed"] += 1
                diagnostics["errors"].append("Batch processing returned wrong number of results")

        except Exception as e:
            diagnostics["tests_failed"] += 1
            diagnostics["errors"].append(f"Batch processing test failed: {e}")

        logger.info(
            f"C++ diagnostics completed: {diagnostics['tests_passed']} passed, "
            f"{diagnostics['tests_failed']} failed"
        )

        return diagnostics

    def benchmark_performance_comparison(self, iterations: int = 10) -> Dict[str, Any]:
        """Compare C++ vs Python performance."""
        if not self.cpp_available:
            return {"error": "C++ extensions not available"}

        # Create test data
        test_image = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        test_health_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
        test_empty_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)

        # Benchmark C++
        cpp_times = []
        for _ in range(iterations):
            start_time = time.time()
            try:
                automation_core.detect_health_parallel(
                    test_image, test_health_template, test_empty_template, 0.3
                )
                cpp_times.append(time.time() - start_time)
            except Exception as e:
                logger.error(f"C++ benchmark iteration failed: {e}")

        # Benchmark Python fallback
        python_times = []
        for _ in range(iterations):
            start_time = time.time()
            self._detect_health_python_fallback(test_image)
            python_times.append(time.time() - start_time)

        if not cpp_times or not python_times:
            return {"error": "Benchmark failed"}

        cpp_avg = sum(cpp_times) / len(cpp_times)
        python_avg = sum(python_times) / len(python_times)
        speedup = python_avg / cpp_avg if cpp_avg > 0 else 0

        return {
            "iterations": iterations,
            "cpp_avg_time_ms": cpp_avg * 1000,
            "python_avg_time_ms": python_avg * 1000,
            "speedup_factor": speedup,
            "cpp_faster": speedup > 1,
            "performance_improvement": f"{(speedup - 1) * 100:.1f}%" if speedup > 1 else "0%",
        }
