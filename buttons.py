"""On-screen clickable buttons drawn in a sidebar, as an alternative to keyboard shortcuts.

Also supports forwarding clicks on the video area itself (used for in-window
zone editing) via on_video_click.
"""

import cv2

SIDEBAR_WIDTH = 160
BUTTON_HEIGHT = 60
BUTTON_MARGIN = 12


class ButtonPanel:
    def __init__(self, buttons, frame_width):
        self.buttons = buttons
        self.on_video_click = None
        self._frame_width = frame_width
        self._pending = []
        self._rects = self._layout()

    def set_buttons(self, buttons):
        self.buttons = buttons
        self._rects = self._layout()

    def _layout(self):
        rects = []
        y = BUTTON_MARGIN
        for label, action in self.buttons:
            rects.append((label, action, (BUTTON_MARGIN, y, SIDEBAR_WIDTH - BUTTON_MARGIN, y + BUTTON_HEIGHT)))
            y += BUTTON_HEIGHT + BUTTON_MARGIN
        return rects

    def attach(self, window_name):
        cv2.setMouseCallback(window_name, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, userdata):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if x < self._frame_width:
            # Click landed on the video itself, not the sidebar.
            if self.on_video_click:
                self.on_video_click(x, y)
            return

        # Click landed in the sidebar — translate to sidebar-local coordinates.
        local_x = x - self._frame_width
        for label, action, (x1, y1, x2, y2) in self._rects:
            if x1 <= local_x <= x2 and y1 <= y <= y2:
                self._pending.append(action)
                return

    def poll_action(self):
        if self._pending:
            return self._pending.pop(0)
        return None

    def render(self, frame, stats_lines=None):
        """Returns a new frame with the sidebar (buttons + optional live
        stats block beneath them) drawn on the right edge."""
        h, w = frame.shape[:2]
        self._frame_width = w
        canvas = cv2.copyMakeBorder(frame, 0, 0, 0, SIDEBAR_WIDTH, cv2.BORDER_CONSTANT, value=(40, 40, 40))

        last_bottom = BUTTON_MARGIN
        for label, _, (x1, y1, x2, y2) in self._rects:
            bx1, by1, bx2, by2 = x1 + w, y1, x2 + w, y2
            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (90, 90, 90), -1)
            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (200, 200, 200), 1)
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            tx = bx1 + max(4, ((bx2 - bx1) - text_size[0]) // 2)
            ty = by1 + ((by2 - by1) + text_size[1]) // 2
            cv2.putText(canvas, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            last_bottom = y2

        if stats_lines:
            cv2.line(canvas, (w + BUTTON_MARGIN, last_bottom + 10), (w + SIDEBAR_WIDTH - BUTTON_MARGIN, last_bottom + 10),
                      (90, 90, 90), 1)
            ty = last_bottom + 32
            for line, color in stats_lines:
                cv2.putText(canvas, line, (w + BUTTON_MARGIN, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
                ty += 20

        return canvas
