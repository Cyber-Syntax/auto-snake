import time
from pathlib import Path

import cv2
import numpy as np
from mss import mss

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
MONITOR_REGION = {"top": 0, "left": 0, "width": 1200, "height": 924}
IMAGES_DIR = Path(__file__).parent.parent / "auto_warrior" / "images"

# Template definitions: name, filename, matching threshold
TEMPLATE_CONFIG = [
    *[
        {"name": f"{pct}% Health", "file": f"{pct}_health_bar.png", "th": 0.1}
        for pct in ["20", "40", "50", "70", "90", "full"]
    ],
    *[
        {"name": f"{pct}% Mana", "file": f"{pct}_mana_bar.png", "th": 0.1}
        for pct in ["20", "40", "50", "70", "90", "full"]
    ],
    {"name": "Empty Health", "file": "empty_health_bar.png", "th": 0.1},
    {"name": "Left Empty Health", "file": "left_empty_health_bar.png", "th": 0.1},
    {"name": "Respawn Button", "file": "respawn_button.png", "th": 0.1},
    {"name": "Mob Health", "file": "mob_full_health_bar.png", "th": 0.1},
    {"name": "Object Yang", "file": "object_yang.png", "th": 0.1},
    {"name": "Health Potion v1", "file": "object_health_pot.png", "th": 0.1},
    {"name": "Health Potion v2", "file": "object_health_pot_v2.png", "th": 0.1},
    {"name": "Auto Hunt Start", "file": "auto_hunt_start_button.png", "th": 0.1},
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def load_templates():
    """
    Load each PNG into a grayscale array, ready for matching.
    Returns a list of dicts {name, tpl_gray, threshold}.
    """
    out = []
    for cfg in TEMPLATE_CONFIG:
        path = IMAGES_DIR / cfg["file"]
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"Cannot load template: {path}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        out.append(
            {
                "name": cfg["name"],
                "template": gray,
                "threshold": cfg["th"],
            }
        )
    return out


def grab_region(region=MONITOR_REGION):
    """
    Grab just the specified rectangle via MSS,
    drop alpha channel and ensure C-contiguous.
    """
    with mss() as sct:
        shot = sct.grab(region)
        arr = np.array(shot)[:, :, :3]
        return np.ascontiguousarray(arr)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────
def main_loop():
    templates = load_templates()
    cv2.namedWindow("Live Debug Detection", cv2.WINDOW_NORMAL)
    prev_time = time.time()

    while True:
        frame = grab_region()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        disp = frame.copy()

        # Collect scores for overlay text
        overlay_lines = []

        # 1) Match every template and draw its box+label
        for cfg in templates:
            tpl = cfg["template"]
            th = cfg["threshold"]
            name = cfg["name"]

            # run matchTemplate
            res = cv2.matchTemplate(gray, tpl, cv2.TM_SQDIFF_NORMED)
            min_val, _, min_loc, _ = cv2.minMaxLoc(res)
            score = min_val  # For SQDIFF_NORMED, lower is better
            overlay_lines.append(f"{name}: {score:.3f}")

            x, y = min_loc  # Use minimum location for SQDIFF_NORMED
            h, w = tpl.shape

            # hit = thick colored; miss = thin gray
            # For SQDIFF_NORMED: lower scores are better, so check <= threshold
            if score <= th:
                color = (0, 255, 0)  # green for hit
                thickness = 3
            else:
                color = (200, 200, 200)  # light gray for miss
                thickness = 1

            # draw rectangle and label
            cv2.rectangle(disp, (x, y), (x + w, y + h), color, thickness)
            cv2.putText(
                disp, name, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA
            )

        # 2) Draw all confidences in a column on the left
        for idx, line in enumerate(overlay_lines):
            cv2.putText(
                disp,
                line,
                (5, 20 + idx * 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 3) Draw FPS
        now = time.time()
        fps = 1.0 / (now - prev_time) if now != prev_time else 0.0
        prev_time = now
        cv2.putText(
            disp,
            f"FPS: {fps:.1f}",
            (5, disp.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
            cv2.LINE_AA,
        )

        # 4) Show and quit
        cv2.imshow("Live Debug Detection", disp)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main_loop()
