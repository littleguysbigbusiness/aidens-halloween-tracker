"""
Click out your detection zone (e.g. your yard/walkway) on a live frame from
the camera, then paste the printed coordinates into config.DETECTION_ZONE.

Usage:
    python pick_zone.py

Click each corner of the area in order (e.g. around your porch/walkway).
Press ENTER when done, 'u' to undo the last point, 'r' to reset, 'q' to quit
without saving.
"""

import cv2
import config
from zone import save_zone_to_config

points = []


def on_click(event, x, y, flags, userdata):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))


def main():
    cap = cv2.VideoCapture(config.RTSP_URL)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        print("Could not grab a frame from the camera. Check config.RTSP_URL.")
        return

    h, w = frame.shape[:2]
    if w > config.PROCESS_WIDTH:
        scale = config.PROCESS_WIDTH / w
        frame = cv2.resize(frame, (config.PROCESS_WIDTH, int(h * scale)))

    base = frame.copy()
    cv2.namedWindow("Pick detection zone")
    cv2.setMouseCallback("Pick detection zone", on_click)

    print("Click corners of your detection zone in order.")
    print("ENTER = done, 'u' = undo, 'r' = reset, 'q' = quit without saving.")

    while True:
        display = base.copy()
        for i, p in enumerate(points):
            cv2.circle(display, p, 5, (0, 0, 255), -1)
            cv2.putText(display, str(i + 1), (p[0] + 6, p[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        if len(points) > 1:
            cv2.polylines(display, [cv2_points(points)], isClosed=True, color=(255, 255, 0), thickness=2)

        cv2.imshow("Pick detection zone", display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord("q"):
            print("Quit without saving.")
            break
        elif key == ord("u") and points:
            points.pop()
        elif key == ord("r"):
            points.clear()
        elif key in (13, 10):  # ENTER
            if len(points) < 3:
                print("Need at least 3 points for a zone.")
                continue
            save_zone_to_config(points)
            print(f"\nSaved to config.py: DETECTION_ZONE = {points}")
            break

    cv2.destroyAllWindows()


def cv2_points(pts):
    import numpy as np
    return np.array(pts, dtype=np.int32)


if __name__ == "__main__":
    main()
