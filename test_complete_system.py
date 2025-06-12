#!/usr/bin/env python3
"""Comprehensive test and demonstration script for the auto-snake automation system.

This script tests both the multi-threaded and C++ enhanced automation systems,
demonstrates their capabilities, and provides performance comparisons.
"""

import logging
import sys
import time
import traceback

import numpy as np


def setup_logging():
    """Setup logging for comprehensive testing."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(threadName)-15s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("system_test.log")],
    )

    # Reduce noise from external libraries
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


def print_banner():
    """Print the test banner."""
    print("🧪 Auto-Snake Complete System Test & Demonstration")
    print("=" * 70)
    print("Testing both multi-threaded and C++ enhanced automation systems")
    print("=" * 70)


def test_basic_imports():
    """Test all basic module imports."""
    print("\n🔍 Testing Basic Imports...")
    print("-" * 50)

    tests = [
        ("OpenCV", "cv2"),
        ("NumPy", "numpy"),
        ("PIL", "PIL"),
        ("PyAutoGUI", "pyautogui"),
        ("PyInput", "pynput"),
    ]

    passed = 0
    for name, module in tests:
        try:
            __import__(module)
            print(f"   ✅ {name}")
            passed += 1
        except ImportError as e:
            print(f"   ❌ {name}: {e}")

    print(f"\nBasic imports: {passed}/{len(tests)} passed")
    return passed == len(tests)


def test_core_modules():
    """Test core automation modules."""
    print("\n🔧 Testing Core Modules...")
    print("-" * 50)

    tests = []

    # Test core automation components
    try:
        from auto_snake.templates import TemplateManager

        print("   ✅ Core automation modules")
        tests.append(True)
    except Exception as e:
        print(f"   ❌ Core automation modules: {e}")
        tests.append(False)

    # Test template manager functionality
    try:
        template_manager = TemplateManager(debug_mode=True)
        template_manager.load_all_templates()

        template_info = template_manager.get_template_info()
        health_count = template_info["health_templates_count"]
        empty_loaded = template_info["empty_health_loaded"]
        respawn_loaded = template_info["respawn_button_loaded"]

        print(
            f"   ✅ Template Manager: {health_count} health templates, "
            f"empty={empty_loaded}, respawn={respawn_loaded}"
        )
        tests.append(True)
    except Exception as e:
        print(f"   ❌ Template Manager: {e}")
        tests.append(False)

    # Test template path resolution
    try:
        template_manager = TemplateManager()
        health_path = template_manager.get_template_path("health_bar")
        empty_path = template_manager.get_template_path("empty_health")
        respawn_path = template_manager.get_template_path("respawn_button")

        paths_found = sum(
            [health_path is not None, empty_path is not None, respawn_path is not None]
        )

        print(f"   ✅ Template Path Resolution: {paths_found}/3 paths found")
        tests.append(True)
    except Exception as e:
        print(f"   ❌ Template Path Resolution: {e}")
        tests.append(False)

    passed = sum(tests)
    print(f"\nCore modules: {passed}/{len(tests)} passed")
    return passed == len(tests)


def test_cpp_extensions():
    """Test C++ extensions availability and functionality."""
    print("\n🚀 Testing C++ Extensions...")
    print("-" * 50)

    # Test C++ module import
    try:
        import automation_core

        print("   ✅ C++ extension import successful")
        cpp_available = True
    except ImportError as e:
        print(f"   ❌ C++ extension import failed: {e}")
        return False

    if not cpp_available:
        return False

    # Test basic C++ functionality
    tests = []

    # Test template matching
    try:
        test_image = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        test_template = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

        start_time = time.time()
        result = automation_core.multi_template_match(test_image, [test_template], [0.5])
        cpp_time = time.time() - start_time

        if result and len(result) == 1:
            print(f"   ✅ Template matching: {cpp_time * 1000:.2f}ms")
            tests.append(True)
        else:
            print("   ❌ Template matching: unexpected result")
            tests.append(False)
    except Exception as e:
        print(f"   ❌ Template matching: {e}")
        tests.append(False)

    # Test health detection
    try:
        test_screenshot = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        test_health_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
        test_empty_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)

        start_time = time.time()
        result = automation_core.detect_health_parallel(
            test_screenshot, test_health_template, test_empty_template, 0.3
        )
        cpp_time = time.time() - start_time

        if result and all(
            key in result for key in ["health_percentage", "is_empty", "processing_time_ms"]
        ):
            print(f"   ✅ Health detection: {cpp_time * 1000:.2f}ms")
            tests.append(True)
        else:
            print("   ❌ Health detection: incomplete result")
            tests.append(False)
    except Exception as e:
        print(f"   ❌ Health detection: {e}")
        tests.append(False)

    # Test batch processing
    try:
        test_screenshots = [
            np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8) for _ in range(3)
        ]
        test_health_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
        test_respawn_template = np.random.randint(0, 255, (50, 150, 3), dtype=np.uint8)

        start_time = time.time()
        results = automation_core.batch_process_screenshots(
            test_screenshots, test_health_template, test_respawn_template, 0.3
        )
        cpp_time = time.time() - start_time

        if results and len(results) == 3:
            print(f"   ✅ Batch processing: {cpp_time * 1000:.2f}ms for 3 screenshots")
            tests.append(True)
        else:
            print("   ❌ Batch processing: wrong number of results")
            tests.append(False)
    except Exception as e:
        print(f"   ❌ Batch processing: {e}")
        tests.append(False)

    # Test benchmark function
    try:
        test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        test_template = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

        result = automation_core.benchmark_template_matching(test_image, test_template, 10)

        if result and "avg_time_ms" in result:
            avg_time = result["avg_time_ms"]
            print(f"   ✅ Benchmark function: {avg_time:.3f}ms average")
            tests.append(True)
        else:
            print("   ❌ Benchmark function: invalid result")
            tests.append(False)
    except Exception as e:
        print(f"   ❌ Benchmark function: {e}")
        tests.append(False)

    passed = sum(tests)
    print(f"\nC++ extensions: {passed}/{len(tests)} passed")
    return passed == len(tests)


def test_threading_automation():
    """Test multi-threaded automation system."""
    print("\n🧵 Testing Multi-Threaded Automation...")
    print("-" * 50)

    try:
        from auto_snake.threading_automation import MultiThreadedGameAutomation

        # Initialize automation
        automation = MultiThreadedGameAutomation(
            debug_mode=False,  # Reduce logging noise
            health_threshold=0.3,
            max_detection_threads=2,
        )
        print("   ✅ Initialization successful")

        # Test queue operations
        automation.add_custom_action(
            action_type="health_potion", priority=5, params={"health_percentage": 0.5}
        )

        queue_status = automation.get_queue_status()
        if queue_status["action_queue_size"] > 0:
            print("   ✅ Queue operations working")
        else:
            print("   ❌ Queue operations failed")
            return False

        # Test performance stats
        stats = automation.get_performance_stats()
        if "runtime_seconds" in stats:
            print("   ✅ Performance statistics working")
        else:
            print("   ❌ Performance statistics failed")
            return False

        # Test template access
        template_info = automation.template_manager.get_template_info()
        health_templates = template_info["health_templates_count"]
        print(f"   ✅ Template access: {health_templates} health templates loaded")

        return True

    except Exception as e:
        print(f"   ❌ Threading automation failed: {e}")
        if "debug_mode" in str(e).lower():
            traceback.print_exc()
        return False


def test_cpp_enhanced_automation():
    """Test C++ enhanced automation system."""
    print("\n🚀 Testing C++ Enhanced Automation...")
    print("-" * 50)

    try:
        from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation

        # Initialize automation
        automation = CppEnhancedAutomation(
            debug_mode=False,  # Reduce logging noise
            health_threshold=0.3,
            max_detection_threads=2,
        )

        print(f"   ✅ Initialization successful (C++ available: {automation.cpp_available})")

        if not automation.cpp_available:
            print("   ⚠️  C++ extensions not available, testing fallback mode")

        # Test diagnostics
        diagnostics = automation.run_cpp_diagnostics()
        tests_passed = diagnostics["tests_passed"]
        tests_failed = diagnostics["tests_failed"]
        print(f"   🧪 Diagnostics: {tests_passed} passed, {tests_failed} failed")

        # Test performance benchmark if C++ is available
        if automation.cpp_available:
            benchmark = automation.benchmark_performance_comparison(iterations=5)
            if "speedup_factor" in benchmark and "error" not in benchmark:
                speedup = benchmark["speedup_factor"]
                improvement = benchmark["performance_improvement"]
                print(f"   ⚡ Performance: {speedup:.1f}x speedup ({improvement})")
            else:
                print(f"   ❌ Benchmark failed: {benchmark.get('error', 'Unknown error')}")

        # Test template caching
        automation.clear_template_cache()
        print("   ✅ Template cache operations working")

        # Test performance stats
        stats = automation.get_performance_stats()
        if "cpp_available" in stats:
            cpp_usage = stats.get("cpp_usage_percentage", 0)
            print(f"   📊 C++ usage: {cpp_usage:.1f}%")

        return True

    except Exception as e:
        print(f"   ❌ C++ enhanced automation failed: {e}")
        traceback.print_exc()
        return False


def run_performance_comparison():
    """Run performance comparison between different systems."""
    print("\n⚡ Performance Comparison...")
    print("-" * 50)

    try:
        # Test data
        test_image = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        test_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
        iterations = 10

        results = {}

        # Test pure OpenCV (baseline)
        try:
            import cv2

            times = []
            for _ in range(iterations):
                start_time = time.time()
                result = cv2.matchTemplate(test_image, test_template, cv2.TM_CCOEFF_NORMED)
                cv2.minMaxLoc(result)
                times.append(time.time() - start_time)

            avg_time = sum(times) / len(times)
            results["Pure OpenCV"] = avg_time
            print(f"   🐍 Pure OpenCV: {avg_time * 1000:.2f}ms average")
        except Exception as e:
            print(f"   ❌ Pure OpenCV test failed: {e}")

        # Test C++ extensions
        try:
            import automation_core

            times = []
            for _ in range(iterations):
                start_time = time.time()
                automation_core.multi_template_match(test_image, [test_template], [0.5])
                times.append(time.time() - start_time)

            avg_time = sum(times) / len(times)
            results["C++ Extensions"] = avg_time
            print(f"   🚀 C++ Extensions: {avg_time * 1000:.2f}ms average")
        except Exception as e:
            print(f"   ❌ C++ extensions test failed: {e}")

        # Calculate and display speedups
        if len(results) > 1:
            baseline = results.get("Pure OpenCV")
            if baseline:
                print("\n   📊 Performance Improvements:")
                for name, time_val in results.items():
                    if name != "Pure OpenCV":
                        speedup = baseline / time_val if time_val > 0 else 0
                        improvement = (speedup - 1) * 100 if speedup > 1 else 0
                        print(f"      {name}: {speedup:.1f}x faster (+{improvement:.1f}%)")

        return True

    except Exception as e:
        print(f"   ❌ Performance comparison failed: {e}")
        return False


def run_system_integration_test():
    """Run a comprehensive integration test."""
    print("\n🔗 System Integration Test...")
    print("-" * 50)

    tests_passed = 0
    total_tests = 0

    # Test 1: Full threading system initialization
    try:
        print("   Testing full threading system...")
        from auto_snake.threading_automation import MultiThreadedGameAutomation

        automation = MultiThreadedGameAutomation(debug_mode=False)

        # Add some test actions
        automation.add_custom_action("health_potion", 5, {"health_percentage": 0.5})
        automation.add_custom_action("skill_use", 8, {"skill_key": "1"})

        # Check queue status
        queue_status = automation.get_queue_status()
        assert queue_status["action_queue_size"] == 2

        print("   ✅ Threading system integration")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Threading system integration: {e}")
    total_tests += 1

    # Test 2: Full C++ enhanced system initialization
    try:
        print("   Testing full C++ enhanced system...")
        from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation

        automation = CppEnhancedAutomation(debug_mode=False)

        # Test template operations
        health_path = automation.template_manager.get_template_path("health_bar")
        assert health_path is not None

        # Test C++ integration
        if automation.cpp_available:
            # Test actual template loading
            health_template = automation._get_template_array("health_bar")
            assert health_template is not None

        print("   ✅ C++ enhanced system integration")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ C++ enhanced system integration: {e}")
    total_tests += 1

    # Test 3: Cross-compatibility
    try:
        print("   Testing cross-compatibility...")

        # Both systems should be able to load the same templates
        from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation
        from auto_snake.threading_automation import MultiThreadedGameAutomation

        threading_auto = MultiThreadedGameAutomation(debug_mode=False)
        cpp_auto = CppEnhancedAutomation(debug_mode=False)

        # Compare template info
        threading_info = threading_auto.template_manager.get_template_info()
        cpp_info = cpp_auto.template_manager.get_template_info()

        assert threading_info["health_templates_count"] == cpp_info["health_templates_count"]
        assert threading_info["empty_health_loaded"] == cpp_info["empty_health_loaded"]

        print("   ✅ Cross-compatibility verified")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Cross-compatibility: {e}")
    total_tests += 1

    print(f"\n   Integration tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests


def main():
    """Main test function."""
    setup_logging()
    print_banner()

    test_results = []

    # Run all tests
    test_results.append(("Basic Imports", test_basic_imports()))
    test_results.append(("Core Modules", test_core_modules()))
    test_results.append(("C++ Extensions", test_cpp_extensions()))
    test_results.append(("Threading Automation", test_threading_automation()))
    test_results.append(("C++ Enhanced Automation", test_cpp_enhanced_automation()))
    test_results.append(("Performance Comparison", run_performance_comparison()))
    test_results.append(("System Integration", run_system_integration_test()))

    # Print final results
    print("\n" + "=" * 70)
    print("📊 FINAL TEST RESULTS")
    print("=" * 70)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name:<25} | {status}")
        if result:
            passed += 1

    print("-" * 70)
    print(f"   TOTAL: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready for automation.")
        print("\nQuick start commands:")
        print("   python3 cpp_enhanced_usage.py     # C++ enhanced automation")
        print("   python3 multi_threaded_usage.py   # Multi-threaded automation")
        print("   python3 test_cpp_extensions.py    # Extended C++ tests")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above for details.")
        print("\nTroubleshooting:")
        print("   1. Ensure all dependencies are installed: pip install -r requirements.txt")
        print("   2. Build C++ extensions: ./build_cpp.sh")
        print("   3. Check template images exist in auto_snake/images/")
        return 1


if __name__ == "__main__":
    sys.exit(main())
