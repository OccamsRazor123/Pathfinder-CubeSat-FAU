import tkinter as tk
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections
from datetime import datetime
import threading
import random
import time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ── Palette ──────────────────────────────────────────────────────────────────
BG_DEEP    = "#0d0f14"
BG_PANEL   = "#13161e"
BG_CARD    = "#1a1d28"
BORDER     = "#2a2d3e"
ACCENT_CYN = "#00e5ff"
ACCENT_GRN = "#00ff88"
ACCENT_YLW = "#ffd600"
ACCENT_BLU = "#448aff"
ACCENT_PRP = "#b388ff"
ACCENT_RED = "#ff5252"
TEXT_HI    = "#e8eaf6"
TEXT_MID   = "#9e9eb8"
TEXT_DIM   = "#4a4a6a"

FONT_MONO  = ("Consolas", 12)

class ProfessionalOBCDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PATHFINDER GROUND SEGMENT  ·  OBC TERMINAL")
        self.geometry("1500x960")
        self.configure(fg_color=BG_DEEP)

        self.start_time   = datetime.now()
        self.temp_history = collections.deque([22.0] * 60, maxlen=60)
        self.time_steps   = list(range(60))

        self._build_header()
        self._build_body()

        threading.Thread(target=self._mission_simulator, daemon=True).start()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, height=84, fg_color=BG_PANEL,
                           border_width=1, border_color=BORDER, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        # Left: mission identity
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left", padx=24, fill="y")
        ctk.CTkLabel(left, text="PATHFINDER  //  OBC TERMINAL",
                     font=("Consolas", 22, "bold"), text_color=TEXT_HI).pack(anchor="w", pady=(14, 0))
        ctk.CTkLabel(left, text="GROUND SEGMENT  ·  LIVE TELEMETRY",
                     font=("Consolas", 16), text_color=TEXT_MID).pack(anchor="w")

        # Centre: MET
        self.met_lbl = ctk.CTkLabel(hdr, text="MET  00:00:00",
                                    font=("Consolas", 42, "bold"), text_color=ACCENT_CYN)
        self.met_lbl.pack(side="left", expand=True)

        # Right: status dot + export
        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right", padx=24, fill="y")
        ctk.CTkButton(right, text="⬇  EXPORT LOGS",
                      fg_color=ACCENT_GRN, text_color="#000",
                      font=("Consolas", 14, "bold"),
                      height=42, width=180, corner_radius=4).pack(pady=15)

    # ── Body ──────────────────────────────────────────────────────────────────
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # 3 columns: env (wide) | health (medium) | terminal (medium)
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=3)
        body.grid_columnconfigure(2, weight=6)
        body.grid_rowconfigure(0, weight=5)   # top row — main content, gets most space
        body.grid_rowconfigure(1, weight=2)   # bottom row — compact graph strip

        self._build_env_panel(body)
        self._build_health_panel(body)
        self._build_terminal_panel(body)
        self._build_graph_panel(body)

    # ── Environmental Data ────────────────────────────────────────────────────
    def _build_env_panel(self, parent):
        panel = self._panel(parent, "ENVIRONMENTAL DATA", 0, 0)

        params = [
            ("AIR TEMP",   "──°C",   ACCENT_CYN, 40,   "temp"),
            ("CO₂ CONC",   "── ppm", ACCENT_GRN, 2000, "co2"),
            ("HUMIDITY",   "──%",    ACCENT_BLU, 100,  "hum"),
            ("LUMINOSITY", "── lux", ACCENT_YLW, 1000, "lux"),
            ("PRESSURE",   "── hPa", ACCENT_PRP, 1100, "pres"),
        ]

        self._env_widgets = {}
        for name, init, color, maxv, key in params:
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(10, 0))

            # Channel label
            ctk.CTkLabel(row, text=name, font=("Consolas", 18, "bold"),
                         text_color=TEXT_MID, width=160, anchor="w").pack(side="left")

            # Value — large
            val_lbl = ctk.CTkLabel(row, text=init,
                                   font=("Consolas", 46, "bold"), text_color=color)
            val_lbl.pack(side="right")

            # Bar
            bar = ctk.CTkProgressBar(panel, height=12, progress_color=color,
                                     fg_color=BG_CARD, corner_radius=4)
            bar.pack(fill="x", padx=20, pady=(4, 8))
            bar.set(0)

            self._env_widgets[key] = (val_lbl, bar, maxv)

    # ── Subsystem Health ──────────────────────────────────────────────────────
    def _build_health_panel(self, parent):
        panel = self._panel(parent, "SUBSYSTEM HEALTH", 0, 1)

        subsystems = [
            ("THERMAL STRIPS", ACCENT_YLW, "heater"),
            ("FLUID PUMP",     ACCENT_BLU,  "pump"),
            ("COOLING FANS",   ACCENT_GRN,  "fan"),
            ("SYSTEM LEDs",    TEXT_HI,     "led"),
        ]

        self._health_widgets = {}
        for name, color, key in subsystems:
            card = ctk.CTkFrame(panel, fg_color=BG_CARD,
                                border_width=1, border_color=BORDER, corner_radius=8)
            card.pack(fill="x", padx=16, pady=8)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=14)

            dot = ctk.CTkLabel(inner, text="●", font=("Arial", 46), text_color=TEXT_DIM)
            dot.pack(side="left")

            txt_col = ctk.CTkFrame(inner, fg_color="transparent")
            txt_col.pack(side="left", padx=14)
            ctk.CTkLabel(txt_col, text=name,
                         font=("Consolas", 20, "bold"), text_color=TEXT_HI).pack(anchor="w")
            state_lbl = ctk.CTkLabel(txt_col, text="○  STANDBY",
                                     font=("Consolas", 15), text_color=TEXT_DIM)
            state_lbl.pack(anchor="w")

            self._health_widgets[key] = {"dot": dot, "state_lbl": state_lbl, "color": color}

    # ── Terminal ──────────────────────────────────────────────────────────────
    def _build_terminal_panel(self, parent):
        panel = self._panel(parent, "UPLINK / DOWNLINK  —  RAW STREAM", 0, 2)

        # header strip
        hdr = ctk.CTkFrame(panel, fg_color=BG_CARD, height=36, corner_radius=0)
        hdr.pack(fill="x", padx=16, pady=(0, 6))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="  ● RX ACTIVE   ○ TX STANDBY",
                     font=("Consolas", 14, "bold"), text_color=ACCENT_GRN).pack(side="left", padx=8, fill="y")

        self.terminal = tk.Text(panel,
                                bg=BG_CARD, fg=ACCENT_GRN,
                                font=("Consolas", 17, "bold"),
                                insertbackground=ACCENT_GRN,
                                selectbackground="#2a2d3e",
                                borderwidth=0, highlightthickness=0,
                                relief="flat", spacing1=4, spacing3=4)
        self.terminal.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    # ── Graph ─────────────────────────────────────────────────────────────────
    def _build_graph_panel(self, parent):
        panel = self._panel(parent, "MISSION TIMELINE  —  AIR TEMPERATURE (°C)", 1, 0,
                            colspan=3)

        self.fig = Figure(figsize=(6, 3), dpi=100, facecolor=BG_PANEL)
        self.ax  = self.fig.add_subplot(111, facecolor=BG_CARD)
        self.fig.subplots_adjust(left=0.05, right=0.98, top=0.92, bottom=0.14)

        for spine in self.ax.spines.values():
            spine.set_color(BORDER)
        self.ax.tick_params(colors=TEXT_MID, labelsize=11)
        self.ax.set_xlabel("Time (seconds)", color=TEXT_MID, fontsize=12)
        self.ax.set_ylabel("Temp (°C)", color=TEXT_MID, fontsize=12)
        self.ax.yaxis.label.set_fontfamily("Consolas")
        self.ax.xaxis.label.set_fontfamily("Consolas")
        self.ax.grid(color=BORDER, linewidth=0.6, alpha=0.7)

        self.line, = self.ax.plot(self.time_steps, self.temp_history,
                                  color=ACCENT_CYN, linewidth=2.5, solid_capstyle="round")
        self.fill  = self.ax.fill_between(self.time_steps, list(self.temp_history),
                                          alpha=0.12, color=ACCENT_CYN)

        self.canvas = FigureCanvasTkAgg(self.fig, master=panel)
        self.canvas.get_tk_widget().configure(bg=BG_PANEL, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=16, pady=(0, 12))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _panel(self, parent, title, row, col, colspan=1):
        frame = ctk.CTkFrame(parent, fg_color=BG_PANEL,
                             border_width=1, border_color=BORDER, corner_radius=10)
        frame.grid(row=row, column=col, columnspan=colspan,
                   padx=6, pady=6, sticky="nsew")

        title_row = ctk.CTkFrame(frame, fg_color=BG_CARD, height=52,
                                 corner_radius=0)
        title_row.pack(fill="x")
        title_row.pack_propagate(False)
        ctk.CTkLabel(title_row, text=f"  {title}",
                     font=("Consolas", 18, "bold"), text_color=TEXT_HI,
                     anchor="w").pack(side="left", padx=12, fill="y")
        return frame

    # ── Simulator ─────────────────────────────────────────────────────────────
    def _mission_simulator(self):
        c_temp = 22.0
        c_co2  = 450
        c_hum  = 55.0
        c_lux  = 800
        c_pres = 1013.25
        while True:
            c_temp += random.uniform(-0.3, 0.3)
            c_co2  += random.randint(-2, 5)
            c_hum   = max(0, min(100, c_hum + random.uniform(-0.5, 0.5)))
            c_lux  += random.randint(-10, 10)
            c_pres += random.uniform(-0.1, 0.1)

            data = {
                "temp": c_temp, "co2": c_co2, "hum": c_hum,
                "lux": c_lux, "pres": c_pres,
                "heater": "ON"  if c_temp < 20.0 else "OFF",
                "pump":   "ON"  if (int(time.time()) % 15 < 3) else "OFF",
                "fan":    "ON"  if c_temp > 24.0 else "OFF",
                "led":    "ON"  if c_lux < 500 else "OFF",
            }
            self.after(0, self._update, data)
            time.sleep(1)

    # ── Update ────────────────────────────────────────────────────────────────
    def _update(self, d):
        elapsed = datetime.now() - self.start_time
        met_str = str(elapsed).split(".")[0]
        self.met_lbl.configure(text=f"MET  {met_str}")

        # Environmental
        fmt = {
            "temp": (d["temp"],  "°C",   lambda v: f"{v:+.1f}°C"),
            "co2":  (d["co2"],   " ppm",  lambda v: f"{v:.0f} ppm"),
            "hum":  (d["hum"],   "%",     lambda v: f"{v:.1f}%"),
            "lux":  (d["lux"],   " lux",  lambda v: f"{v:.0f} lux"),
            "pres": (d["pres"],  " hPa",  lambda v: f"{v:.1f} hPa"),
        }
        for key, (val, _, formatter) in fmt.items():
            lbl, bar, maxv = self._env_widgets[key]
            lbl.configure(text=formatter(val))
            bar.set(min(max(val / maxv, 0), 1.0))

        # Health
        for key, hw in self._health_widgets.items():
            on = d[key] == "ON"
            hw["dot"].configure(text_color=hw["color"] if on else TEXT_DIM)
            hw["state_lbl"].configure(
                text="● ACTIVE" if on else "○ STANDBY",
                text_color=hw["color"] if on else TEXT_DIM)

        # Graph
        self.temp_history.append(d["temp"])
        y = list(self.temp_history)
        self.line.set_ydata(y)
        # Redraw fill
        self.fill.remove()
        self.fill = self.ax.fill_between(self.time_steps, y, alpha=0.12, color=ACCENT_CYN)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

        # Terminal — two lines per packet for readability at large font
        ts = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert("end",
            f"[{ts}]  RX  ·  MET {met_str}\n"
            f"  T={d['temp']:+.1f}°C  H={d['hum']:.1f}%  CO2={d['co2']:.0f}ppm  P={d['pres']:.1f}hPa\n\n")
        self.terminal.see("end")


if __name__ == "__main__":
    app = ProfessionalOBCDashboard()
    app.mainloop()
