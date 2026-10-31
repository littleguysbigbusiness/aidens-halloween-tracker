"""
Graphical first-run setup for Aiden's Halloween Tracker — no terminal typing
required. Scans the network for your camera, lets you fill in candy math,
and saves everything, just like setup.py but as a window instead of a
console wizard.

    python setup_gui.py
"""

import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import config
from setup import set_config_value, set_secret
from network_scan import get_local_subnet_prefix, scan_for_cameras, try_rtsp_url, COMMON_RTSP_PATHS, RTSP_PORT

try:
    from local_settings import RENDER_URL as EXISTING_RENDER_URL
except ImportError:
    EXISTING_RENDER_URL = None


class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aiden's Halloween Tracker — Setup")
        self.geometry("520x620")
        self.resizable(False, False)

        self.found_ips = []
        self.working_rtsp_url = None

        self._build_camera_section()
        self._build_candy_section()
        self._build_render_section()
        self._build_footer()

    # --- Camera ---
    def _build_camera_section(self):
        frame = ttk.LabelFrame(self, text="1. Camera", padding=10)
        frame.pack(fill="x", padx=12, pady=8)

        ttk.Button(frame, text="Scan my network for cameras", command=self._start_scan).pack(anchor="w")
        self.scan_status = ttk.Label(frame, text="Not scanned yet.")
        self.scan_status.pack(anchor="w", pady=(4, 8))

        self.camera_listbox = tk.Listbox(frame, height=4)
        self.camera_listbox.pack(fill="x")

        cred_frame = ttk.Frame(frame)
        cred_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(cred_frame, text="Username:").grid(row=0, column=0, sticky="w")
        self.username_var = tk.StringVar(value="admin")
        ttk.Entry(cred_frame, textvariable=self.username_var, width=20).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(cred_frame, text="Password:").grid(row=1, column=0, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.password_var, show="*", width=20).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(frame, text="Connect using selected camera", command=self._start_connect).pack(anchor="w", pady=(8, 4))

        ttk.Label(frame, text="— or type the full RTSP URL yourself —", foreground="#666").pack(anchor="w", pady=(8, 2))
        self.manual_url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.manual_url_var, width=60).pack(fill="x")
        ttk.Button(frame, text="Test this URL", command=self._start_test_manual).pack(anchor="w", pady=(4, 0))

        self.camera_result = ttk.Label(frame, text="", foreground="#0a7a0a")
        self.camera_result.pack(anchor="w", pady=(8, 0))

    def _start_scan(self):
        self.scan_status.config(text="Scanning your network (a few seconds)...")
        self.camera_listbox.delete(0, tk.END)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        prefix = get_local_subnet_prefix()
        found = scan_for_cameras(prefix)
        self.found_ips = found
        self.after(0, self._scan_done, prefix, found)

    def _scan_done(self, prefix, found):
        if not found:
            self.scan_status.config(text=f"No cameras found on {prefix}1-254. Try the manual URL below.")
            return
        self.scan_status.config(text=f"Found {len(found)} device(s) with RTSP open:")
        for ip in found:
            self.camera_listbox.insert(tk.END, ip)
        self.camera_listbox.select_set(0)

    def _start_connect(self):
        selection = self.camera_listbox.curselection()
        if not selection:
            messagebox.showwarning("No camera selected", "Scan first, then pick a camera from the list.")
            return
        ip = self.camera_listbox.get(selection[0])
        username = self.username_var.get().strip() or "admin"
        password = self.password_var.get()
        self.camera_result.config(text=f"Trying common URL patterns against {ip}...", foreground="#666")
        threading.Thread(target=self._connect_worker, args=(ip, username, password), daemon=True).start()

    def _connect_worker(self, ip, username, password):
        for brand, path in COMMON_RTSP_PATHS:
            url = f"rtsp://{username}:{password}@{ip}:{RTSP_PORT}{path}"
            if try_rtsp_url(url):
                self.after(0, self._connect_done, url)
                return
        self.after(0, self._connect_done, None)

    def _connect_done(self, url):
        if url:
            self.working_rtsp_url = url
            self.camera_result.config(text="Connected! Camera URL saved for when you click Save below.", foreground="#0a7a0a")
        else:
            self.camera_result.config(
                text="Couldn't connect with common patterns — try the manual URL field above.",
                foreground="#b00",
            )

    def _start_test_manual(self):
        url = self.manual_url_var.get().strip()
        if not url.startswith("rtsp://"):
            messagebox.showwarning("Not a valid URL", "The URL must start with rtsp://")
            return
        self.camera_result.config(text="Testing connection...", foreground="#666")
        threading.Thread(target=self._test_manual_worker, args=(url,), daemon=True).start()

    def _test_manual_worker(self, url):
        ok = try_rtsp_url(url)
        self.after(0, self._test_manual_done, url, ok)

    def _test_manual_done(self, url, ok):
        if ok:
            self.working_rtsp_url = url
            self.camera_result.config(text="Connected! Camera URL saved for when you click Save below.", foreground="#0a7a0a")
        else:
            self.camera_result.config(text="Couldn't connect with that URL.", foreground="#b00")

    # --- Candy math ---
    def _build_candy_section(self):
        frame = ttk.LabelFrame(self, text="2. Candy math (optional)", padding=10)
        frame.pack(fill="x", padx=12, pady=8)

        ttk.Label(frame, text="Total candy tonight:").grid(row=0, column=0, sticky="w")
        current_total = config.CANDY_TOTAL if config.CANDY_TOTAL is not None else ""
        self.candy_total_var = tk.StringVar(value=str(current_total))
        ttk.Entry(frame, textvariable=self.candy_total_var, width=10).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(frame, text="Per trick-or-treater:").grid(row=1, column=0, sticky="w")
        self.candy_per_var = tk.StringVar(value=str(config.CANDY_PER_VISITOR))
        ttk.Entry(frame, textvariable=self.candy_per_var, width=10).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(frame, text="End hour (24h, e.g. 22 = 10pm):").grid(row=2, column=0, sticky="w")
        self.end_hour_var = tk.StringVar(value=str(config.EVENT_END_HOUR))
        ttk.Spinbox(frame, from_=0, to=23, textvariable=self.end_hour_var, width=8).grid(row=2, column=1, sticky="w", padx=4)

    # --- Render dashboard ---
    def _build_render_section(self):
        frame = ttk.LabelFrame(self, text="3. Public dashboard (optional)", padding=10)
        frame.pack(fill="x", padx=12, pady=8)

        if EXISTING_RENDER_URL:
            ttk.Label(frame, text=f"Already configured: {EXISTING_RENDER_URL}", foreground="#666").pack(anchor="w")
            self.render_url_var = None
            self.render_secret_var = None
        else:
            ttk.Label(frame, text="Render app URL:").pack(anchor="w")
            self.render_url_var = tk.StringVar()
            ttk.Entry(frame, textvariable=self.render_url_var, width=50).pack(fill="x")
            ttk.Label(frame, text="Render shared secret:").pack(anchor="w", pady=(6, 0))
            self.render_secret_var = tk.StringVar()
            ttk.Entry(frame, textvariable=self.render_secret_var, width=50, show="*").pack(fill="x")

    # --- Footer ---
    def _build_footer(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="x", padx=12, pady=8)
        ttk.Button(frame, text="Save and finish", command=self._save).pack(side="right")

    def _save(self):
        if self.working_rtsp_url:
            set_secret("RTSP_URL", repr(self.working_rtsp_url))

        try:
            candy_total = self.candy_total_var.get().strip()
            set_config_value("CANDY_TOTAL", int(candy_total) if candy_total else None)

            candy_per = self.candy_per_var.get().strip()
            if candy_per:
                set_config_value("CANDY_PER_VISITOR", int(candy_per))

            end_hour = self.end_hour_var.get().strip()
            if end_hour:
                set_config_value("EVENT_END_HOUR", int(end_hour))
        except ValueError:
            messagebox.showerror("Invalid candy numbers", "Candy amounts and end hour must be whole numbers.")
            return

        if self.render_url_var is not None:
            url = self.render_url_var.get().strip()
            if url:
                set_secret("RENDER_URL", repr(url))
                secret = self.render_secret_var.get().strip()
                if secret:
                    set_secret("RENDER_SECRET", repr(secret))

        messagebox.showinfo("Saved", "Settings saved! Next, let's draw your detection zone.")

        draw_now = messagebox.askyesno(
            "Draw detection zone",
            "Open the zone-drawing window now? (Click the corners of your yard/walkway on the live camera feed.)",
        )
        if draw_now:
            self.withdraw()
            subprocess.run([sys.executable, "pick_zone.py"])
            self.deiconify()

        start_now = messagebox.askyesno("Start tracking", "Setup's done! Launch the tracker now?")
        if start_now:
            subprocess.Popen([sys.executable, "main.py"])

        self.destroy()


if __name__ == "__main__":
    SetupApp().mainloop()
