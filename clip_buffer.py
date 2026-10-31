"""Rolling in-memory video buffer with manual save-to-disk.

Saving is always a deliberate human action (press 's') — nothing here
auto-saves or auto-uploads video of anyone.
"""

import collections
import os
import time

import cv2

import config


SAVE_COOLDOWN_SECONDS = 3.0

# H.264 (avc1) needs an OpenH264 DLL this machine doesn't have — OpenCV's
# VideoWriter reports isOpened()==True for it anyway and then silently
# writes a broken file, so it can't be detected or trusted at runtime.
# XVID/.avi is genuinely functional here and plays natively in VLC/Windows
# Media Player without extra codec installs.
CODEC = "XVID"
EXTENSION = ".avi"


class ClipBuffer:
    def __init__(self):
        self._buffer = collections.deque()
        self._last_save_time = 0.0

    def add_frame(self, frame):
        now = time.time()
        self._buffer.append((now, frame.copy()))
        cutoff = now - config.CLIP_BUFFER_SECONDS
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

    def get_buffered_frames(self):
        """Returns the current pre-roll as a list of (timestamp, frame).
        Used by AutoRecorder to seed a new recording with the ~30s leading
        up to the moment a visit was detected."""
        return list(self._buffer)

    def save_clip(self):
        """Writes the buffered frames to a local mp4. Returns the file path,
        or None if the buffer is empty or a save just happened (cooldown)."""
        now = time.time()
        if now - self._last_save_time < SAVE_COOLDOWN_SECONDS:
            return None
        if not self._buffer:
            return None

        os.makedirs(config.CLIPS_DIR, exist_ok=True)
        timestamps = [t for t, _ in self._buffer]
        frames = [f for _, f in self._buffer]
        duration = max(timestamps[-1] - timestamps[0], 0.001)
        fps = max(1.0, len(frames) / duration)

        h, w = frames[0].shape[:2]
        filename = os.path.join(config.CLIPS_DIR, time.strftime(f"clip_%Y%m%d_%H%M%S{EXTENSION}"))

        writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*CODEC), fps, (w, h))
        if not writer.isOpened():
            writer.release()
            return None

        for f in frames:
            writer.write(f)
        writer.release()
        self._last_save_time = now
        return filename
