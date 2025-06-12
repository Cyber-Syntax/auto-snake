#!/usr/bin/env python3
"""Test script to verify C++ extensions and functionality."""

import sys
import time
import traceback

import numpy as np


def test_basic_imports():
    """Test basic module imports."""
    print("🔍 Testing basic imports...")

    try:
        import cv2

        print(f"   ✅ OpenCV {cv2.__version__}")
    except ImportError as e:
        print(f"   ❌ OpenCV import failed: {e}")
        return False

    try:
        import numpy as np

        print(f"   ✅ NumPy {np.__version__}")
    except ImportError as e:
        print(f"   ❌ NumPy import failed: {e}")
        return False

    return True


def test_cpp_extension():
    """Test C++ extension availability and basic functionality."""
    print("\n🚀 Testing C++ extensions...")

    try:
        import automation_core

        print("   ✅ C++ extension imported successfully")
    except ImportError as e:
        print(f"   ❌ C++ extension import failed: {e}")
        print("   💡 Run './build_cpp.sh' to build C++ extensions")
        return False

    # Test basic functionality
    try:
        # Create test data
        test_image = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        test_template = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

        print("   🧪 Testing template matching...")
        start_time = time.time()
        result = automation_core.multi_template_match(test_image, [test_template], [0.5])
        cpp_time = time.time() - start_time

        if result and len(result) == 1:
            print(f"   ✅ Template matching: {cpp_time * 1000:.2f}ms")
        else:
            print("   ❌ Template matching returned unexpected result")
            return False

        print("   🧪 Testing health detection...")
        start_time = time.time()
        health_result = automation_core.detect_health_parallel(
            test_image, test_template, test_template, 0.3
        )
        cpp_time = time.time() - start_time

        if health_result and "health_percentage" in health_result:
            print(f"   ✅ Health detection: {cpp_time * 1000:.2f}ms")
            print(f"       Health: {health_result['health_percentage'] * 100:.1f}%")
        else:
            print("   ❌ Health detection failed")
            return False

        print("   🧪 Testing batch processing...")
        test_screenshots = [
            np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8) for _ in range(3)
        ]

        start_time = time.time()
        batch_results = automation_core.batch_process_screenshots(
            test_screenshots, test_template, test_template, 0.3
        )
        cpp_time = time.time() - start_time

        if batch_results and len(batch_results) == 3:
            print(f"   ✅ Batch processing: {cpp_time * 1000:.2f}ms for 3 screenshots")
        else:
            print("   ❌ Batch processing failed")
            return False

        return True

    except Exception as e:
        print(f"   ❌ C++ extension test failed: {e}")
        traceback.print_exc()
        return False


def test_threading_automation():
    """Test multi-threaded automation without C++."""
    print("\n🧵 Testing threading automation...")

    try:
        from auto_snake.threading_automation import MultiThreadedGameAutomation

        # Quick initialization test
        automation = MultiThreadedGameAutomation(
            debug_mode=False, health_threshold=0.3, max_detection_threads=2
        )

        print("   ✅ Threading automation initialized")

        # Test queue operations
        automation.add_custom_action(
            action_type="health_potion", priority=5, params={"health_percentage": 0.5}
        )

        queue_status = automation.get_queue_status()
        if queue_status["action_queue_size"] > 0:
            print("   ✅ Action queue working")

        stats = automation.get_performance_stats()
        if "runtime_seconds" in stats:
            print("   ✅ Performance stats working")

        return True

    except Exception as e:
        print(f"   ❌ Threading automation test failed: {e}")
        traceback.print_exc()
        return False


def test_cpp_enhanced_automation():
    """Test C++ enhanced automation."""
    print("\n🚀 Testing C++ enhanced automation...")

    try:
        from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation

        automation = CppEnhancedAutomation(
            debug_mode=False, health_threshold=0.3, max_detection_threads=2
        )

        print(f"   C++ Available: {automation.cpp_available}")

        if automation.cpp_available:
            print("   ✅ C++ enhanced automation initialized")

            # Test diagnostics
            diagnostics = automation.run_cpp_diagnostics()
            print(
                f"   🧪 Diagnostics: {diagnostics['tests_passed']} passed, {diagnostics['tests_failed']} failed"
            )

            # Test performance benchmark
            benchmark = automation.benchmark_performance_comparison(iterations=3)
            if "speedup_factor" in benchmark:
                print(f"   ⚡ Performance: {benchmark['speedup_factor']:.1f}x speedup")

            # Test template caching
            automation.clear_template_cache()
            print("   ✅ Template cache operations working")

        else:
            print("   ⚠️  C++ extensions not available, using fallback")

        return True

    except Exception as e:
        print(f"   ❌ C++ enhanced automation test failed: {e}")
        traceback.print_exc()
        return False


def test_constants_and_config():
    """Test constants and configuration."""
    print("\n⚙️  Testing configuration...")

    try:
        from auto_snake.constants import (
            CPP_TEMPLATE_MATCH_THRESHOLD,
            DEFAULT_HEALTH_THRESHOLD,
            DETECTION_THREAD_COUNT,
            SCREENSHOT_QUEUE_SIZE,
        )

        print(f"   Screenshot queue size: {SCREENSHOT_QUEUE_SIZE}")
        print(f"   Detection threads: {DETECTION_THREAD_COUNT}")
        print(f"   Template threshold: {CPP_TEMPLATE_MATCH_THRESHOLD}")
        print(f"   Health threshold: {DEFAULT_HEALTH_THRESHOLD}")
        print("   ✅ Configuration loaded successfully")

        return True

    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False


def run_performance_comparison():
    """Run performance comparison between Python and C++."""
    print("\n⚡ Performance Comparison...")

    try:
        # Test data
        test_image = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        test_template = np.random.randint(0, 255, (30, 100, 3), dtype=np.uint8)
        iterations = 5

        # Python timing (using OpenCV directly)
        import cv2

        python_times = []

        for _ in range(iterations):
            start_time = time.time()
            result = cv2.matchTemplate(test_image, test_template, cv2.TM_CCOEFF_NORMED)
            cv2.minMaxLoc(result)
            python_times.append(time.time() - start_time)

        python_avg = sum(python_times) / len(python_times)
        print(f"   Python average: {python_avg * 1000:.2f}ms")

        # C++ timing (if available)
        try:
            import automation_core

            cpp_times = []

            for _ in range(iterations):
                start_time = time.time()
                automation_core.multi_template_match(test_image, [test_template], [0.5])
                cpp_times.append(time.time() - start_time)

            cpp_avg = sum(cpp_times) / len(cpp_times)
            speedup = python_avg / cpp_avg if cpp_avg > 0 else 0

            print(f"   C++ average: {cpp_avg * 1000:.2f}ms")
            print(f"   Speedup: {speedup:.1f}x")

            if speedup > 1:
                print(f"   🏆 C++ is {speedup:.1f}x faster!")
            else:
                print("   ⚠️  C++ not faster (check implementation)")

        except ImportError:
            print("   ⚠️  C++ extensions not available for comparison")

        return True

    except Exception as e:
        print(f"   ❌ Performance comparison failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 C++ Extensions and Automation Test Suite")
    print("=" * 60)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("C++ Extensions", test_cpp_extension),
        ("Threading Automation", test_threading_automation),
        ("C++ Enhanced Automation", test_cpp_enhanced_automation),
        ("Configuration", test_constants_and_config),
        ("Performance Comparison", run_performance_comparison),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ {test_name} crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {passed / (passed + failed) * 100:.1f}%")

    if failed == 0:
        print("\n🎉 All tests passed! System is ready for automation.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
