"""
First-run setup wizard for Aiden's Halloween Tracker.

Run this once before main.py to configure your camera, candy math, and
(optionally) the public Render dashboard — it writes straight into
config.py so you don't have to hand-edit it.

    python setup.py
"""

import os
import re

CONFIG_PATH = "config.py"
LOCAL_SETTINGS_PATH = "local_settings.py"


def set_config_value(key, value_repr):
    with open(CONFIG_PATH, "r") as f:
        text = f.read()
    new_text, n = re.subn(rf"^{key}\s*=.*$", f"{key} = {value_repr}", text, count=1, flags=re.MULTILINE)
    if n == 0:
        raise ValueError(f"Could not find '{key}' in {CONFIG_PATH} — was it renamed?")
    with open(CONFIG_PATH, "w") as f:
        f.write(new_text)


def set_secret(key, value_repr):
    """Secrets go in local_settings.py, which is gitignored — never config.py."""
    if not os.path.exists(LOCAL_SETTINGS_PATH):
        example = LOCAL_SETTINGS_PATH + ".example"
        text = open(example).read() if os.path.exists(example) else ""
        with open(LOCAL_SETTINGS_PATH, "w") as f:
            f.write(text)

    with open(LOCAL_SETTINGS_PATH, "r") as f:
        text = f.read()

    new_text, n = re.subn(rf"^{key}\s*=.*$", f"{key} = {value_repr}", text, count=1, flags=re.MULTILINE)
    if n == 0:
        # Key doesn't exist yet (e.g. it was commented out) — append it.
        new_text = text.rstrip() + f"\n{key} = {value_repr}\n"
    with open(LOCAL_SETTINGS_PATH, "w") as f:
        f.write(new_text)


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else " (blank to skip)"
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else default


def ask_int(prompt, default=None, min_value=None, max_value=None):
    """Like ask(), but keeps re-prompting until the answer is a whole
    number (so e.g. typing '10 PM' can't end up written as literal code
    into config.py)."""
    while True:
        val = ask(prompt, default)
        if val is None:
            return None
        try:
            n = int(val)
        except ValueError:
            print(f"  '{val}' isn't a whole number — please enter digits only (e.g. 22, not '10 PM').")
            continue
        if min_value is not None and n < min_value:
            print(f"  Must be at least {min_value}.")
            continue
        if max_value is not None and n > max_value:
            print(f"  Must be at most {max_value}.")
            continue
        return n


def main():
    print("=== Aiden's Halloween Tracker — setup ===\n")

    print("Camera setup — how do you want to find your camera?")
    print("  1. Scan my network for it (recommended — picks it out automatically)")
    print("  2. I'll type the RTSP URL myself")
    choice = ask("Choose 1 or 2", "1")

    rtsp_url = None
    if choice.strip() == "2":
        while True:
            typed = ask("Camera RTSP URL (must start with rtsp://, e.g. rtsp://user:pass@ip:port/path)")
            if not typed:
                break
            if typed.startswith("rtsp://"):
                rtsp_url = typed
                break
            print(f"  '{typed}' doesn't look like a real RTSP URL (it should start with rtsp://) — try again, or leave it blank to cancel.")
    else:
        from network_scan import run_interactive_scan
        rtsp_url = run_interactive_scan()

    if rtsp_url:
        set_secret("RTSP_URL", repr(rtsp_url))
        print("  Saved RTSP_URL to local_settings.py (never committed to git).")
    else:
        print("  Skipped — your camera URL is unchanged.")

    print("\n-- Candy math (leave blank to skip this feature) --")
    candy = ask_int("How many pieces of candy do you have tonight?", min_value=0)
    if candy is not None:
        set_config_value("CANDY_TOTAL", candy)
        per_visitor = ask_int("Pieces of candy per trick-or-treater", "2", min_value=1)
        set_config_value("CANDY_PER_VISITOR", per_visitor)
        end_hour = ask_int("What hour (24h, e.g. 22 for 10pm) should trick-or-treating end?", "21", min_value=0, max_value=23)
        set_config_value("EVENT_END_HOUR", end_hour)
        print("  Saved candy settings.")

    try:
        from local_settings import RENDER_URL as existing_render_url
    except ImportError:
        existing_render_url = None

    if existing_render_url:
        print(f"\n-- Public Render dashboard already configured ({existing_render_url}) — skipping. --")
    else:
        print("\n-- Public Render dashboard (optional — needs render_app/ already deployed) --")
        render_url = ask("Render app URL")
        if render_url:
            secret = ask("Render shared secret (the TRACKER_SECRET value Render generated)")
            if secret:
                set_secret("RENDER_SECRET", repr(secret))
            set_secret("RENDER_URL", repr(render_url))
            print("  Saved Render settings to local_settings.py (never committed to git).")

    print("\nDone. Next steps:")
    print("  1. python pick_zone.py   (draw your detection zone)")
    print("  2. python main.py        (start tracking)")


if __name__ == "__main__":
    main()
