"""
In-memory, privacy-preserving re-entry tracker.

Visitors are represented only by:
  - a short-lived integer visit id
  - a coarse color-histogram appearance signature (clothing/overall look)
  - first-seen / last-seen timestamps

Nothing here is a biometric identifier, nothing is written to disk, and
everything is discarded once REENTRY_WINDOW_SECONDS has passed since the
visitor was last seen. There is no face data anywhere in this file.
"""

import time
import itertools
import numpy as np
import cv2

import config


def _appearance_signature(frame_bgr, box):
    """Coarse HSV color-histogram signature for a bounding box crop.

    This is deliberately low-fidelity appearance matching (think "person in
    an orange hoodie"), not identity recognition. It's only meant to bridge
    a few seconds/minutes of someone stepping out of frame.
    """
    x1, y1, x2, y2 = box
    crop = frame_bgr[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten().astype(np.float32)


def _cosine_similarity(a, b):
    if a is None or b is None:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class Visit:
    __slots__ = ("visit_id", "signature", "first_seen", "last_seen", "active", "confirmed")

    def __init__(self, visit_id, signature, now):
        self.visit_id = visit_id
        self.signature = signature
        self.first_seen = now
        self.last_seen = now
        self.active = True
        self.confirmed = False


class ReentryTracker:
    """Tracks distinct trick-or-treater visits without storing any biometric data."""

    def __init__(self, initial_count=0):
        self._visits = {}
        self._id_counter = itertools.count(1)
        self.total_unique_visits = initial_count

    def _prune_expired(self, now):
        expired = [
            vid for vid, v in self._visits.items()
            if (now - v.last_seen) > config.REENTRY_WINDOW_SECONDS
        ]
        for vid in expired:
            del self._visits[vid]

    def _mark_departed(self, now):
        for v in self._visits.values():
            if v.active and (now - v.last_seen) > config.MAX_MISSING_SECONDS_BEFORE_INACTIVE:
                v.active = False

    def update(self, frame_bgr, boxes):
        """Feed current-frame person boxes.

        Returns list of (visit_id, box, just_confirmed, confirmed). A visit
        is only added to total_unique_visits (just_confirmed=True once, the
        frame it happens) after being continuously present for
        config.COUNT_DEBOUNCE_SECONDS — this filters out one-frame flicker
        detections.
        """
        now = time.time()
        self._mark_departed(now)
        self._prune_expired(now)

        results = []
        used_visit_ids = set()

        for box in boxes:
            sig = _appearance_signature(frame_bgr, box)
            if sig is None:
                continue

            best_vid, best_score = None, 0.0
            for vid, v in self._visits.items():
                if vid in used_visit_ids:
                    continue
                score = _cosine_similarity(sig, v.signature)
                if score > best_score:
                    best_vid, best_score = vid, score

            if best_vid is not None and best_score >= config.SIMILARITY_THRESHOLD:
                v = self._visits[best_vid]
                v.last_seen = now
                v.signature = sig  # drift the signature to the latest view
                v.active = True
                used_visit_ids.add(best_vid)
            else:
                vid = next(self._id_counter)
                v = Visit(vid, sig, now)
                self._visits[vid] = v
                used_visit_ids.add(vid)

            just_confirmed = False
            if not v.confirmed and (now - v.first_seen) >= config.COUNT_DEBOUNCE_SECONDS:
                v.confirmed = True
                self.total_unique_visits += 1
                just_confirmed = True

            results.append((v.visit_id, box, just_confirmed, v.confirmed))

        return results

    def active_confirmed_count(self):
        """How many confirmed visitors are in the zone right now (for the
        'biggest group at once' stat)."""
        return sum(1 for v in self._visits.values() if v.confirmed and v.active)

    def manual_adjust(self, delta):
        """Manually nudge the tally up or down (e.g. to correct a miscount)."""
        self.total_unique_visits = max(0, self.total_unique_visits + delta)
