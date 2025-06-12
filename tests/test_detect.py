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
IMAGES_DIR = Path(__file__).parent.parent / "auto_warrior" / "images"
OUTPUT_DIR = Path("/tmp")

# Thresholds - you can adjust these easily
EMPTY_HEALTH_CONFIDENCE = 0.8
MIN_TEMPLATE_CONFIDENCE = 0.75
RESPAWN_BUTTON_CONFIDENCE = 0.8
MOB_HEALTH_CONFIDENCE = 0.75  # New threshold for mob health detection

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
        'respawn': (128, 128, 128), # Gray
        'mob_health': (255, 0, 0),  # Blue for mob health
        'object': (0, 255, 0),      # Green for objects
        'button': (128, 0, 128)     # Purple for buttons
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
        f"Respawn Button Threshold: {RESPAWN_BUTTON_CONFIDENCE}",
        f"Mob Health Threshold: {MOB_HEALTH_CONFIDENCE}"
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
        "respawn_button.png",
        "mob_full_health_bar.png",        # Added mob health bar
        "object_yang.png",            # Added objects
        "object_health_pot.png",
        "object_health_pot_v2.png",
        "auto_hunt_start_button.png"  # Added button
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
    
    # Test mob health bar
    print("\n👹 Testing Mob Health Bar:")
    print("-" * 60)
    mob_health_template = load_template("mob_health_bar.png")
    mob_detected, mob_confidence, mob_location = test_template_match(
        screenshot, mob_health_template, "Mob Health", MOB_HEALTH_CONFIDENCE
    )
    
    detections.append({
        'name': 'Mob Health',
        'detected': mob_detected,
        'confidence': mob_confidence,
        'location': mob_location,
        'template': mob_health_template,
        'type': 'mob_health'
    })
    
    # Test objects
    print("\n📦 Testing Objects:")
    print("-" * 60)
    object_templates = {
        "Object Yang": "object_yang.png",
        "Object Health Potion": "object_health_pot.png",
        "Object Health Potionv2": "object_health_pot_v2.png"
    }
    
    for name, filename in object_templates.items():
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
            'type': 'object'
        })
    
    # Test buttons
    print("\n🔄 Testing Buttons:")
    print("-" * 60)
    button_templates = {
        "Auto Hunt Start Button": "auto_hunt_start_button.png",
        "Respawn Button": "respawn_button.png"
    }
    
    respawn_detected = False
    for name, filename in button_templates.items():
        # Use special threshold for respawn button
        threshold = RESPAWN_BUTTON_CONFIDENCE if name == "Respawn Button" else MIN_TEMPLATE_CONFIDENCE
        template = load_template(filename)
        detected, confidence, location = test_template_match(
            screenshot, template, name, threshold
        )
        
        detections.append({
            'name': name,
            'detected': detected,
            'confidence': confidence,
            'location': location,
            'template': template,
            'type': 'button'
        })
        
        if name == "Respawn Button" and detected:
            respawn_detected = True
    
    # Create visualization
    vis_image = create_visualization(screenshot, detections, timestamp)
    
    # Generate filename
    if empty_detected or left_empty_detected:
        health_status = "EMPTY"
    elif best_health_match:
        # Only consider it valid health if mob health isn't detected nearby
        if not mob_detected or mob_confidence < best_health_confidence:
            health_status = f"HEALTH_{best_health_match.replace('% Health', '').replace(' ', '_')}"
        else:
            health_status = "MOB_HEALTH_DETECTED"
    else:
        health_status = "NO_HEALTH"
    
    respawn_status = "RESPAWN" if respawn_detected else "NO_RESPAWN"
    mob_status = "MOB" if mob_detected else "NO_MOB"
    
    filename = f"temp_detected_{health_status}_{respawn_status}_{mob_status}_{timestamp}.png"
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
    print(f"👹 Mob Health: {'YES' if mob_detected else 'NO'} ({mob_confidence:.4f})")
    print(f"🔄 Respawn Button: {'YES' if respawn_detected else 'NO'}")
    
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
    
    if mob_confidence > 0.0:
        if mob_detected:
            print(f"   Mob health detected with {mob_confidence:.4f} confidence")
            if mob_confidence < MOB_HEALTH_CONFIDENCE + 0.05:
                print(f"   💡 Consider lowering MOB_HEALTH_CONFIDENCE to {mob_confidence - 0.02:.3f}")
        else:
            if mob_confidence > MOB_HEALTH_CONFIDENCE - 0.1:
                print(f"   Mob health close to threshold ({mob_confidence:.4f} vs {MOB_HEALTH_CONFIDENCE:.3f})")
                print(f"   💡 Consider lowering MOB_HEALTH_CONFIDENCE to {mob_confidence - 0.02:.3f}")
    
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