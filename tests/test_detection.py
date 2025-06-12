"""Simple detection test using OpenCV and PNG files directly.

This script provides a straightforward way to test health bar and respawn button
detection without complex modules - just pure OpenCV template matching.
"""

import cv2
import numpy as np
import pyautogui
import time
from pathlib import Path

# Configuration
IMAGES_DIR = Path(__file__).parent.parent / "auto_snake" / "images"
OUTPUT_DIR = Path("/tmp")

# Thresholds - you can adjust these easily
EMPTY_HEALTH_CONFIDENCE = 0.8
MIN_TEMPLATE_CONFIDENCE = 0.5
RESPAWN_BUTTON_CONFIDENCE = 0.8

def take_screenshot():
    """Take a screenshot and convert to OpenCV format."""
    screenshot = pyautogui.screenshot()
    # Convert PIL to OpenCV format (BGR)
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return screenshot_cv

def load_template(filename):
    """Load a template image."""
    template_path = IMAGES_DIR / filename
    if template_path.exists():
        return cv2.imread(str(template_path))
    return None

def test_template_match(screenshot, template, template_name, threshold):
    """Test template matching and return results."""
    if template is None:
        return None, 0.0, (0, 0)
    
    # Convert to grayscale for matching
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # Perform template matching
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # Check if above threshold
    detected = max_val > threshold
    
    print(f"{template_name:20} | Confidence: {max_val:.4f} | Threshold: {threshold:.3f} | {'✅ DETECTED' if detected else '❌ NOT DETECTED'}")
    
    return detected, max_val, max_loc

