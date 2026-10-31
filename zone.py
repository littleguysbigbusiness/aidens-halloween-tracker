"""Helpers for the optional detection-zone polygon (see config.DETECTION_ZONE)."""

import re

import numpy as np
import cv2


def point_in_zone(point, zone):
    """zone: list of (x, y) points, or None/empty to mean 'everywhere'."""
    if not zone:
        return True
    polygon = np.array(zone, dtype=np.int32)
    result = cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False)
    return result >= 0


def foot_point(box):
    """Bottom-center of a box — a person's feet, the natural point to test
    against a yard/walkway zone (more reliable than the box center, which
    shifts a lot as someone crouches, reaches for candy, etc.)."""
    x1, y1, x2, y2 = box
    return ((x1 + x2) // 2, y2)


def draw_zone(frame, zone):
    if not zone:
        return
    polygon = np.array(zone, dtype=np.int32)
    cv2.polylines(frame, [polygon], isClosed=True, color=(255, 255, 0), thickness=2)


def save_zone_to_config(zone, config_path="config.py"):
    """Rewrites the DETECTION_ZONE line in config.py so the new zone survives a restart."""
    with open(config_path, "r") as f:
        text = f.read()

    new_line = f"DETECTION_ZONE = {zone}"
    new_text, count = re.subn(r"^DETECTION_ZONE\s*=.*$", new_line, text, count=1, flags=re.MULTILINE)
    if count == 0:
        raise ValueError("Could not find DETECTION_ZONE line in config.py")

    with open(config_path, "w") as f:
        f.write(new_text)
