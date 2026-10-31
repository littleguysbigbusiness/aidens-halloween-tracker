"""
Halloween trick-or-treater tally tracker.

Reads an RTSP camera stream, detects people, and tallies distinct visits
without storing any biometric or face data. See config.py for all tunables
and tracker.py for how brief re-entries are handled.

Controls are on-screen buttons in the sidebar on the right of the preview
window: Save Clip, Mute/Unmute, +1, -1, Edit Zone, Quit. (q also quits via
keyboard.) "Edit Zone" lets you click out a new detection zone directly in
the window instead of running a separate script.

A plain video (not facial recognition — ordinary footage, like a doorbell
camera) is also recorded automatically around each confirmed visit, see
auto_recorder.py and config.AUTO_VIDEO_* for details.
"""

import sys
import time
from datetime import datetime

import cv2
import numpy as np
from ultralytics import YOLO

import config
import dashboard
import logger
import remote_push
from alert import beep
from auto_recorder import AutoRecorder
from buttons import ButtonPanel
from clip_buffer import ClipBuffer
from stats import NightStats, format_duration
from stream import FrameGrabber
from tracker import ReentryTracker
from zone import point_in_zone, foot_point, draw_zone, save_zone_to_config

STALE_FRAME_SECONDS = 5.0  # show a "reconnecting" badge if no fresh frame for this long

WINDOW_NAME = "Aiden's Halloween Tracker"

NORMAL_BUTTONS = [
    ("Save Clip", "save_clip"),
    ("Mute", "toggle_mute"),
    ("+1", "increment"),
    ("-1", "decrement"),
    ("Edit Zone", "edit_zone"),
    ("Stats: Full", "toggle_stats_verbose"),
    ("Public: Off", "toggle_public_sharing"),
    ("Quit", "quit"),
]

EDIT_BUTTONS = [
    ("Confirm Zone", "confirm_zone"),
    ("Clear Points", "clear_points"),
    ("Cancel", "cancel_edit"),
]