def create_visualization(screenshot, detections, timestamp):
    """Create visualization with detection boxes."""
    vis_image = screenshot.copy()
    
    # Colors: BGR format
    colors = {
        'health': (0, 0, 255),    # Red
        'empty': (128, 128, 128), # Gray
        'left_empty': (0, 215, 255), # Gold
        'respawn': (128, 128, 128) # Gray
    }
    
    for detection in detections:
        if detection['template'] is not None:
            x, y = detection['location']
            h, w = detection['template'].shape[:2]
            
            # Draw rectangle for all detections (detected or not)
            color = colors.get(detection['type'], (255, 255, 255))
            if detection['detected']:
                # Thick line for detected
                cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 3)
                label = f"{detection['name']} ({detection['confidence']:.3f}) DETECTED"
            else:
                # Thin line for not detected
                cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 1)
                label = f"{detection['name']} ({detection['confidence']:.3f})"
            
            # Add label
            cv2.putText(vis_image, label, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Add status overlay
    status_lines = [
        f"Timestamp: {timestamp}",
        f"Empty Health Threshold: {EMPTY_HEALTH_CONFIDENCE}",
        f"Health Template Threshold: {MIN_TEMPLATE_CONFIDENCE}",
        f"Respawn Button Threshold: {RESPAWN_BUTTON_CONFIDENCE}"
    ]
    
    for i, line in enumerate(status_lines):
        y_pos = 25 + i * 20
        # White text with black outline
        cv2.putText(vis_image, line, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(vis_image, line, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    return vis_image

def main():
    """Run the simple detection test."""
    print("🚀 Simple Detection Test")
    print("=" * 60)
    print(f"📁 Images directory: {IMAGES_DIR}")
    print(f"💾 Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    # Check if images exist
    template_files = [
        "20_health_bar.png",
        "40_health_bar.png", 
        "50_health_bar.png",
        "70_health_bar.png",
        "90_health_bar.png",
        "full_health_bar.png",
        "empty_health_bar.png",
        "left_empty_health_bar.png",
        "respawn_button.png"
    ]
    
    print("📋 Template Files Check:")
    missing_files = []
    for filename in template_files:
        filepath = IMAGES_DIR / filename
        if filepath.exists():
            print(f"   ✅ {filename}")
        else:
            print(f"   ❌ {filename} - MISSING!")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n⚠️  Warning: {len(missing_files)} template files are missing!")
    
    print("\n" + "=" * 60)
    
    while True:
        print("\nChoose test mode:")
        print("1. Single test (current screen)")
        print("2. Continuous test (every 3 seconds)")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            run_single_test()
        elif choice == "2":
            run_continuous_test()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

def run_single_test():
    """Run a single detection test."""
    timestamp = int(time.time())
    print(f"\n📸 Taking screenshot at {timestamp}...")
    
    # Take screenshot
    screenshot = take_screenshot()
    print(f"Screenshot size: {screenshot.shape[1]}x{screenshot.shape[0]}")
    
    print("\n🔍 Testing Health Templates:")
    print("-" * 60)
    print(f"{'Template':<20} | {'Confidence':<12} | {'Threshold':<10} | {'Status'}")
    print("-" * 60)
    
    detections = []
    
    # Test health templates
    health_templates = {
        "20% Health": "20_health_bar.png",
        "40% Health": "40_health_bar.png",
        "50% Health": "50_health_bar.png", 
        "70% Health": "70_health_bar.png",
        "90% Health": "90_health_bar.png",
        "Full Health": "full_health_bar.png"
    }
    
    best_health_match = None
    best_health_confidence = 0.0
    
    for name, filename in health_templates.items():
        template = load_template(filename)
        detected, confidence, location = test_template_match(
            screenshot, template, name, MIN_TEMPLATE_CONFIDENCE
        )
        
        detections.append({
            'name': name,
            'detected': detected,
            'confidence': confidence,
            'location': location,
            'template': template,
            'type': 'health'
        })
        
        if confidence > best_health_confidence:
            best_health_confidence = confidence
            best_health_match = name
    
    print("-" * 60)
    
    # Test empty health
    print("\n💀 Testing Empty Health:")
    print("-" * 60)
    empty_template = load_template("empty_health_bar.png")
    empty_detected, empty_confidence, empty_location = test_template_match(
        screenshot, empty_template, "Empty Health", EMPTY_HEALTH_CONFIDENCE
    )
    
    detections.append({
        'name': 'Empty Health',
        'detected': empty_detected,
        'confidence': empty_confidence,
        'location': empty_location,
        'template': empty_template,
        'type': 'empty'
    })
    
    left_empty_template = load_template("left_empty_health_bar.png")
    left_empty_detected, left_empty_confidence, left_empty_location = test_template_match(
        screenshot, left_empty_template, "Left Empty Health", EMPTY_HEALTH_CONFIDENCE
    )
    
    detections.append({
        'name': 'Left Empty Health',
        'detected': left_empty_detected,
        'confidence': left_empty_confidence,
        'location': left_empty_location,
        'template': left_empty_template,
        'type': 'left_empty'
    })
    
    # Test respawn button
    print("\n🔄 Testing Respawn Button:")
    print("-" * 60)
    respawn_template = load_template("respawn_button.png")
    respawn_detected, respawn_confidence, respawn_location = test_template_match(
        screenshot, respawn_template, "Respawn Button", RESPAWN_BUTTON_CONFIDENCE
    )
    
    detections.append({
        'name': 'Respawn Button',
        'detected': respawn_detected,
        'confidence': respawn_confidence,
        'location': respawn_location,
        'template': respawn_template,
        'type': 'respawn'
    })
    
    # Create visualization
    vis_image = create_visualization(screenshot, detections, timestamp)
    
    # Generate filename
    if empty_detected or left_empty_detected:
        health_status = "EMPTY"
    elif best_health_match:
        health_status = f"HEALTH_{best_health_match.replace('% Health', '').replace(' ', '_')}"
    else:
        health_status = "NO_HEALTH"
    respawn_status = "RESPAWN" if respawn_detected else "NO_RESPAWN"
    
    filename = f"temp_detected_{health_status}_{respawn_status}_{timestamp}.png"
    output_path = OUTPUT_DIR / filename
    
    # Save visualization
    try:
        cv2.imwrite(str(output_path), vis_image)
        print(f"\n💾 Screenshot saved: {output_path}")
    except Exception as e:
        print(f"\n❌ Failed to save screenshot: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 DETECTION SUMMARY")
    print("=" * 60)
    print(f"🏆 Best Health Match: {best_health_match} ({best_health_confidence:.4f})" if best_health_match else "🏆 Best Health Match: None")
    print(f"💀 Empty Health: {'YES' if empty_detected else 'NO'} ({empty_confidence:.4f})")
    print(f"💀 Left Empty Health: {'YES' if left_empty_detected else 'NO'} ({left_empty_confidence:.4f})")
    print(f"🔄 Respawn Button: {'YES' if respawn_detected else 'NO'} ({respawn_confidence:.4f})")
    
    print("\n💡 THRESHOLD RECOMMENDATIONS:")
    if empty_confidence > 0.0:
        if empty_detected:
            print(f"   Empty health detected with {empty_confidence:.4f} confidence")
            if empty_confidence < EMPTY_HEALTH_CONFIDENCE + 0.05:
                print(f"   💡 Consider lowering EMPTY_HEALTH_CONFIDENCE to {empty_confidence - 0.02:.3f}")
        else:
            if empty_confidence > EMPTY_HEALTH_CONFIDENCE - 0.1:
                print(f"   Empty health close to threshold ({empty_confidence:.4f} vs {EMPTY_HEALTH_CONFIDENCE:.3f})")
                print(f"   💡 Consider raising EMPTY_HEALTH_CONFIDENCE to {empty_confidence + 0.05:.3f}")
    
    if respawn_confidence > 0.0:
        if respawn_detected:
            print(f"   Respawn button detected with {respawn_confidence:.4f} confidence")
        else:
            if respawn_confidence > RESPAWN_BUTTON_CONFIDENCE - 0.1:
                print(f"   Respawn button close to threshold ({respawn_confidence:.4f} vs {RESPAWN_BUTTON_CONFIDENCE:.3f})")
                print(f"   💡 Consider lowering RESPAWN_BUTTON_CONFIDENCE to {respawn_confidence - 0.02:.3f}")
    
    print("=" * 60)

def run_continuous_test():
    """Run continuous testing every 3 seconds."""
    print("🔄 Starting continuous testing (every 3 seconds). Press Ctrl+C to stop.")
    
    try:
        while True:
            run_single_test()
            print("\n⏳ Waiting 3 seconds for next test...\n")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n🛑 Continuous testing stopped by user.")

if __name__ == "__main__":
    main()