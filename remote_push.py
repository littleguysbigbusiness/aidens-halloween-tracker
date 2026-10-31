"""Pushes the same stats the LAN dashboard shows to a deployed Render app
(render_app/), so a public-ish URL stays live too. No-op unless
config.RENDER_URL is set. Fire-and-forget on a background thread so a slow
or unreachable server never blocks the main loop/camera processing."""

import json
import threading
import time
import urllib.request

import config

_last_push = 0.0


def push_async(state):
    global _last_push
    if not config.RENDER_URL:
        return
    now = time.time()
    if now - _last_push < config.RENDER_PUSH_INTERVAL_SECONDS:
        return
    _last_push = now
    threading.Thread(target=_push, args=(dict(state),), daemon=True).start()


def _push(state):
    try:
        data = json.dumps(state).encode("utf-8")
        req = urllib.request.Request(
            config.RENDER_URL.rstrip("/") + "/update",
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Tracker-Secret": config.RENDER_SECRET or "",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Render push failed (will keep retrying): {e}")
