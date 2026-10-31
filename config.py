"""Configuration for Aiden's Halloween Tracker.

Secrets (camera URL/credentials, Render secret) live in local_settings.py,
which is gitignored and never committed — see local_settings.py.example.
"""

try:
    from local_settings import RTSP_URL
except ImportError:
    # Placeholder for a fresh clone with no local_settings.py yet.
    # Copy local_settings.py.example to local_settings.py and fill this in.
    RTSP_URL = "rtsp://username:password@192.168.1.50:554/your-camera-path"

# --- Detection ---
# YOLOv8 model file. "yolov8n.pt" (nano) is fastest and downloads automatically
# on first run. Only the "person" class is used.
MODEL_PATH = "yolov8n.pt"
DETECTION_CONFIDENCE = 0.45
PERSON_CLASS_ID = 0  # COCO class index for "person"

# --- Re-entry tracking (no biometric/face data is ever stored) ---
# Visitors are matched across brief absences using a coarse appearance
# signature (color histogram of clothing/overall appearance), not facial
# recognition. This is intentionally low-fidelity: it's good enough to avoid
# double-counting someone who steps off-frame and back, but it is NOT an
# identity system and makes no attempt to be.
REENTRY_WINDOW_SECONDS = 20 * 60  # how long a departed visitor is "remembered"
SIMILARITY_THRESHOLD = 0.82       # cosine similarity required to treat as same visitor
MAX_MISSING_SECONDS_BEFORE_INACTIVE = 3.0  # frames without a detection before a track is considered "departed"

# --- Logging (counts only; no images or embeddings are ever written to disk) ---
LOG_CSV_PATH = "tally_log.csv"

# --- Detection zone ---
# Only people whose feet (bottom-center of their box) fall inside this
# polygon are counted — e.g. draw it around your yard/walkway so people
# passing by on the sidewalk/street aren't tallied as trick-or-treaters.
# Points are (x, y) pixel coordinates in the PROCESS_WIDTH-scaled frame.
# Leave as None to disable (count anyone detected anywhere in frame).
# Run `python pick_zone.py` to click out the points on a live camera frame
# and get this value printed out ready to paste in.
DETECTION_ZONE = [(36, 439), (683, 309), (947, 255), (1272, 253), (1276, 705), (6, 714)]

# --- Automatic visit video ---
# A plain video clip (not facial recognition — no biometric data, just
# ordinary footage, like any doorbell camera records) is saved automatically
# around each confirmed visit: it starts ~CLIP_BUFFER_SECONDS before the
# visitor was actually detected (using the same rolling pre-roll buffer as
# the manual clip save below) and keeps recording forward until the total
# length hits AUTO_VIDEO_TOTAL_SECONDS. If another visit gets confirmed
# while a recording is already in progress, the recording is simply
# extended instead of starting a second overlapping file — so a cluster of
# trick-or-treaters all end up together in one video.
AUTO_VIDEO_DIR = "videos"
AUTO_VIDEO_TOTAL_SECONDS = 120

# --- Manual costume clip saving ---
# There is no reliable way for software to detect "this person is an adult",
# especially through costumes/masks, so this is intentionally a MANUAL,
# human-judgment action: press 's' in the preview window and the last
# CLIP_BUFFER_SECONDS of video is saved. Only save clips you've personally
# looked at and decided are appropriate to keep (e.g. skip if minors are in
# frame). Clips are saved locally only — nothing is uploaded automatically.
CLIP_BUFFER_SECONDS = 30
CLIPS_DIR = "clips"

# --- Arrival alert ---
# Plays a short beep when a visit is confirmed (see COUNT_DEBOUNCE_SECONDS
# below). Press 'm' in the preview window to mute/unmute at any time — this
# is a simple on/off toggle you control, not automatic "quiet hours" logic.
ALERT_ENABLED = True

# --- Count debounce ---
# A person must be continuously present in the zone for this many seconds
# before they're added to the tally (and before the arrival beep fires).
# This avoids false counts from a single flickery/misfired detection frame.
COUNT_DEBOUNCE_SECONDS = 1.5

# --- Performance ---
# Cameras streaming at 4K are needlessly slow to run detection on; frames are
# downscaled to this width (aspect ratio preserved) before detection/display.
PROCESS_WIDTH = 1280

# --- Sidebar stats settings ---
# Which stats show in the sidebar/dashboard when verbose mode is on (the
# "Stats: Full/Simple" button toggles verbose mode at runtime). In simple
# mode, only the running count is shown.
SHOW_STAT_BIGGEST_GROUP = True
SHOW_STAT_BUSIEST_WINDOW = True
SHOW_STAT_LAST_VISIT = True
SHOW_STAT_SESSION_DURATION = True
STATS_VERBOSE_DEFAULT = True

# --- Remote dashboard (optional) ---
# If you've deployed render_app/ to Render, set RENDER_URL to its address
# and RENDER_SECRET to the TRACKER_SECRET env var Render generated for it.
# The local tracker will push stats there every RENDER_PUSH_INTERVAL_SECONDS
# so the public page stays live. Leave RENDER_URL as None to skip this —
# the LAN-only dashboard above still works either way.
try:
    from local_settings import RENDER_URL
except ImportError:
    RENDER_URL = None
try:
    from local_settings import RENDER_SECRET
except ImportError:
    RENDER_SECRET = None
RENDER_PUSH_INTERVAL_SECONDS = 5

# --- Live dashboard ---
# A tiny local webpage showing the live tally, running stats, and recent
# visit videos — visit http://<this-PC's-LAN-IP>:DASHBOARD_PORT/ from your
# phone on the same wifi. No camera frames are streamed, just numbers.
DASHBOARD_PORT = 8787

# --- Candy math ---
# Set CANDY_TOTAL to how many pieces you're starting with tonight and
# CANDY_PER_VISITOR to how many you give each trick-or-treater. The tracker
# will estimate whether you're on pace to run out before EVENT_END_HOUR
# (24-hour local time, e.g. 21 = 9pm) based on tonight's visit rate so far.
CANDY_TOTAL = None  # e.g. 200 — leave as None to disable candy tracking
CANDY_PER_VISITOR = 2
EVENT_END_HOUR = 21

# --- Display ---
SHOW_PREVIEW_WINDOW = True
