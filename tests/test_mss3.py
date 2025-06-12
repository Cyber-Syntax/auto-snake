import time
import cv2
import numpy as np
from mss import mss
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
# Change this to your desired region. Here: top-left corner, size 1024×768.
MONITOR_REGION = {
    "top": 0,  # y-offset of capture
    "left": 0,  # x-offset of capture
    "width": 1024,  # only capture the left 1024 pixels
    "height": 768,  # only capture 768 pixels vertically
}

# Threshold for deciding a "hit"
MIN_TEMPLATE_CONFIDENCE = 0.75

# Where your templates live
IMAGES_DIR = Path(__file__).parent.parent / "auto_warrior" / "images"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def load_health_templates():
    """Load all health‐bar templates into grayscale numpy arrays."""
    templates = {}
    for pct in ["20", "40", "50", "70", "90", "full", "empty"]:
        fname = f"{pct}_health_bar.png"
        path = IMAGES_DIR / fname
        tpl = cv2.imread(str(path))
        if tpl is None:
            raise FileNotFoundError(f"Missing template: {path}")
        # convert once at startup
        tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
        templates[pct] = tpl_gray
    return templates


def grab_region(region=MONITOR_REGION):
    """Grab only the rectangle defined by MONITOR_REGION."""
    with mss() as sct:
        sct_img = sct.grab(region)
        # sct.grab is BGRA; drop alpha and ensure C-contiguous
        img = np.array(sct_img)[:, :, :3]
        return np.ascontiguousarray(img)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────
def main_loop():
    templates = load_health_templates()
    cv2.namedWindow("Live Health Detection", cv2.WINDOW_NORMAL)
    prev_time = time.time()

    while True:
        # 1) Grab only the left-side region — much less data to process!
        frame = grab_region()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        best_pct = None
        best_score = 0.0

        # 2) Run template matching only on that small ROI
        for pct, tpl in templates.items():
            res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
            if score > best_score:
                best_score, best_pct, best_loc = score, pct, loc

        # 3) Overlay result
        display = frame.copy()
        if best_score > MIN_TEMPLATE_CONFIDENCE:
            x, y = best_loc
            h, w = templates[best_pct].shape
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            label = f"{best_pct}% ({best_score:.2f})"
        else:
            label = f"Unknown ({best_score:.2f})"

        # Draw label
        cv2.putText(
            display, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2
        )

        # 4) FPS counter
        now = time.time()
        fps = 1.0 / (now - prev_time)
        prev_time = now
        cv2.putText(
            display,
            f"FPS: {fps:.1f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        # 5) Show and handle keys
        cv2.imshow("Live Health Detection", display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main_loop()