def main():
    if not config.RTSP_URL.startswith("rtsp://"):
        print(f"ERROR: RTSP_URL doesn't look like a real camera URL: {config.RTSP_URL!r}")
        print("Run `python setup.py` to fix it (or edit local_settings.py directly).")
        sys.exit(1)

    logger.init_log()
    model = YOLO(config.MODEL_PATH)
    resumed_count = logger.get_last_count()
    tracker = ReentryTracker(initial_count=resumed_count)
    if resumed_count:
        print(f"Resuming tonight's tally from the log: {resumed_count}")
    clip_buffer = ClipBuffer()
    auto_recorder = AutoRecorder()
    stats = NightStats()
    alert_muted = not config.ALERT_ENABLED
    stats_verbose = config.STATS_VERBOSE_DEFAULT
    public_sharing_enabled = config.PUBLIC_SHARING_ENABLED

    _, dashboard_port = dashboard.start_dashboard()
    print(f"Dashboard: http://{dashboard.get_lan_ip()}:{dashboard_port}/  (same wifi, from your phone)")

    grabber = FrameGrabber(config.RTSP_URL).start()
    print("Connecting to camera...")
    for _ in range(100):  # wait up to ~10s for the first frame
        frame, age = grabber.get_frame()
        if frame is not None:
            break
        time.sleep(0.1)
    else:
        print(f"ERROR: could not get a frame from RTSP stream: {config.RTSP_URL}")
        sys.exit(1)

    panel = None
    editing_zone = False
    zone_points = []
    toast_text = ""
    toast_until = 0.0
    TOAST_SECONDS = 2.5

    if config.SHOW_PREVIEW_WINDOW:
        cv2.namedWindow(WINDOW_NAME)

    print("Tracker running. Use the on-screen buttons in the sidebar (or press q to quit).")

    try:
        while True:
            frame, age = grabber.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            stream_stale = age > STALE_FRAME_SECONDS

            h, w = frame.shape[:2]
            if w > config.PROCESS_WIDTH:
                scale = config.PROCESS_WIDTH / w
                frame = cv2.resize(frame, (config.PROCESS_WIDTH, int(h * scale)))

            clip_buffer.add_frame(frame)
            finished_video_path = auto_recorder.add_frame(frame)
            if finished_video_path:
                print(f"Visit video saved: {finished_video_path}  (review before sharing!)")
                logger.log_event("visit_video_saved", tracker.total_unique_visits)
                toast_text = f"Visit video saved: {finished_video_path}"
                toast_until = time.time() + TOAST_SECONDS

            if editing_zone:
                # Detection is paused while you redraw the zone, to keep
                # things simple and responsive to clicks.
                for i, p in enumerate(zone_points):
                    cv2.circle(frame, p, 5, (0, 0, 255), -1)
                    cv2.putText(frame, str(i + 1), (p[0] + 6, p[1] - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                if len(zone_points) > 1:
                    polygon = np.array(zone_points, dtype=np.int32)
                    cv2.polylines(frame, [polygon], isClosed=True, color=(255, 255, 0), thickness=2)
                cv2.putText(frame, "Click corners of your zone, then Confirm Zone",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            else:
                results = model(frame, verbose=False)[0]
                boxes = []
                for det in results.boxes:
                    cls_id = int(det.cls[0])
                    conf = float(det.conf[0])
                    if cls_id == config.PERSON_CLASS_ID and conf >= config.DETECTION_CONFIDENCE:
                        box = tuple(map(int, det.xyxy[0]))
                        if point_in_zone(foot_point(box), config.DETECTION_ZONE):
                            boxes.append(box)

                tracked = tracker.update(frame, boxes)

                for vid, (x1, y1, x2, y2), just_confirmed, confirmed in tracked:
                    color = (0, 200, 0) if confirmed else (0, 140, 255)  # orange = pending, green = confirmed
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"visit#{vid}" if confirmed else f"visit#{vid} (pending)"
                    cv2.putText(frame, label, (x1, max(0, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    if just_confirmed:
                        logger.log_event("new_visit", tracker.total_unique_visits)
                        stats.record_visit()
                        if not alert_muted:
                            beep()
                        auto_recorder.trigger(clip_buffer)

                stats.update_concurrent(tracker.active_confirmed_count())
                draw_zone(frame, config.DETECTION_ZONE)

                # Status bar across the bottom of the frame.
                bar_h = 70
                fh, fw = frame.shape[:2]
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, fh - bar_h), (fw, fh), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

                cv2.putText(frame, f"Trick-or-treaters tonight: {tracker.total_unique_visits}",
                            (10, fh - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                cv2.putText(frame, f"Alert: {'MUTED' if alert_muted else 'on'}",
                            (10, fh - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            if stream_stale:
                cv2.putText(frame, f"Camera feed stalled, reconnecting... ({age:.0f}s)",
                            (10, frame.shape[0] - 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if time.time() < toast_until:
                text_size = cv2.getTextSize(toast_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                tx = max(10, (frame.shape[1] - text_size[0]) // 2)
                ty = 50
                cv2.rectangle(frame, (tx - 15, ty - text_size[1] - 15), (tx + text_size[0] + 15, ty + 15),
                              (0, 140, 0), -1)
                cv2.putText(frame, toast_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # --- Live stats (sidebar + dashboard) ---
            last_visit_ago = stats.seconds_since_last_visit()
            busiest = stats.busiest_window_count()
            stats_lines = [(f"Count: {tracker.total_unique_visits}", (255, 255, 255))]

            if stats_verbose:
                if config.SHOW_STAT_BIGGEST_GROUP:
                    stats_lines.append((f"Biggest group: {stats.max_concurrent}", (200, 200, 200)))
                if config.SHOW_STAT_BUSIEST_WINDOW:
                    stats_lines.append((f"Busiest 10min: {busiest}", (200, 200, 200)))
                if config.SHOW_STAT_LAST_VISIT:
                    stats_lines.append(
                        (f"Last visit: {format_duration(last_visit_ago)} ago" if last_visit_ago else "Last visit: -",
                         (200, 200, 200))
                    )
                if config.SHOW_STAT_SESSION_DURATION:
                    stats_lines.append((f"Running: {format_duration(stats.session_duration_seconds())}", (200, 200, 200)))

            candy_remaining = None
            candy_warning = False
            if stats_verbose and config.CANDY_TOTAL is not None:
                candy_given = tracker.total_unique_visits * config.CANDY_PER_VISITOR
                candy_remaining = max(0, config.CANDY_TOTAL - candy_given)
                rate = stats.visits_per_minute(tracker.total_unique_visits)
                now_dt = datetime.now()
                end_dt = now_dt.replace(hour=config.EVENT_END_HOUR, minute=0, second=0, microsecond=0)
                minutes_left = max(0.0, (end_dt - now_dt).total_seconds() / 60.0)
                projected_visitors = rate * minutes_left
                projected_candy_needed = projected_visitors * config.CANDY_PER_VISITOR
                candy_warning = projected_candy_needed > candy_remaining
                candy_color = (0, 0, 255) if candy_warning else (200, 200, 200)
                stats_lines.append((f"Candy left: ~{candy_remaining}", candy_color))
                if candy_warning:
                    stats_lines.append(("May run out!", (0, 0, 255)))

            live_state = {
                "count": tracker.total_unique_visits,
                "last_visit_ago": (f"{format_duration(last_visit_ago)} ago" if last_visit_ago else None),
                "biggest_group": stats.max_concurrent,
                "busiest_10min": busiest,
                "session_duration": format_duration(stats.session_duration_seconds()),
                "candy_remaining": candy_remaining,
                "candy_warning": candy_warning,
            }
            dashboard.update_state(**live_state)
            if public_sharing_enabled:
                remote_push.push_async(live_state)

            if config.SHOW_PREVIEW_WINDOW:
                if panel is None:
                    panel = ButtonPanel(list(NORMAL_BUTTONS), frame_width=frame.shape[1])
                    panel.attach(WINDOW_NAME)

                display_frame = panel.render(frame, stats_lines=stats_lines)
                cv2.imshow(WINDOW_NAME, display_frame)
                key = cv2.waitKey(1) & 0xFF

                action = panel.poll_action()
                if key == ord("q"):
                    action = "quit"

                if action == "quit":
                    break

                elif action == "save_clip":
                    path = clip_buffer.save_clip()
                    if path:
                        print(f"Saved clip: {path}  (review before sharing!)")
                        logger.log_event("clip_saved", tracker.total_unique_visits)
                        toast_text = f"Clip saved: {path}"
                        toast_until = time.time() + TOAST_SECONDS
                    else:
                        toast_text = "Clip not saved (just saved one recently, try again shortly)"
                        toast_until = time.time() + TOAST_SECONDS

                elif action == "toggle_mute":
                    alert_muted = not alert_muted
                    updated = list(panel.buttons)
                    updated[1] = ("Unmute" if alert_muted else "Mute", "toggle_mute")
                    panel.set_buttons(updated)
                    print(f"Alert {'muted' if alert_muted else 'unmuted'}.")
                    toast_text = "Alert muted" if alert_muted else "Alert unmuted"
                    toast_until = time.time() + TOAST_SECONDS

                elif action == "toggle_stats_verbose":
                    stats_verbose = not stats_verbose
                    updated = [
                        (("Stats: Full" if stats_verbose else "Stats: Simple"), "toggle_stats_verbose")
                        if a == "toggle_stats_verbose" else (lbl, a)
                        for lbl, a in panel.buttons
                    ]
                    panel.set_buttons(updated)
                    toast_text = "Stats: Full" if stats_verbose else "Stats: Simple"
                    toast_until = time.time() + TOAST_SECONDS

                elif action == "toggle_public_sharing":
                    public_sharing_enabled = not public_sharing_enabled
                    updated = [
                        (("Public: On" if public_sharing_enabled else "Public: Off"), "toggle_public_sharing")
                        if a == "toggle_public_sharing" else (lbl, a)
                        for lbl, a in panel.buttons
                    ]
                    panel.set_buttons(updated)
                    if public_sharing_enabled and not config.RENDER_URL:
                        toast_text = "Public ON, but no Render URL configured (run setup.py)"
                    else:
                        toast_text = "Public sharing ON" if public_sharing_enabled else "Public sharing OFF"
                    toast_until = time.time() + TOAST_SECONDS
                    print(f"Public sharing {'enabled' if public_sharing_enabled else 'disabled'}.")

                elif action == "increment":
                    tracker.manual_adjust(1)
                    logger.log_event("manual_increment", tracker.total_unique_visits)
                    toast_text = f"Tally +1 -> {tracker.total_unique_visits}"
                    toast_until = time.time() + TOAST_SECONDS

                elif action == "decrement":
                    tracker.manual_adjust(-1)
                    logger.log_event("manual_decrement", tracker.total_unique_visits)
                    toast_text = f"Tally -1 -> {tracker.total_unique_visits}"
                    toast_until = time.time() + TOAST_SECONDS

                elif action == "edit_zone":
                    editing_zone = True
                    zone_points = []
                    panel.set_buttons(list(EDIT_BUTTONS))
                    panel.on_video_click = lambda x, y: zone_points.append((x, y))

                elif action == "clear_points":
                    zone_points.clear()

                elif action == "cancel_edit":
                    editing_zone = False
                    panel.on_video_click = None
                    panel.set_buttons(list(NORMAL_BUTTONS))

                elif action == "confirm_zone":
                    if len(zone_points) >= 3:
                        config.DETECTION_ZONE = list(zone_points)
                        save_zone_to_config(config.DETECTION_ZONE)
                        print(f"Zone updated and saved to config.py: {config.DETECTION_ZONE}")
                        editing_zone = False
                        panel.on_video_click = None
                        panel.set_buttons(list(NORMAL_BUTTONS))
                        toast_text = "Zone saved"
                        toast_until = time.time() + TOAST_SECONDS
                    else:
                        print("Need at least 3 points before confirming the zone.")
                        toast_text = "Need at least 3 points"
                        toast_until = time.time() + TOAST_SECONDS

    finally:
        grabber.stop()
        cv2.destroyAllWindows()
        logger.log_event("session_end", tracker.total_unique_visits)
        print(f"Final tally: {tracker.total_unique_visits} unique visits.")
        print(f"Biggest group at once: {stats.max_concurrent}")
        print(f"Busiest 10-min stretch: {stats.busiest_window_count()}")
        print(f"Session ran: {format_duration(stats.session_duration_seconds())}")


if __name__ == "__main__":
    main()
