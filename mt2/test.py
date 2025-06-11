import os

import cv2
import numpy as np
import pyautogui


def test_image_detection():
    """Comprehensive test for image detection debugging"""

    print("=== Image Detection Debug Test ===\n")

    # Check if images folder exists
    images_path = "images"
    if not os.path.exists(images_path):
        print(f"ERROR: Images folder '{images_path}' not found!")
        return

    print(f"✓ Images folder found: {images_path}")

    # List all image files
    image_files = [f for f in os.listdir(images_path) if f.endswith(".png")]
    print(f"✓ Found {len(image_files)} PNG files: {image_files}\n")

    # Take a screenshot first
    print("Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # Save screenshot for debugging
    cv2.imwrite("debug/debug_full_screenshot.png", screenshot_cv)
    print(f"✓ Screenshot saved as 'debug_full_screenshot.png' (Size: {screenshot.size})\n")

    # Test each health bar image
    for image_file in image_files:
        if "health_bar" in image_file:
            print(f"--- Testing {image_file} ---")
            image_path = os.path.join(images_path, image_file)

            # Check if image file exists and can be loaded
            if not os.path.exists(image_path):
                print(f"ERROR: File not found: {image_path}")
                continue

            # Load template image
            template = cv2.imread(image_path)
            if template is None:
                print(f"ERROR: Could not load {image_path}")
                continue

            print(f"✓ Template loaded: {template.shape}")

            # Test 1: PyAutoGUI locateOnScreen with different confidence levels
            print("Test 1: PyAutoGUI locateOnScreen")
            confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5]

            for confidence in confidence_levels:
                try:
                    location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                    if location:
                        print(f"  ✓ Found at confidence {confidence}: {location}")
                        # Save a cropped version for comparison
                        x, y, w, h = location
                        cropped = screenshot_cv[y : y + h, x : x + w]
                        cv2.imwrite(
                            f"debug/debug_found_{image_file.replace('.png', '')}_conf{confidence}.png",
                            cropped,
                        )
                        break
                    else:
                        print(f"  ✗ Not found at confidence {confidence}")
                except pyautogui.ImageNotFoundException:
                    print(f"  ✗ Not found at confidence {confidence}")
                except Exception as e:
                    print(f"  ERROR at confidence {confidence}: {e}")

            # Test 2: OpenCV Template Matching
            print("Test 2: OpenCV Template Matching")
            try:
                # Convert to grayscale for better matching
                screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

                # Perform template matching
                result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                print(f"  Match score: {max_val:.4f} at location {max_loc}")

                if max_val > 0.3:  # Lower threshold for debugging
                    print(f"  ✓ Potential match found (score: {max_val:.4f})")

                    # Draw rectangle on screenshot
                    h, w = template_gray.shape
                    top_left = max_loc
                    bottom_right = (top_left[0] + w, top_left[1] + h)

                    # Save marked screenshot
                    marked_screenshot = screenshot_cv.copy()
                    cv2.rectangle(marked_screenshot, top_left, bottom_right, (0, 255, 0), 2)
                    cv2.imwrite(
                        f"debug/debug_match_{image_file.replace('.png', '')}.png", marked_screenshot
                    )

                    # Save the matched region
                    matched_region = screenshot_cv[
                        top_left[1] : bottom_right[1], top_left[0] : bottom_right[0]
                    ]
                    cv2.imwrite(
                        f"debug/debug_region_{image_file.replace('.png', '')}.png", matched_region
                    )

                else:
                    print(f"  ✗ No good match (score too low: {max_val:.4f})")

            except Exception as e:
                print(f"  ERROR in OpenCV matching: {e}")

            print()  # Empty line for readability

    # Test 3: Check screen resolution and scaling
    print("--- System Information ---")
    screen_size = pyautogui.size()
    print(f"Screen resolution: {screen_size}")

    # Test 4: Manual region check
    print("\n--- Manual Region Test ---")
    print(
        "Move your mouse to different parts of the health bar and press SPACE to capture that region"
    )
    print("Press 'q' to quit this test")

    import time

    import keyboard

    region_count = 0
    while True:
        if keyboard.is_pressed("space"):
            region_count += 1
            x, y = pyautogui.position()
            print(f"Mouse position: ({x}, {y})")

            # Capture a small region around the mouse
            region_size = 100
            try:
                region_screenshot = pyautogui.screenshot(
                    region=(
                        max(0, x - region_size // 2),
                        max(0, y - region_size // 2),
                        region_size,
                        region_size,
                    )
                )

                region_cv = cv2.cvtColor(np.array(region_screenshot), cv2.COLOR_RGB2BGR)
                cv2.imwrite(f"debug_manual_region_{region_count}.png", region_cv)
                print(f"  Saved region as debug_manual_region_{region_count}.png")

                time.sleep(0.5)  # Prevent multiple captures

            except Exception as e:
                print(f"  Error capturing region: {e}")

        elif keyboard.is_pressed("q"):
            break

        time.sleep(0.1)

    print("\n=== Test Complete ===")
    print("Check the generated debug images:")
    print("- debug_full_screenshot.png: Full screen capture")
    print("- debug_match_*.png: Screenshots with detected regions marked")
    print("- debug_region_*.png: Cropped regions that were matched")
    print("- debug_found_*.png: Regions found by PyAutoGUI")
    print("- debug_manual_region_*.png: Manual captures around mouse position")


if __name__ == "__main__":
    test_image_detection()
