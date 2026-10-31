"""Tiny local dashboard webpage — view the live tally and recent visit
videos from your phone on the same wifi, without touching the preview
window. No camera frames are streamed here, just numbers and a file list;
auto-refreshes every few seconds.
"""

import glob
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config

_state = {
    "count": 0,
    "last_visit_ago": None,
    "biggest_group": 0,
    "busiest_10min": 0,
    "session_duration": "-",
    "candy_remaining": None,
    "candy_warning": False,
}


def update_state(**kwargs):
    _state.update(kwargs)


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def _render_page():
    last_visit = _state.get("last_visit_ago")
    last_visit_text = f"{last_visit}" if last_visit else "waiting for first visitor..."

    videos_dir = config.AUTO_VIDEO_DIR
    videos = []
    if os.path.isdir(videos_dir):
        videos = sorted(glob.glob(os.path.join(videos_dir, "*.avi")), key=os.path.getmtime, reverse=True)[:10]
    video_items = "".join(f"<li>{os.path.basename(v)}</li>" for v in videos) or "<li>none yet</li>"

    candy_html = ""
    if _state.get("candy_remaining") is not None:
        warn_class = "warn" if _state.get("candy_warning") else ""
        candy_html = f'<div class="stats {warn_class}">Candy left: ~{_state["candy_remaining"]} pieces</div>'

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Halloween Tally</title>
<style>
body {{ background:#15131a; color:#eee; font-family: system-ui, sans-serif; text-align:center; padding-top:30px; margin:0; }}
.count {{ font-size:88px; font-weight:bold; color:#ff9800; line-height:1; }}
.label {{ font-size:18px; color:#aaa; margin-bottom:20px; }}
.stats {{ font-size:18px; margin:6px 0; }}
.warn {{ color:#ff5252; font-weight:bold; }}
ul {{ text-align:left; display:inline-block; font-size:14px; color:#ccc; }}
h3 {{ color:#ff9800; margin-top:30px; }}
</style></head>
<body>
<div class="count">{_state.get("count", 0)}</div>
<div class="label">trick-or-treaters tonight</div>
<div class="stats">Last visit: {last_visit_text}</div>
<div class="stats">Biggest group at once: {_state.get("biggest_group", 0)}</div>
<div class="stats">Busiest 10-min stretch: {_state.get("busiest_10min", 0)}</div>
<div class="stats">Running: {_state.get("session_duration", "-")}</div>
{candy_html}
<h3>Recent visit videos</h3>
<ul>{video_items}</ul>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the console quiet

    def do_GET(self):
        html = _render_page()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def start_dashboard(port=None):
    port = port or config.DASHBOARD_PORT
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port
