"""Background RTSP frame grabber.

cv2.VideoCapture.read() can block for many seconds when the network stream
stalls or corrupts a packet (common on wifi cameras). If that call happens
on the same thread that's servicing the preview window, the window appears
frozen ("Not Responding") for the whole stall. Running the read loop on its
own thread keeps the GUI thread free to keep pumping window events no
matter what the camera is doing, and lets us reconnect automatically.
"""

import os
import threading
import time

import cv2

# Prefer TCP for RTSP — more resilient to the packet loss that causes the
# "error while decoding MB ..." spam and stream stalls over UDP/wifi.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


class FrameGrabber:
    def __init__(self, url, reconnect_delay=2.0):
        self.url = url
        self.reconnect_delay = reconnect_delay
        self._lock = threading.Lock()
        self._frame = None
        self._last_update = 0.0
        self._running = False
        self._cap = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._running = True
        self._thread.start()
        return self

    def _open(self):
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture(self.url)
        # Not all OpenCV/ffmpeg builds honor these, but when they do, a
        # stalled read fails fast instead of hanging for ~30s.
        self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        self._cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

    def _run(self):
        self._open()
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                time.sleep(self.reconnect_delay)
                self._open()
                continue

            ok, frame = self._cap.read()
            if ok:
                with self._lock:
                    self._frame = frame
                    self._last_update = time.time()
            else:
                time.sleep(self.reconnect_delay)
                self._open()

    def get_frame(self):
        """Returns (frame_or_None, seconds_since_last_good_frame)."""
        with self._lock:
            if self._frame is None:
                return None, float("inf")
            return self._frame.copy(), time.time() - self._last_update

    def stop(self):
        self._running = False
        if self._cap is not None:
            self._cap.release()
