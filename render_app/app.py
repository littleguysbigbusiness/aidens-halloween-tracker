"""
Aiden's Halloween Tracker — public live-stats webpage.

Deployed to Render as its own small web service. Holds the latest stats
in plain memory (no database) — the local tracker POSTs updates to /update
and this page just reflects whatever it was told last. No camera footage,
no images, no biometric data — just numbers.
"""

import os
import time

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

SHARED_SECRET = os.environ.get("TRACKER_SECRET", "changeme")

state = {
    "count": 0,
    "last_visit_ago": None,
    "biggest_group": 0,
    "busiest_10min": 0,
    "session_duration": "-",
    "candy_remaining": None,
    "candy_warning": False,
    "updated_at": None,
}

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aiden's Halloween Tracker</title>
<style>
body { background:#15131a; color:#eee; font-family: system-ui, sans-serif; text-align:center; padding-top:30px; margin:0; }
h1 { color:#ff9800; font-size:22px; margin-bottom:0; }
.count { font-size:88px; font-weight:bold; color:#ff9800; line-height:1; margin-top:10px; }
.label { font-size:18px; color:#aaa; margin-bottom:20px; }
.stats { font-size:18px; margin:6px 0; }
.warn { color:#ff5252; font-weight:bold; }
.stale { color:#ff5252; font-size:14px; margin-top:20px; }
</style></head>
<body>
<h1>Aiden's Halloween Tracker</h1>
<div class="count">{{ count }}</div>
<div class="label">trick-or-treaters tonight</div>
<div class="stats">Last visit: {{ last_visit_ago or "waiting for first visitor..." }}</div>
<div class="stats">Biggest group at once: {{ biggest_group }}</div>
<div class="stats">Busiest 10-min stretch: {{ busiest_10min }}</div>
<div class="stats">Running: {{ session_duration }}</div>
{% if candy_remaining is not none %}
<div class="stats {{ 'warn' if candy_warning else '' }}">Candy left: ~{{ candy_remaining }} pieces</div>
{% if candy_warning %}<div class="stats warn">May run out!</div>{% endif %}
{% endif %}
{% if stale %}<div class="stale">No update from the tracker in a while — it may be offline.</div>{% endif %}
</body></html>"""


@app.route("/update", methods=["POST"])
def update():
    if request.headers.get("X-Tracker-Secret") != SHARED_SECRET:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True, silent=True) or {}
    state.update(data)
    state["updated_at"] = time.time()
    return jsonify({"ok": True})


@app.route("/")
def index():
    stale = state["updated_at"] is None or (time.time() - state["updated_at"] > 120)
    return render_template_string(PAGE, stale=stale, **state)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
