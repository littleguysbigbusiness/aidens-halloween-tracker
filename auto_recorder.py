"""Automatically records a video clip around each confirmed visit.

This is plain video capture — not facial recognition, no biometric data —
exactly like any doorbell camera's "someone's here" clip. A new recording
is seeded with the shared ClipBuffer's pre-roll (the ~CLIP_BUFFER_SECONDS
leading up to detection), then keeps recording forward in real time until
AUTO_VIDEO_TOTAL_SECONDS have elapsed since it started.

If another visit is confirmed while a recording is already running, the
recording window is simply extended rather than starting a second
overlapping file, so a cluster of visitors arriving close together end up
together in one combined video instead of several.
"""

import os
import time

import cv2

import config

CODEC = "XVID"
EXTENSION = ".avi"


class AutoRecorder:
    def __init__(self):
        self._writer = None
        self._end_time = 0.0
        self._path = None

    @property
    def is_recording(self):
        return self._writer is not None

    def trigger(self, clip_buffer):
        """Call when a visit is confirmed."""
        now = time.time()
        forward_seconds = config.AUTO_VIDEO_TOTAL_SECONDS - config.CLIP_BUFFER_SECONDS

        if self._writer is not None:
            # Already recording — fold this visit into the same video
            # instead of starting a second, overlapping one.
            self._end_time = max(self._end_time, now + forward_seconds)
            return

        preroll = clip_buffer.get_buffered_frames()
        if not preroll:
            return

        os.makedirs(config.AUTO_VIDEO_DIR, exist_ok=True)
        timestamps = [t for t, _ in preroll]
        frames = [f for _, f in preroll]
        duration = max(timestamps[-1] - timestamps[0], 0.001)
        fps = max(1.0, len(frames) / duration)

        h, w = frames[0].shape[:2]
        self._path = os.path.join(config.AUTO_VIDEO_DIR, time.strftime(f"visit_%Y%m%d_%H%M%S{EXTENSION}"))
        writer = cv2.VideoWriter(self._path, cv2.VideoWriter_fourcc(*CODEC), fps, (w, h))
        if not writer.isOpened():
            writer.release()
            self._path = None
            return

        for f in frames:
            writer.write(f)

        self._writer = writer
        self._end_time = now + forward_seconds

    def add_frame(self, frame):
        """Call every loop iteration regardless of whether a visit was just
        confirmed. Returns the finished file path once the recording
        window closes, else None."""
        if self._writer is None:
            return None

        self._writer.write(frame)

        if time.time() >= self._end_time:
            self._writer.release()
            path = self._path
            self._writer = None
            self._path = None
            return path

        return None
