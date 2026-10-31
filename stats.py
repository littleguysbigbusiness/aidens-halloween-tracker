"""Running night stats for the sidebar/dashboard: biggest group at once,
busiest 10-minute stretch, time since the last visitor, session duration."""

import time

BUSIEST_WINDOW_SECONDS = 10 * 60


class NightStats:
    def __init__(self):
        self.start_time = time.time()
        self.last_visit_time = None
        self.max_concurrent = 0
        self._visit_timestamps = []

    def record_visit(self):
        now = time.time()
        self.last_visit_time = now
        self._visit_timestamps.append(now)

    def update_concurrent(self, current_count):
        self.max_concurrent = max(self.max_concurrent, current_count)

    def busiest_window_count(self, window_seconds=BUSIEST_WINDOW_SECONDS):
        """Most visits that landed within any window_seconds-wide stretch tonight."""
        times = self._visit_timestamps
        if not times:
            return 0
        best = 0
        j = 0
        for i in range(len(times)):
            while times[i] - times[j] > window_seconds:
                j += 1
            best = max(best, i - j + 1)
        return best

    def seconds_since_last_visit(self):
        if self.last_visit_time is None:
            return None
        return time.time() - self.last_visit_time

    def session_duration_seconds(self):
        return time.time() - self.start_time

    def visits_per_minute(self, total_visits):
        elapsed_minutes = self.session_duration_seconds() / 60.0
        if elapsed_minutes < 0.1:
            return 0.0
        return total_visits / elapsed_minutes


def format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
