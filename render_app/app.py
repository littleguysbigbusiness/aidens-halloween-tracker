"""
Aiden's Halloween Tracker — public live-stats webpage.

Deployed to Render as its own small web service. Holds the latest stats
in plain memory (no database) — the local tracker POSTs updates to /update
and this page just reflects whatever it was told last. No camera footage,
no images, no biometric data — just numbers.

IMPORTANT: this page is a single shared view. Everyone who has the link
sees the exact same live data — there's no per-visitor privacy boundary,
it's just one global display. The /admin panel below (protected by the
same TRACKER_SECRET) exists specifically so you can pause/hide that shared
view or reset it, since anyone with the URL can otherwise see it live.
"""

import os
import time

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

SHARED_SECRET = os.environ.get("TRACKER_SECRET", "changeme")

DEFAULT_STATE = {
    "count": 0,
    "last_visit_ago": None,
    "biggest_group": 0,
    "busiest_10min": 0,
    "session_duration": "-",
    "candy_remaining": None,
    "candy_warning": False,
    "updated_at": None,
}

state = dict(DEFAULT_STATE)
admin_paused = False

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
.paused { font-size:22px; color:#888; margin-top:40px; }
</style></head>
<body>
<h1>Aiden's Halloween Tracker</h1>
{% if paused %}
<div class="paused">Tracking is currently paused by the admin.</div>
{% else %}
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
{% endif %}
</body></html>"""

ADMIN_LOGIN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Admin</title>
<style>body{background:#15131a;color:#eee;font-family:system-ui,sans-serif;text-align:center;padding-top:60px;}
input{padding:8px;font-size:16px;} button{padding:8px 16px;font-size:16px;margin-left:8px;}
.error{color:#ff5252;margin-top:10px;}</style></head>
<body>
<h2>Admin login</h2>
<form method="post" action="/admin">
<input type="password" name="secret" placeholder="TRACKER_SECRET" autofocus>
<button type="submit">Log in</button>
</form>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
</body></html>"""

ADMIN_PANEL_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Admin</title>
<style>body{background:#15131a;color:#eee;font-family:system-ui,sans-serif;text-align:center;padding-top:40px;}
button{padding:10px 20px;font-size:16px;margin:8px;cursor:pointer;}
input{padding:8px;font-size:16px;width:120px;}
.status{font-size:18px;margin:20px 0;}
.danger{background:#ff5252;color:#fff;border:none;}
</style></head>
<body>
<h2>Aiden's Halloween Tracker — Admin</h2>
<div class="status">Public page is currently: <b>{{ "PAUSED" if paused else "LIVE" }}</b></div>
<div class="status">Current count: <b>{{ count }}</b></div>

<form method="post" action="/admin/toggle_pause" style="display:inline">
<input type="hidden" name="secret" value="{{ secret }}">
<button type="submit">{{ "Resume public page" if paused else "Pause public page" }}</button>
</form>

<form method="post" action="/admin/set_count" style="display:inline">
<input type="hidden" name="secret" value="{{ secret }}">
<input type="number" name="count" value="{{ count }}">
<button type="submit">Set count</button>
</form>

<form method="post" action="/admin/reset" style="display:inline">
<input type="hidden" name="secret" value="{{ secret }}">
<button type="submit" class="danger">Reset everything</button>
</form>

<p><a href="/" style="color:#ff9800;">View public page</a></p>
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
    return render_template_string(PAGE, stale=stale, paused=admin_paused, **state)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    secret = request.form.get("secret", "")
    if request.method == "POST" and secret == SHARED_SECRET:
        return render_template_string(ADMIN_PANEL_PAGE, paused=admin_paused, count=state["count"], secret=secret)
    if request.method == "POST":
        return render_template_string(ADMIN_LOGIN_PAGE, error="Wrong secret.")
    return render_template_string(ADMIN_LOGIN_PAGE, error=None)


@app.route("/admin/toggle_pause", methods=["POST"])
def admin_toggle_pause():
    global admin_paused
    if request.form.get("secret") != SHARED_SECRET:
        return "unauthorized", 401
    admin_paused = not admin_paused
    return render_template_string(ADMIN_PANEL_PAGE, paused=admin_paused, count=state["count"], secret=request.form.get("secret"))


@app.route("/admin/set_count", methods=["POST"])
def admin_set_count():
    if request.form.get("secret") != SHARED_SECRET:
        return "unauthorized", 401
    try:
        state["count"] = int(request.form.get("count", state["count"]))
    except ValueError:
        pass
    return render_template_string(ADMIN_PANEL_PAGE, paused=admin_paused, count=state["count"], secret=request.form.get("secret"))


@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    global state, admin_paused
    if request.form.get("secret") != SHARED_SECRET:
        return "unauthorized", 401
    state = dict(DEFAULT_STATE)
    admin_paused = False
    return render_template_string(ADMIN_PANEL_PAGE, paused=admin_paused, count=state["count"], secret=request.form.get("secret"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
