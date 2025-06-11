"""
LICENSE: BSD 3-Clause License 
Author:Cyber-syntax
This is a script to automate healing, mana and skill usage.
This is created only for educational purposes.
"""

import time
import cv2
import numpy as np
import pyautogui
from pynput import keyboard as pynput_keyboard
from PIL import Image
import os
import platform
import argparse


#TODO: make modules better
class GameAutomation:
    def __init__(self, debug_mode=False):
        # Debug mode control - set to False for reduced CPU usage
        self.debug_mode = debug_mode
        
        # Configuration for health bar detection using pre-captured images
        self.health_images_path = "images"
        self.health_templates = {}
        self.load_health_templates()
        
        # Load respawn and empty health templates
        self.empty_health_template = None
        self.respawn_button_template = None
        self.load_respawn_templates()

        # Configuration for mana (WIP - commented out for now)
        # self.mana_bar_region = None    # (x, y, width, height) - to be set

        # Thresholds for when to use potions (0.0 to 1.0)
        self.health_threshold = 0.5  # Use health potion when below 50%
        # self.mana_threshold = 0.5    # Use mana potion when below 50% - WIP
        
        # Empty health detection state
        self.empty_health_detected = False
        self.empty_health_count = 0
        self.last_empty_health_message = 0  # For rate limiting messages
        
        # Respawn system state
        self.is_dead = False
        self.respawn_wait_start = None
        self.respawn_wait_duration = 7.5  # Wait 7.5 seconds before clicking respawn
        self.post_respawn_heal_time = None
        self.post_respawn_heal_duration = 3.0  # Heal for 3 seconds after respawn

        # Key bindings
        self.health_potion_key = "1"  # Key 1 for health potion
        # self.mana_potion_key = '2'    # Key 2 for mana potion - WIP
        self.skill_keys = ["3", "4", "5", "6"]

        # Mana functionality commented out for now - WIP
        # self.mana_color_range = {
        #     'lower': np.array([100, 100, 100]),  # Blue lower bound
        #     'upper': np.array([130, 255, 255])   # Blue upper bound
        # }

        # Safety settings
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
        # Configure screenshot tool for Linux
        if platform.system() == "Linux" and self.debug_mode:
            print("DEBUG: Running on Linux, will use scrot for screenshots")

    def load_health_templates(self):
        """Load pre-captured health bar images as templates"""
        print(
            f"DEBUG: Starting to load health templates from: {self.health_images_path}"
        )
        template_files = {
            "20": "20_health_bar.png",
            "40": "40_health_bar.png",
            "50": "50_health_bar.png",
            "full": "full_health_bar.png",
        }

        print(f"DEBUG: Looking for templates: {list(template_files.values())}")

        for percentage, filename in template_files.items():
            filepath = os.path.join(self.health_images_path, filename)
            print(f"DEBUG: Checking file: {filepath}")

            if os.path.exists(filepath):
                # Try multiple ways to load the image
                template = cv2.imread(filepath)
                if template is not None:
                    self.health_templates[percentage] = template
                    print(
                        f"SUCCESS: Loaded health template: {percentage}% - {filename} (shape: {template.shape})"
                    )

                    # Also verify the image can be used with PyAutoGUI
                    try:
                        test_img = Image.open(filepath)
                        print(
                            f"DEBUG: PIL can also load {filename} (size: {test_img.size})"
                        )
                    except Exception as e:
                        print(f"WARNING: PIL cannot load {filename}: {e}")

                else:
                    print(
                        f"ERROR: Could not load {filename} - cv2.imread returned None"
                    )
                    # Try with PIL as backup
                    try:
                        pil_img = Image.open(filepath)
                        template = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        self.health_templates[percentage] = template
                        print(
                            f"SUCCESS: Loaded via PIL: {percentage}% - {filename} (shape: {template.shape})"
                        )
                    except Exception as e:
                        print(f"ERROR: PIL also failed for {filename}: {e}")
            else:
                print(f"ERROR: Template file not found: {filepath}")

        print(f"DEBUG: Total templates loaded: {len(self.health_templates)}")
        if not self.health_templates:
            print("CRITICAL ERROR: No health templates loaded! Check your images folder.")

    def load_respawn_templates(self):
        """Load empty health bar and respawn button templates"""
        print("DEBUG: Loading respawn system templates...")
        
        # Load empty health bar template
        empty_health_path = os.path.join(self.health_images_path, "empty_health_bar.png")
        if os.path.exists(empty_health_path):
            self.empty_health_template = cv2.imread(empty_health_path)
            if self.empty_health_template is not None:
                print(f"SUCCESS: Loaded empty health template (shape: {self.empty_health_template.shape})")
            else:
                print("ERROR: Could not load empty_health_bar.png")
        else:
            print("ERROR: empty_health_bar.png not found")
            
        # Load respawn button template
        respawn_path = os.path.join(self.health_images_path, "respawn_button.png")
        if os.path.exists(respawn_path):
            self.respawn_button_template = cv2.imread(respawn_path)
            if self.respawn_button_template is not None:
                print(f"SUCCESS: Loaded respawn button template (shape: {self.respawn_button_template.shape})")
            else:
                print("ERROR: Could not load respawn_button.png")
        else:
            print("ERROR: respawn_button.png not found")
    
    def _take_screenshot_with_scrot(self):
        """Take screenshot using scrot directly"""
        import subprocess
        import tempfile
        import time
        
        try:
            # Create a named temporary file
            tmp_path = f"/tmp/screenshot_{int(time.time())}.png"
            
            # Use scrot to take screenshot
            cmd = ['scrot', tmp_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                print(f"DEBUG: scrot stderr: {result.stderr}")
                print(f"DEBUG: scrot stdout: {result.stdout}")
                raise Exception(f"scrot failed with code {result.returncode}")
            
            # Small delay to ensure file is written
            time.sleep(0.05)
            
            # Check if file exists and has content
            if not os.path.exists(tmp_path):
                raise Exception(f"Screenshot file not created: {tmp_path}")
            
            file_size = os.path.getsize(tmp_path)
            if file_size == 0:
                raise Exception(f"Screenshot file is empty: {tmp_path}")
            
            # Load the image with PIL
            from PIL import Image
            img = Image.open(tmp_path)
            
            # Clean up temp file immediately
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            if self.debug_mode:
                print(f"DEBUG: scrot screenshot successful, size: {img.size}")
            return img
            
        except Exception as e:
            if self.debug_mode:
                print(f"ERROR: scrot screenshot failed: {e}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            raise Exception(f"Screenshot failed: {e}")

    def press_key(self, key, duration=0.1):
        """Function to press key after some duration"""
        print(f"DEBUG: Pressing key '{key}' for {duration} seconds...")
        try:
            from pynput.keyboard import Key, Controller
            keyboard_controller = Controller()
            keyboard_controller.press(key)
            time.sleep(duration)
            keyboard_controller.release(key)
            time.sleep(0.1)
            print(f"DEBUG: Key '{key}' pressed successfully")
        except Exception as e:
            print(f"ERROR: Failed to press key '{key}': {e}")

    # Screenshot functionality commented out - using pre-captured images instead
    # def capture_screen_region(self, region):
    #     """Capture a specific region of the screen"""
    #     if region is None:
    #         return None
    #
    #     x, y, width, height = region
    #     screenshot = pyautogui.screenshot(region=(x, y, width, height))
    #     return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def match_health_template(self, screen_image):
        """Match current screen with health bar templates to determine health percentage"""
        if self.debug_mode:
            print(f"DEBUG: Starting template matching...")

        if not self.health_templates:
            if self.debug_mode:
                print("ERROR: No health templates loaded!")
            return 1.0

        if self.debug_mode:
            print(f"DEBUG: Screen image shape: {screen_image.shape}")

        best_match = None
        best_score = 0
        all_scores = {}
        min_threshold = 0.3  # Minimum confidence threshold

        # Convert screen image to same format as templates
        if len(screen_image.shape) == 3:
            screen_gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
            if self.debug_mode:
                print(f"DEBUG: Converted screen to grayscale, shape: {screen_gray.shape}")
        else:
            screen_gray = screen_image
            if self.debug_mode:
                print(f"DEBUG: Screen already grayscale, shape: {screen_gray.shape}")

        # Try both PyAutoGUI and OpenCV approaches
        if self.debug_mode:
            print(f"DEBUG: Testing {len(self.health_templates)} templates...")

        # Method 1: Try PyAutoGUI locateOnScreen for each template (only in debug mode)
        if self.debug_mode:
            for percentage, template in self.health_templates.items():
                template_filename = (
                    f"images/{percentage}_health_bar.png"
                    if percentage not in ["empty", "full"]
                    else f"images/{percentage}_health_bar.png"
                )
                if percentage == "empty":
                    template_filename = "images/empty_health_bar.png"
                elif percentage == "full":
                    template_filename = "images/full_health_bar.png"

                print(
                    f"DEBUG: Testing PyAutoGUI for {percentage}% using {template_filename}"
                )

                try:
                    if os.path.exists(template_filename):
                        # Try multiple confidence levels
                        for confidence in [0.9, 0.8, 0.7, 0.6, 0.5]:
                            try:
                                location = pyautogui.locateOnScreen(
                                    template_filename, confidence=confidence
                                )
                                if location:
                                    print(
                                        f"DEBUG: PyAutoGUI found {percentage}% at confidence {confidence}: {location}"
                                    )
                                    all_scores[f"{percentage}_pyautogui"] = confidence
                                    if confidence > best_score:
                                        best_score = confidence
                                        best_match = percentage
                                    break
                            except pyautogui.ImageNotFoundException:
                                continue
                            except Exception as e:
                                print(
                                    f"DEBUG: PyAutoGUI error for {percentage}% at confidence {confidence}: {e}"
                                )
                                continue
                except Exception as e:
                    print(f"DEBUG: PyAutoGUI setup error for {percentage}%: {e}")

        # Method 2: OpenCV template matching (optimized - use only one method)
        for percentage, template in self.health_templates.items():
            if self.debug_mode:
                print(
                    f"DEBUG: Testing OpenCV for template {percentage}% (shape: {template.shape})"
                )

            try:
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                if self.debug_mode:
                    print(
                        f"DEBUG: Template {percentage}% converted to grayscale, shape: {template_gray.shape}"
                    )

                # Use only the most reliable method for better performance
                method = cv2.TM_CCOEFF_NORMED
                method_name = "CCOEFF_NORMED"

                try:
                    result = cv2.matchTemplate(screen_gray, template_gray, method)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                    match_val = max_val
                    match_loc = max_loc

                    score_key = f"{percentage}_{method_name}"
                    all_scores[score_key] = match_val
                    
                    if self.debug_mode:
                        print(
                            f"DEBUG: Template {percentage}% {method_name} score: {match_val:.4f} at location {match_loc}"
                        )

                    # Use best score from any method
                    if match_val > best_score and match_val > min_threshold:
                        best_score = match_val
                        best_match = percentage
                        if self.debug_mode:
                            print(
                                f"DEBUG: New best match: {percentage}% with {method_name} score {match_val:.4f}"
                            )

                except Exception as e:
                    if self.debug_mode:
                        print(
                            f"ERROR: OpenCV {method_name} failed for template {percentage}%: {e}"
                        )

            except Exception as e:
                if self.debug_mode:
                    print(f"ERROR: Failed to process template {percentage}%: {e}")

        if self.debug_mode:
            print(f"DEBUG: All match scores: {all_scores}")
            print(f"DEBUG: Best match: {best_match}% with score {best_score:.4f}")

        # Only use result if confidence is high enough
        if best_score < min_threshold:
            if self.debug_mode:
                print(
                    f"WARNING: Best match score {best_score:.4f} below threshold {min_threshold}, defaulting to full health"
                )
            return 1.0

        # Convert percentage string to float
        if best_match == 'full':
            result_percent = 1.0
        elif best_match == 'empty':
            result_percent = 0.0
        elif best_match in ['20', '40', '50']:
            result_percent = int(best_match) / 100.0
        else:
            result_percent = 1.0  # Default to full health if no good match
            if self.debug_mode:
                print(f"WARNING: No good template match found, defaulting to full health")

        if self.debug_mode:
            print(f"DEBUG: Final health percentage: {result_percent:.2%}")
        return result_percent

    def get_health_percentage(self):
        """Get current health percentage using template matching"""
        if self.debug_mode:
            print(f"DEBUG: Taking screenshot...")
        
        try:
            # Use scrot directly for Linux systems
            if platform.system() == "Linux":
                screenshot = self._take_screenshot_with_scrot()
                if self.debug_mode:
                    print(f"DEBUG: Screenshot taken with scrot, size: {screenshot.size}")
            else:
                screenshot = pyautogui.screenshot()
                if self.debug_mode:
                    print(f"DEBUG: Screenshot taken with pyautogui, size: {screenshot.size}")
            
            screen_image = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            if self.debug_mode:
                print(f"DEBUG: Screenshot converted to OpenCV format, shape: {screen_image.shape}")

            # Optional: Save screenshot for debugging (only in debug mode)
            if self.debug_mode:
                cv2.imwrite("debug_screenshot.png", screen_image)
                print(f"DEBUG: Screenshot saved as debug_screenshot.png")

                # Also save a smaller region if templates are small
                if self.health_templates:
                    # Get template size for reference
                    sample_template = next(iter(self.health_templates.values()))
                    th, tw = sample_template.shape[:2]
                    print(f"DEBUG: Template reference size: {tw}x{th}")

                    # Save multiple regions for testing
                    regions_to_test = [
                        (0, 0, tw * 3, th * 3),  # Top-left corner
                        (
                            screen_image.shape[1] // 4,
                            screen_image.shape[0] // 4,
                            tw * 3,
                            th * 3,
                        ),  # Quarter screen
                        (
                            screen_image.shape[1] // 2,
                            screen_image.shape[0] // 2,
                            tw * 3,
                            th * 3,
                        ),  # Center
                    ]

                    for i, (x, y, w, h) in enumerate(regions_to_test):
                        x = max(0, min(x, screen_image.shape[1] - w))
                        y = max(0, min(y, screen_image.shape[0] - h))
                        w = min(w, screen_image.shape[1] - x)
                        h = min(h, screen_image.shape[0] - y)

                        region = screen_image[y : y + h, x : x + w]
                        cv2.imwrite(f"debug_region_{i}.png", region)
                        print(f"DEBUG: Saved test region {i} as debug_region_{i}.png")

            # Match with health templates
            health_percent = self.match_health_template(screen_image)
            return health_percent

        except Exception as e:
            print(f"ERROR: Failed to get health percentage: {e}")
            return 1.0

    # Mana functionality commented out - WIP
    # def get_mana_percentage(self):
    #     """Get current mana percentage - WIP"""
    #     # This will be implemented later with mana bar images
    #     return 1.0

    def is_health_empty(self):
        """Check if health bar is completely empty using dedicated template matching"""
        if self.empty_health_template is None:
            # Fallback to percentage-based detection
            health_percent = self.get_health_percentage()
            if health_percent == 0.0:
                if self.debug_mode:
                    print("DEBUG: Health detected as exactly 0% (empty template matched)")
                return True
            elif health_percent <= 0.01:  # Less than 1% could also indicate death
                if self.debug_mode:
                    print(f"DEBUG: Health extremely low ({health_percent:.2%}), treating as empty")
                return True
            return False
            
        # Use template matching for empty health detection
        try:
            screenshot = self._take_screenshot_with_scrot()
            if screenshot is None:
                return False
                
            # Convert screenshot to the same format as template
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_cv, self.empty_health_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            # Consider it a match if confidence is above 0.7
            is_empty = max_val > 0.7
            
            if self.debug_mode and is_empty:
                print(f"DEBUG: Empty health bar detected with confidence: {max_val:.3f}")
                
            return is_empty
            
        except Exception as e:
            if self.debug_mode:
                print(f"DEBUG: Error in empty health detection: {e}")
            return False

    def detect_respawn_button(self):
        """Detect if respawn button is visible on screen"""
        if self.respawn_button_template is None:
            return False, None
            
        try:
            screenshot = self._take_screenshot_with_scrot()
            if screenshot is None:
                return False, None
                
            # Convert screenshot to the same format as template
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_cv, self.respawn_button_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            # Consider it a match if confidence is above 0.8
            if max_val > 0.8:
                # Calculate center of the button
                h, w = self.respawn_button_template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                
                if self.debug_mode:
                    print(f"DEBUG: Respawn button detected with confidence: {max_val:.3f} at ({center_x}, {center_y})")
                    
                return True, (center_x, center_y)
            
            return False, None
            
        except Exception as e:
            if self.debug_mode:
                print(f"DEBUG: Error in respawn button detection: {e}")
            return False, None

    def click_respawn_button(self):
        """Click the respawn button if detected"""
        button_found, button_pos = self.detect_respawn_button()
        
        if button_found and button_pos:
            print(f"🔄 Clicking respawn button at position {button_pos}")
            pyautogui.click(button_pos[0], button_pos[1])
            time.sleep(1.0)  # Wait after clicking
            return True
        
        return False

    def use_health_potion(self, force_heal=False):
        """Function to heal when the bar decreases - uses multiple potions based on health level"""
        if self.debug_mode:
            print("DEBUG: Checking health status...")
            print(f"DEBUG: Health threshold set to: {self.health_threshold:.2%}")

        # Check if we're in post-respawn healing mode
        if force_heal:
            if self.debug_mode:
                print("DEBUG: Force healing mode (post-respawn)")
            potions_to_use = 2  # Use 2 potions after respawn
            print(f"Post-respawn healing: Using {potions_to_use} health potion(s) (Key 1)...")
            
            for i in range(potions_to_use):
                if self.debug_mode:
                    print(f"  Pressing potion {i+1}/{potions_to_use}")
                self.press_key(self.health_potion_key)
                
                # Wait between multiple potion presses (except after the last one)
                if i < potions_to_use - 1:
                    time.sleep(0.5)  # Slightly longer delay for post-respawn healing
                    
            # Wait for potions to take effect
            time.sleep(2.0)  # Longer wait for post-respawn healing
            if self.debug_mode:
                print(f"DEBUG: Finished post-respawn healing with {potions_to_use} potion(s)")
            return True

        # First check if health is empty to avoid wasting potions
        if self.is_health_empty():
            if not self.empty_health_detected:  # Only show message on first detection
                print("⚠️  EMPTY HEALTH BAR DETECTED - Character appears to be dead/incapacitated")
                print("   Stopping potion usage to prevent waste. Waiting for revival...")
            return "empty"  # Special return value to indicate empty health

        health_percent = self.get_health_percentage()
        
        # Always show health percentage for monitoring
        print(f"Health: {health_percent:.2%}")

        # Determine how many potions to use based on health level
        potions_to_use = 0
        
        if health_percent <= 0.20:  # 20% or lower
            potions_to_use = 4
            if self.debug_mode:
                print(f"DEBUG: Critical health ({health_percent:.2%}) - using 4 potions")
        elif health_percent <= 0.40:  # 40% or lower
            potions_to_use = 2
            if self.debug_mode:
                print(f"DEBUG: Low health ({health_percent:.2%}) - using 2 potions")
        elif health_percent <= 0.50:  # 50% or lower
            potions_to_use = 1
            if self.debug_mode:
                print(f"DEBUG: Medium health ({health_percent:.2%}) - using 1 potion")
        else:
            if self.debug_mode:
                print(f"DEBUG: Health {health_percent:.2%} > 50%, no potion needed")
            return False

        if potions_to_use > 0:
            print(f"Using {potions_to_use} health potion(s) (Key 1)...")
            
            for i in range(potions_to_use):
                if self.debug_mode:
                    print(f"  Pressing potion {i+1}/{potions_to_use}")
                self.press_key(self.health_potion_key)
                
                # Wait between multiple potion presses (except after the last one)
                if i < potions_to_use - 1:
                    time.sleep(0.3)  # Short delay between potions
                    
            # Wait for potions to take effect
            time.sleep(1.5)
            if self.debug_mode:
                print(f"DEBUG: Finished using {potions_to_use} potion(s)")
            return True
            
        return False

    # Mana potion functionality commented out - WIP
    # def use_mana_potion(self):
    #     """Function to increase mana when the mana bar decreases - WIP"""
    #     mana_percent = self.get_mana_percentage()
    #     print(f"Mana: {mana_percent:.2%}")
    #
    #     if mana_percent < self.mana_threshold:
    #         print("Using mana potion (Key 2)...")
    #         self.press_key(self.mana_potion_key)
    #         time.sleep(1)  # Wait for potion to take effect
    #         return True
    #     return False

    def use_skill(self, skill_key=None):
        """Function to use skills on entities"""
        if skill_key is None:
            skill_key = self.skill_keys[0]  # Default to first skill

        print(f"Using skill: {skill_key}")
        self.press_key(skill_key)

    # Setup regions functionality commented out - using pre-captured images instead
    # def setup_regions(self):
    #     """Interactive setup for health and mana bar regions - not needed with templates"""
    #     print("Using pre-captured health bar images - no region setup needed")

    # Color calibration commented out - using template matching instead
    # def calibrate_colors(self):
    #     """Calibrate color ranges for better detection - not needed with templates"""
    #     print("Using template matching - no color calibration needed")

    def run_automation(self):
        """Main automation loop with respawn system"""
        print("Starting automation... Press 'q' to quit")
        print("Health monitoring active (Key 1 for health potions)")
        print("Respawn system active - will auto-respawn when dead")
        print("Mana functionality is WIP - coming soon!")
        print(f"DEBUG: Templates loaded: {list(self.health_templates.keys())}")
        print("DEBUG: Starting main automation loop...")

        # Set up keyboard listener for quit key
        self.automation_running = True
        
        def on_key_press(key):
            try:
                if hasattr(key, 'char') and key.char == 'q':
                    print("Stopping automation...")
                    self.automation_running = False
                    return False  # Stop listener
            except AttributeError:
                pass
        
        # Start keyboard listener in background
        listener = pynput_keyboard.Listener(on_press=on_key_press)
        listener.start()

        loop_count = 0
        try:
            while self.automation_running:
                loop_count += 1
                if self.debug_mode:
                    print(f"\nDEBUG: Automation loop #{loop_count}")

                current_time = time.time()

                # Handle post-respawn healing phase
                if self.post_respawn_heal_time is not None:
                    elapsed_heal_time = current_time - self.post_respawn_heal_time
                    if elapsed_heal_time < self.post_respawn_heal_duration:
                        print(f"🩹 Post-respawn healing phase ({elapsed_heal_time:.1f}s/{self.post_respawn_heal_duration}s)")
                        self.use_health_potion(force_heal=True)
                        time.sleep(1.0)
                        continue
                    else:
                        print("✅ Post-respawn healing completed - resuming normal monitoring")
                        self.post_respawn_heal_time = None

                # Handle respawn waiting phase
                if self.respawn_wait_start is not None:
                    elapsed_wait_time = current_time - self.respawn_wait_start
                    if elapsed_wait_time < self.respawn_wait_duration:
                        remaining_time = self.respawn_wait_duration - elapsed_wait_time
                        print(f"⏳ Waiting for respawn timeout: {remaining_time:.1f}s remaining")
                        time.sleep(1.0)
                        continue
                    else:
                        # Try to click respawn button
                        if self.click_respawn_button():
                            print("🎯 Respawn button clicked! Starting post-respawn healing...")
                            self.respawn_wait_start = None
                            self.is_dead = False
                            self.empty_health_detected = False
                            self.post_respawn_heal_time = current_time
                            continue
                        else:
                            print("❌ Respawn button not found, extending wait...")
                            self.respawn_wait_start = current_time  # Reset wait timer
                            continue

                # Check and use health potion if needed
                if self.debug_mode:
                    print("DEBUG: Calling use_health_potion()...")
                potion_result = self.use_health_potion()

                # Handle empty health bar detection
                if potion_result == "empty":
                    if not self.is_dead:
                        print("💀 Character death detected!")
                        self.is_dead = True
                        self.empty_health_detected = True
                        
                        # Check immediately for respawn button
                        button_found, _ = self.detect_respawn_button()
                        if button_found:
                            print("🔄 Respawn button available immediately!")
                            self.respawn_wait_start = current_time - self.respawn_wait_duration  # Skip wait
                        else:
                            print(f"⏳ Starting respawn wait timer ({self.respawn_wait_duration}s)")
                            self.respawn_wait_start = current_time
                    
                    # Continue to next iteration to handle respawn logic
                    time.sleep(1.0)
                    continue
                    
                elif self.empty_health_detected and potion_result != "empty":
                    # Health has been restored, resume normal operation
                    print("✅ Health restored! Character has been revived - resuming normal automation...")
                    self.empty_health_detected = False
                    self.empty_health_count = 0
                    self.last_empty_health_message = 0
                    self.is_dead = False
                    self.respawn_wait_start = None
                    self.post_respawn_heal_time = None

                if self.debug_mode:
                    if potion_result:
                        print("DEBUG: Health potion was used")
                    else:
                        print("DEBUG: No health potion needed")

                # Mana checking commented out - WIP
                # self.use_mana_potion()

                # Normal delay for active health monitoring
                delay_time = 2.0
                if self.debug_mode:
                    print(f"DEBUG: Waiting {delay_time} seconds before next check...")
                time.sleep(delay_time)

        except KeyboardInterrupt:
            print("Automation stopped by user")
        except Exception as e:
            print(f"ERROR: Automation loop failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            listener.stop()




def main():
    """Main function to run the automation"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Game Automation Script')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode (increases CPU usage)')
    args = parser.parse_args()
    
    debug_mode = args.debug
    
    if debug_mode:
        print("DEBUG: Starting main function...")
    else:
        print("Starting Game Automation (optimized mode)...")

    try:
        automation = GameAutomation(debug_mode=debug_mode)
        if debug_mode:
            print("DEBUG: GameAutomation instance created")
        else:
            print("GameAutomation instance created")



        print("\nGame Automation - Health Monitoring Active")
        print("=========================================")
        print("Health bar templates loaded from images folder")
        print("Key 1: Health Potion")
        print("Mana functionality: WIP (Work In Progress)")
        if debug_mode:
            print("Debug mode: ENABLED (higher CPU usage)")
        else:
            print("Debug mode: DISABLED (optimized for lower CPU usage)")
        print("\nFeatures:")
        print("- Smart health potion usage based on health level")
        print("- Empty health detection (stops potions when dead/incapacitated)")
        print("- Automatic revival detection and resumption")
        print("\nCommands:")
        print("- Press 'r' to start/restart automation")
        print("- Press 'q' to quit")

        if debug_mode:
            print("DEBUG: Entering main command loop...")
        print("Press 'r' to start automation, 'q' to quit")
        
        # Set up global key listener
        automation_started = False
        main_running = True
        
        def on_global_key_press(key):
            nonlocal automation_started, main_running
            try:
                if hasattr(key, 'char'):
                    if key.char == 'r' and not automation_started:
                        if debug_mode:
                            print("DEBUG: 'r' key pressed - starting automation")
                        else:
                            print("Starting automation...")
                        automation_started = True
                        automation.run_automation()
                        automation_started = False
                    elif key.char == 'q':
                        if debug_mode:
                            print("DEBUG: 'q' key pressed - quitting")
                        else:
                            print("Quitting...")
                        main_running = False
                        return False  # Stop listener
            except AttributeError:
                pass
        
        listener = pynput_keyboard.Listener(on_press=on_global_key_press)
        listener.start()
        
        try:
            while main_running:
                time.sleep(0.1)
        finally:
            listener.stop()

    except Exception as e:
        print(f"CRITICAL ERROR in main(): {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

