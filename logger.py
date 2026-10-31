"""Append-only CSV logging. Only timestamps and counts are ever written —
no images, no embeddings, no identity data."""

import csv
import os
from datetime import datetime

import config


def init_log():
    if not os.path.exists(config.LOG_CSV_PATH):
        with open(config.LOG_CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "event", "total_unique_visits"])


def log_event(event, total_unique_visits):
    with open(config.LOG_CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now().isoformat(timespec="seconds"), event, total_unique_visits])


def get_last_count():
    """Reads the tally log and returns the most recent total_unique_visits,
    so a restart (e.g. to pick up a code update) resumes the night's count
    instead of starting over from zero."""
    if not os.path.exists(config.LOG_CSV_PATH):
        return 0
    last_count = 0
    with open(config.LOG_CSV_PATH, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if len(row) >= 3 and row[2].isdigit():
                last_count = int(row[2])
    return last_count
