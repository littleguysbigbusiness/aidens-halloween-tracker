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


def main():
    print("=== Aiden's Halloween Tracker — setup ===\n")

    print("Tip: use 'Scan network for a camera' below instead of typing this by hand.")
    rtsp = ask("Camera RTSP URL (rtsp://user:pass@ip:port/path)")
    if rtsp:
        set_secret("RTSP_URL", repr(rtsp))
        print("  Saved RTSP_URL to local_settings.py (never committed to git).")
    else:
        scan = ask("Scan your network for a camera instead? (y/n)", "y")
        if scan.lower().startswith("y"):
            from network_scan import run_interactive_scan
            found_url = run_interactive_scan()
            if found_url:
                set_secret("RTSP_URL", repr(found_url))
                print("  Saved RTSP_URL to local_settings.py (never committed to git).")

    print("\n-- Candy math (leave blank to skip this feature) --")
    candy = ask("How many pieces of candy do you have tonight?")
    if candy:
        set_config_value("CANDY_TOTAL", candy)
        per_visitor = ask("Pieces of candy per trick-or-treater", "2")
        set_config_value("CANDY_PER_VISITOR", per_visitor)
        end_hour = ask("What hour (24h, e.g. 21 for 9pm) should trick-or-treating end?", "21")
        set_config_value("EVENT_END_HOUR", end_hour)
        print("  Saved candy settings.")

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
