import time
import cv2
import numpy as np
from mss import mss
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
# Only capture the left-hand 1024×768 of your 2K monitor:
MONITOR_REGION = {"top": 0, "left": 0, "width": 1024, "height": 768}

# Base directory for your PNG templates:
IMAGES_DIR = Path(__file__).parent.parent / "auto_warrior" / "images"

# Per-template confidence thresholds
TEMPLATE_CONFIG = [
    # Health bars (use same threshold for all health % templates)
    *[
        {"name": f"{pct}% Health", "filename": f"{pct}_health_bar.png", "threshold": 0.75}
        for pct in ["20", "40", "50", "70", "90", "full"]
    ],
    # Empty / left‐empty health
    {"name": "Empty Health",      "filename": "empty_health_bar.png",     "threshold": 0.70},
    {"name": "Left Empty Health", "filename": "left_empty_health_bar.png", "threshold": 0.70},

    # Respawn button
    {"name": "Respawn Button",    "filename": "respawn_button.png",       "threshold": 0.70},

    # Other game objects you mentioned
    {"name": "Mob Health",        "filename": "mob_health_bar.png",        "threshold": 0.75},
    {"name": "Object Yang",       "filename": "object_yang.png",           "threshold": 0.75},
    {"name": "Health Potion v1",  "filename": "object_health_pot.png",     "threshold": 0.75},
    {"name": "Health Potion v2",  "filename": "object_health_pot_v2.png",  "threshold": 0.75},
    {"name": "Auto Hunt Start",   "filename": "auto_hunt_start_button.png","threshold": 0.75},
]

# Color map for different kinds of templates (BGR)
COLOR_MAP = {
    "Health":       (0, 255, 0),   # green
    "Empty":        (0, 200, 200), # yellowish
    "Respawn":      (0, 0, 255),   # red
    "Mob":          (255, 0, 0),   # blue
    "Object":       (255, 255, 0), # cyan
    "Auto Hunt":    (255, 0, 255), # magenta
    "Default":      (200, 200, 200),
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def load_templates():
    """
    Load all templates into memory, converting to grayscale arrays.
    Returns a list of dicts:
      { name, gray_template, threshold, color }
    """
    loaded = []
    for cfg in TEMPLATE_CONFIG:
        path = IMAGES_DIR / cfg["filename"]
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"Template not found: {path}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # pick a color by keyword in name
        if "Health" in cfg["name"] and "%" in cfg["name"]:
            color = COLOR_MAP["Health"]
        elif "Empty" in cfg["name"]:
            color = COLOR_MAP["Empty"]
        elif "Respawn" in cfg["name"]:
            color = COLOR_MAP["Respawn"]
        elif "Mob" in cfg["name"]:
            color = COLOR_MAP["Mob"]
        elif "Object" in cfg["name"]:
            color = COLOR_MAP["Object"]
        elif "Auto Hunt" in cfg["name"]:
            color = COLOR_MAP["Auto Hunt"]
        else:
            color = COLOR_MAP["Default"]

        loaded.append({
            "name":      cfg["name"],
            "template":  gray,
            "threshold": cfg["threshold"],
            "color":     color,
        })
    return loaded

def grab_region(region=MONITOR_REGION):
    """Grab the specified rectangle via MSS, return a contiguous BGR image."""
    with mss() as sct:
        sct_img = sct.grab(region)
        arr = np.array(sct_img)[:, :, :3]  # drop alpha
        return np.ascontiguousarray(arr)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────
def main_loop():
    templates = load_templates()
    cv2.namedWindow("Live Detection", cv2.WINDOW_NORMAL)
    prev_time = time.time()

    while True:
        frame = grab_region()
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        display = frame.copy()

        # For each template, run matchTemplate and draw if above threshold
        for tpl_cfg in templates:
            res = cv2.matchTemplate(gray_frame, tpl_cfg["template"], cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val >= tpl_cfg["threshold"]:
                x, y = max_loc
                h, w = tpl_cfg["template"].shape
                cv2.rectangle(display, (x, y), (x + w, y + h), tpl_cfg["color"], 2)
                cv2.putText(
                    display,
                    f"{tpl_cfg['name']} ({max_val:.2f})",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    tpl_cfg["color"],
                    1,
                    cv2.LINE_AA,
                )

        # Draw FPS
        now = time.time()
        fps = 1.0 / (now - prev_time) if now != prev_time else 0.0
        prev_time = now
        cv2.putText(
            display,
            f"FPS: {fps:.1f}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Show and handle quit
        cv2.imshow("Live Detection", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main_loop()