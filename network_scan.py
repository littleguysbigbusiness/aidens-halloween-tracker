"""Scans your local network for cameras (anything with RTSP's port 554
open), lets you pick one, asks for its username/password, then tries a
handful of common camera URL path patterns until one actually connects.

This only touches your own LAN — it never contacts the internet.
"""

import socket
from concurrent.futures import ThreadPoolExecutor

import cv2

RTSP_PORT = 554
SCAN_TIMEOUT = 0.3
MAX_WORKERS = 64

# (brand/style, path template) — tried in order against whichever IP you pick.
COMMON_RTSP_PATHS = [
    ("Reolink-style", "/h264Preview_01_main"),
    ("Hikvision-style", "/Streaming/Channels/101"),
    ("Dahua-style", "/cam/realmonitor?channel=1&subtype=0"),
    ("Generic", "/live/ch0"),
    ("Generic", "/video1"),
    ("Generic", "/stream1"),
    ("ONVIF-ish", "/onvif1"),
]


def get_local_subnet_prefix():
    """Best-effort guess at 'this machine's /24, e.g. 192.168.0.'"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ".".join(ip.split(".")[:3]) + "."


def _port_open(ip, port, timeout):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def scan_for_cameras(prefix=None, port=RTSP_PORT, timeout=SCAN_TIMEOUT):
    prefix = prefix or get_local_subnet_prefix()
    candidates = [f"{prefix}{i}" for i in range(1, 255)]
    found = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = pool.map(lambda ip: (ip, _port_open(ip, port, timeout)), candidates)
        for ip, ok in results:
            if ok:
                found.append(ip)
    return sorted(found, key=lambda ip: int(ip.split(".")[-1]))


def try_rtsp_url(url, timeout_ms=4000):
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)
    ok = False
    try:
        if cap.isOpened():
            ok, _ = cap.read()
    finally:
        cap.release()
    return ok


def run_interactive_scan():
    """CLI flow: scan -> pick IP -> enter credentials -> auto-try common
    paths -> return a working rtsp:// URL, or None if nothing worked."""
    prefix = get_local_subnet_prefix()
    print(f"\nScanning {prefix}1-254 for cameras (port {RTSP_PORT} open)... this takes a few seconds.")
    found = scan_for_cameras(prefix)

    if not found:
        print("No cameras found on your network automatically.")
        return None

    print("\nFound these devices with an RTSP port open:")
    for i, ip in enumerate(found, 1):
        print(f"  {i}. {ip}")

    choice = input(f"Which one is your camera? (1-{len(found)}, or blank to cancel): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(found)):
        print("Cancelled.")
        return None
    ip = found[int(choice) - 1]

    username = input("Camera username [admin]: ").strip() or "admin"
    password = input("Camera password: ").strip()

    print(f"\nTrying common URL patterns against {ip}...")
    for brand, path in COMMON_RTSP_PATHS:
        url = f"rtsp://{username}:{password}@{ip}:{RTSP_PORT}{path}"
        print(f"  Trying {brand} ({path})...", end=" ")
        if try_rtsp_url(url):
            print("connected!")
            return url
        print("no.")

    print("None of the common patterns worked.")
    manual_path = input("Enter the exact path for your camera (e.g. /your/path), or blank to give up: ").strip()
    if manual_path:
        url = f"rtsp://{username}:{password}@{ip}:{RTSP_PORT}{manual_path}"
        if try_rtsp_url(url):
            print("Connected!")
            return url
        print("Still couldn't connect with that path either.")

    return None


if __name__ == "__main__":
    result = run_interactive_scan()
    if result:
        print(f"\nWorking RTSP URL: {result}")
    else:
        print("\nNo working camera URL found — enter it manually in setup.py instead.")
