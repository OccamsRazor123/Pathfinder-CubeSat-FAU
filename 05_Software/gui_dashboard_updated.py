# =============================================================================
# PATHFINDER OBC TERMINAL — GUI + MISSION SCRIPT (LAUNCH DAY VERSION)
# Proportional climate control, lux-hour lighting, daily pump dosing.
# GUI shows live sensor data; START MISSION runs the full autonomous loop.
# =============================================================================

import tkinter as tk
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections
from datetime import datetime
import threading
import math
import csv
import os
import time
import random

# ── GPIO / Sensor imports (graceful fallback on non-Pi) ──────────────────────
try:
    import RPi.GPIO as GPIO
    import board
    import adafruit_scd4x
    import adafruit_veml7700
    import adafruit_bme280.basic as adafruit_bme280
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # ── Pin map (from launch day script) ─────────────────────────────────────
    WATER_HEAT_PIN = 17   # Physical 11
    GROW_HEAT_PIN  = 27   # Physical 13
    FAN_PIN        = 24   # Physical 18
    LED_PIN        = 25   # Physical 22
    PUMP_CLK       = 18   # Physical 12 — hardware PWM
    PUMP_EN        = 23   # Physical 16
    PUMP_DIR       = 16   # Physical 36

    pins_to_setup = [WATER_HEAT_PIN, GROW_HEAT_PIN, FAN_PIN, LED_PIN,
                     PUMP_CLK, PUMP_EN, PUMP_DIR]
    for pin in pins_to_setup:
        GPIO.setup(pin, GPIO.OUT)
    GPIO.output(PUMP_EN, GPIO.LOW)

    # PWM objects — created once, exactly like launch day
    pwm_water = GPIO.PWM(WATER_HEAT_PIN, 100)
    pwm_grow  = GPIO.PWM(GROW_HEAT_PIN,  100)
    pwm_fan   = GPIO.PWM(FAN_PIN,         100)
    pwm_led   = GPIO.PWM(LED_PIN,        1000)
    pwm_pump  = GPIO.PWM(PUMP_CLK,       4000)

    pwm_water.start(0)
    pwm_grow.start(0)
    pwm_fan.start(0)
    pwm_led.start(0)

    i2c = board.I2C()
    GPIO_AVAILABLE = True

except Exception as _e:
    GPIO_AVAILABLE = False
    # Stub objects so the rest of the code never has to check None
    class _PWMStub:
        def ChangeDutyCycle(self, v): pass
        def start(self, v): pass
        def stop(self): pass
    pwm_water = pwm_grow = pwm_fan = pwm_led = pwm_pump = _PWMStub()
    print(f"[WARNING] Hardware not available — simulation mode. ({_e})")

def gpio_out(pin, state: bool):
    if GPIO_AVAILABLE:
        try: GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        except Exception as e: print(f"[GPIO] pin {pin}: {e}")

# ── Mission configuration (mirrors launch day script exactly) ─────────────────
TEMP_THRESHOLD_LOW  = 20.0
TEMP_THRESHOLD_HIGH = 22.0
WATER_TEMP_LOW      = 20.0
P_BAND              = 5.0
MAX_HEATER_POWER    = 25.0
DAY_CYCLE_SECONDS   = 120        # change to 86400 for real mission
TARGET_LUX_HOURS    = 1
TARGET_LUX_SECONDS  = TARGET_LUX_HOURS * 3600
MAX_LED_DUTY        = 100.0
TARGET_DAILY_VOL_UL = 88.0
PUMP_FLOW_RATE      = 88.0       # uL/min
R_FIXED             = 20000.0
R_NOMINAL           = 20000.0
B_COEFFICIENT       = 3950.0
V_IN                = 3.3
LUX_CORRECTION      = 0.88

def clamp_pwm(v):
    return max(0.0, min(100.0, v))

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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
ACCENT_ORG = "#ff9100"
TEXT_HI    = "#e8eaf6"
TEXT_MID   = "#9e9eb8"
TEXT_DIM   = "#4a4a6a"


# ── Sensor setup ──────────────────────────────────────────────────────────────
def setup_sensors():
    s = {'scd': None, 'bme': None, 'veml': None, 'ads_chan': None}
    if not GPIO_AVAILABLE:
        return s
    print("\n--- Initializing I2C Hardware ---")
    try:
        s['scd'] = adafruit_scd4x.SCD4X(i2c)
        s['scd'].start_periodic_measurement()
        print(" [OK] SCD40")
    except Exception as e: print(f" [FAIL] SCD40: {e}")
    try:
        for addr in [0x77, 0x76]:
            try:
                s['bme'] = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=addr)
                print(f" [OK] BME280 @ {hex(addr)}")
                break
            except: continue
    except Exception as e: print(f" [FAIL] BME280: {e}")
    try:
        s['veml'] = adafruit_veml7700.VEML7700(i2c)
        print(" [OK] VEML7700")
    except Exception as e: print(f" [FAIL] VEML7700: {e}")
    try:
        ads = ADS.ADS1115(i2c)
        s['ads_chan'] = AnalogIn(ads, 0)
        print(" [OK] ADS1115")
    except Exception as e: print(f" [FAIL] ADS1115: {e}")
    return s

def log_to_csv(filename, row):
    exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp","CO2_ppm","BME_Temp_C","BME_RH",
                        "Pressure_hPa","Lux","Thermistor_C",
                        "Grow_Heat_%","Water_Heat_%","Fans_%","LEDs_%",
                        "Pump_Active","Accum_Lux_Hrs"])
        w.writerow(row)


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
class ProfessionalOBCDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PATHFINDER GROUND SEGMENT  ·  OBC TERMINAL")
        self.geometry("1600x1000")
        self.configure(fg_color=BG_DEEP)

        self.start_time   = datetime.now()
        self.temp_history = collections.deque([22.0] * 60, maxlen=60)
        self.time_steps   = list(range(60))

        self._mission_running = False
        self._stop_event      = threading.Event()
        self._pump_state      = "IDLE"   # IDLE | LOADING | UNLOADING
        self._manual_pump_on  = False

        # Shared telemetry — mission thread writes, GUI reads every second
        self._live = {
            "temp": float('nan'), "co2": float('nan'), "hum": float('nan'),
            "lux":  float('nan'), "pres": float('nan'), "therm": float('nan'),
            "g_heat": 0.0, "w_heat": 0.0, "fan": 0.0, "led": 0.0,
            "pump_active": False, "accum_lux_hrs": 0.0,
        }

        self._sensors = setup_sensors()

        self._build_header()
        self._build_body()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Simulation loop keeps display alive before mission starts
        threading.Thread(target=self._sim_loop, daemon=True).start()
        # GUI refresh — runs forever on main thread via after()
        self._gui_tick()

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════════════════
    def _build_header(self):
        hdr = ctk.CTkFrame(self, height=84, fg_color=BG_PANEL,
                           border_width=1, border_color=BORDER, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left", padx=24, fill="y")
        ctk.CTkLabel(left, text="PATHFINDER  //  OBC TERMINAL",
                     font=("Consolas", 22, "bold"), text_color=TEXT_HI).pack(anchor="w", pady=(14,0))
        ctk.CTkLabel(left, text="GROUND SEGMENT  ·  LIVE TELEMETRY",
                     font=("Consolas", 16), text_color=TEXT_MID).pack(anchor="w")

        self.met_lbl = ctk.CTkLabel(hdr, text="MET  00:00:00",
                                    font=("Consolas", 42, "bold"), text_color=ACCENT_CYN)
        self.met_lbl.pack(side="left", expand=True)

        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right", padx=24, fill="y")
        ctk.CTkButton(right, text="⬇  EXPORT LOGS",
                      fg_color=ACCENT_GRN, text_color="#000",
                      font=("Consolas", 14, "bold"), height=42, width=180,
                      corner_radius=4, command=self._export_logs).pack(pady=15)

    # ══════════════════════════════════════════════════════════════════════════
    # BODY
    # ══════════════════════════════════════════════════════════════════════════
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=3)
        body.grid_columnconfigure(2, weight=6)
        body.grid_rowconfigure(0, weight=5)
        body.grid_rowconfigure(1, weight=2)
        body.grid_rowconfigure(2, weight=3)
        self._build_env_panel(body)
        self._build_health_panel(body)
        self._build_terminal_panel(body)
        self._build_graph_panel(body)
        self._build_mission_control(body)
        self._build_water_management(body)

    # ── Environmental Data ────────────────────────────────────────────────────
    def _build_env_panel(self, parent):
        panel = self._panel(parent, "ENVIRONMENTAL DATA", 0, 0)
        params = [
            ("AIR TEMP",   "──C",    ACCENT_CYN, 40,   "temp"),
            ("CO2 CONC",   "── ppm", ACCENT_GRN, 2000, "co2"),
            ("HUMIDITY",   "──%",    ACCENT_BLU, 100,  "hum"),
            ("LUMINOSITY", "── lux", ACCENT_YLW, 2000, "lux"),
            ("PRESSURE",   "── hPa", ACCENT_PRP, 1100, "pres"),
        ]
        self._env_widgets = {}
        for name, init, color, maxv, key in params:
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(10,0))
            ctk.CTkLabel(row, text=name, font=("Consolas", 18, "bold"),
                         text_color=TEXT_MID, width=160, anchor="w").pack(side="left")
            val_lbl = ctk.CTkLabel(row, text=init,
                                   font=("Consolas", 46, "bold"), text_color=color)
            val_lbl.pack(side="right")
            bar = ctk.CTkProgressBar(panel, height=12, progress_color=color,
                                     fg_color=BG_CARD, corner_radius=4)
            bar.pack(fill="x", padx=20, pady=(4,8))
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
        hdr = ctk.CTkFrame(panel, fg_color=BG_CARD, height=36, corner_radius=0)
        hdr.pack(fill="x", padx=16, pady=(0,6))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="  ● RX ACTIVE   ○ TX STANDBY",
                     font=("Consolas", 14, "bold"), text_color=ACCENT_GRN).pack(side="left", padx=8, fill="y")
        self.terminal = tk.Text(panel, bg=BG_CARD, fg=ACCENT_GRN,
                                font=("Consolas", 17, "bold"),
                                insertbackground=ACCENT_GRN,
                                selectbackground="#2a2d3e",
                                borderwidth=0, highlightthickness=0,
                                relief="flat", spacing1=4, spacing3=4)
        self.terminal.pack(fill="both", expand=True, padx=16, pady=(0,12))

    # ── Graph ─────────────────────────────────────────────────────────────────
    def _build_graph_panel(self, parent):
        panel = self._panel(parent, "MISSION TIMELINE  —  AIR TEMPERATURE (C)", 1, 0, colspan=3)
        self.fig = Figure(figsize=(6,3), dpi=100, facecolor=BG_PANEL)
        self.ax  = self.fig.add_subplot(111, facecolor=BG_CARD)
        self.fig.subplots_adjust(left=0.05, right=0.98, top=0.92, bottom=0.14)
        for spine in self.ax.spines.values(): spine.set_color(BORDER)
        self.ax.tick_params(colors=TEXT_MID, labelsize=11)
        self.ax.set_xlabel("Time (s)", color=TEXT_MID, fontsize=12)
        self.ax.set_ylabel("Temp (C)", color=TEXT_MID, fontsize=12)
        self.ax.yaxis.label.set_fontfamily("Consolas")
        self.ax.xaxis.label.set_fontfamily("Consolas")
        self.ax.grid(color=BORDER, linewidth=0.6, alpha=0.7)
        self.line, = self.ax.plot(self.time_steps, self.temp_history,
                                  color=ACCENT_CYN, linewidth=2.5, solid_capstyle="round")
        self.fill = self.ax.fill_between(self.time_steps, list(self.temp_history),
                                         alpha=0.12, color=ACCENT_CYN)
        self.canvas = FigureCanvasTkAgg(self.fig, master=panel)
        self.canvas.get_tk_widget().configure(bg=BG_PANEL, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=16, pady=(0,12))

    # ── Mission Control ────────────────────────────────────────────────────────
    def _build_mission_control(self, parent):
        panel = self._panel(parent, "MISSION CONTROL", 2, 0)

        top = ctk.CTkFrame(panel, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12,4))
        self._btn_start = ctk.CTkButton(
            top, text="▶  START MISSION",
            fg_color=ACCENT_GRN, text_color="#000",
            font=("Consolas", 16, "bold"), height=52, corner_radius=6,
            command=self._start_mission)
        self._btn_start.pack(side="left", fill="x", expand=True, padx=(0,6))
        self._btn_stop = ctk.CTkButton(
            top, text="■  STOP MISSION",
            fg_color=ACCENT_RED, text_color="#fff",
            font=("Consolas", 16, "bold"), height=52, corner_radius=6,
            state="disabled", command=self._stop_mission)
        self._btn_stop.pack(side="left", fill="x", expand=True, padx=(6,0))

        self._mission_status_lbl = ctk.CTkLabel(
            panel, text="●  MISSION IDLE",
            font=("Consolas", 15, "bold"), text_color=TEXT_DIM)
        self._mission_status_lbl.pack(anchor="w", padx=20, pady=(4,6))

        sep = ctk.CTkFrame(panel, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(panel, text="  SUBSYSTEM TESTS  (5-second pulse each)",
                     font=("Consolas", 13, "bold"), text_color=TEXT_DIM,
                     anchor="w").pack(fill="x", padx=16)

        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4,12))
        for label, color, cmd in [
            ("HEATERS", ACCENT_YLW, self._test_heaters),
            ("PUMP",    ACCENT_BLU,  self._test_pump),
            ("FANS",    ACCENT_GRN,  self._test_fans),
            ("LEDs",    TEXT_HI,     self._test_leds),
        ]:
            ctk.CTkButton(btn_row, text=label,
                          fg_color=BG_CARD, border_width=1, border_color=color,
                          text_color=color, hover_color=BG_DEEP,
                          font=("Consolas", 14, "bold"), height=44, corner_radius=6,
                          command=cmd).pack(side="left", fill="x", expand=True, padx=3)

    # ── Water Management ──────────────────────────────────────────────────────
    def _build_water_management(self, parent):
        panel = self._panel(parent, "WATER MANAGEMENT", 2, 1, colspan=2)

        status_row = ctk.CTkFrame(panel, fg_color="transparent")
        status_row.pack(fill="x", padx=20, pady=(12,4))
        self._pump_dot = ctk.CTkLabel(status_row, text="●",
                                      font=("Arial", 40), text_color=TEXT_DIM)
        self._pump_dot.pack(side="left")
        pump_txt = ctk.CTkFrame(status_row, fg_color="transparent")
        pump_txt.pack(side="left", padx=12)
        ctk.CTkLabel(pump_txt, text="FLUID PUMP",
                     font=("Consolas", 20, "bold"), text_color=TEXT_HI).pack(anchor="w")
        self._pump_status_lbl = ctk.CTkLabel(pump_txt, text="○  IDLE",
                                             font=("Consolas", 15), text_color=TEXT_DIM)
        self._pump_status_lbl.pack(anchor="w")
        gpio_color = ACCENT_GRN if GPIO_AVAILABLE else ACCENT_RED
        gpio_text  = "● GPIO LIVE" if GPIO_AVAILABLE else "⚠  SIMULATION MODE"
        ctk.CTkLabel(status_row, text=gpio_text,
                     font=("Consolas", 13, "bold"), text_color=gpio_color).pack(side="right", padx=8)

        sep = ctk.CTkFrame(panel, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=8)

        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0,16))
        self._btn_load = ctk.CTkButton(
            btn_row, text="LOAD WATER\n(PUMP FWD  CW)",
            fg_color=ACCENT_BLU, text_color="#fff",
            font=("Consolas", 16, "bold"), height=72, corner_radius=8,
            command=self._pump_load)
        self._btn_load.pack(side="left", fill="x", expand=True, padx=(0,8))
        self._btn_pump_stop = ctk.CTkButton(
            btn_row, text="STOP PUMP",
            fg_color=BG_CARD, border_width=2, border_color=ACCENT_RED,
            text_color=ACCENT_RED, hover_color=BG_DEEP,
            font=("Consolas", 16, "bold"), height=72, corner_radius=8,
            state="disabled", command=self._pump_stop)
        self._btn_pump_stop.pack(side="left", fill="x", expand=True, padx=8)
        self._btn_unload = ctk.CTkButton(
            btn_row, text="UNLOAD WATER\n(PUMP REV  CCW)",
            fg_color=ACCENT_ORG, text_color="#000",
            font=("Consolas", 16, "bold"), height=72, corner_radius=8,
            command=self._pump_unload)
        self._btn_unload.pack(side="left", fill="x", expand=True, padx=(8,0))

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _panel(self, parent, title, row, col, colspan=1):
        frame = ctk.CTkFrame(parent, fg_color=BG_PANEL,
                             border_width=1, border_color=BORDER, corner_radius=10)
        frame.grid(row=row, column=col, columnspan=colspan,
                   padx=6, pady=6, sticky="nsew")
        tr = ctk.CTkFrame(frame, fg_color=BG_CARD, height=52, corner_radius=0)
        tr.pack(fill="x"); tr.pack_propagate(False)
        ctk.CTkLabel(tr, text=f"  {title}",
                     font=("Consolas", 18, "bold"), text_color=TEXT_HI,
                     anchor="w").pack(side="left", padx=12, fill="y")
        return frame

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert("end", f"[{ts}]  SYS  ·  {msg}\n\n")
        self.terminal.see("end")

    # ══════════════════════════════════════════════════════════════════════════
    # SIMULATION LOOP (fake data when mission not running)
    # ══════════════════════════════════════════════════════════════════════════
    def _sim_loop(self):
        c_temp = 22.0; c_co2 = 450; c_hum = 55.0; c_lux = 800; c_pres = 1013.25
        while True:
            if not self._mission_running:
                c_temp += random.uniform(-0.3, 0.3)
                c_co2  += random.randint(-2, 5)
                c_hum   = max(0, min(100, c_hum + random.uniform(-0.5, 0.5)))
                c_lux  += random.randint(-10, 10)
                c_pres += random.uniform(-0.1, 0.1)
                self._live.update({
                    "temp": c_temp, "co2": c_co2, "hum": c_hum,
                    "lux": c_lux, "pres": c_pres, "therm": c_temp - 1.0,
                    "g_heat": 0.0, "w_heat": 0.0, "fan": 0.0, "led": 0.0,
                    "pump_active": False, "accum_lux_hrs": 0.0,
                })
            time.sleep(1)

    # ══════════════════════════════════════════════════════════════════════════
    # GUI TICK — reads _live and refreshes all widgets every second
    # ══════════════════════════════════════════════════════════════════════════
    def _gui_tick(self):
        d = self._live
        elapsed = datetime.now() - self.start_time
        met_str = str(elapsed).split(".")[0]
        self.met_lbl.configure(text=f"MET  {met_str}")

        def safe(v, fmt):
            return fmt(v) if not (isinstance(v, float) and math.isnan(v)) else "──"

        displays = {
            "temp": safe(d["temp"], lambda v: f"{v:+.1f}C"),
            "co2":  safe(d["co2"],  lambda v: f"{v:.0f} ppm"),
            "hum":  safe(d["hum"],  lambda v: f"{v:.1f}%"),
            "lux":  safe(d["lux"],  lambda v: f"{v:.0f} lux"),
            "pres": safe(d["pres"], lambda v: f"{v:.1f} hPa"),
        }
        for key, txt in displays.items():
            lbl, bar, maxv = self._env_widgets[key]
            lbl.configure(text=txt)
            val = d[key]
            bar.set(0 if math.isnan(val) else min(max(val / maxv, 0), 1.0))

        # Health indicators — show real PWM duty %
        health = {
            "heater": d["g_heat"] > 0.5 or d["w_heat"] > 0.5,
            "pump":   d["pump_active"] or self._pump_state != "IDLE",
            "fan":    d["fan"] > 0.5,
            "led":    d["led"] > 0.5,
        }
        labels = {
            "heater": f"● G:{d['g_heat']:.0f}%  W:{d['w_heat']:.0f}%" if health["heater"] else "○  STANDBY",
            "pump":   "● ACTIVE" if health["pump"] else "○  STANDBY",
            "fan":    f"● {d['fan']:.0f}% PWR" if health["fan"] else "○  STANDBY",
            "led":    f"● {d['led']:.0f}%  LUX-HR {d['accum_lux_hrs']:.2f}" if health["led"] else f"○  LUX-HR {d['accum_lux_hrs']:.2f}",
        }
        for key, on in health.items():
            hw = self._health_widgets[key]
            hw["dot"].configure(text_color=hw["color"] if on else TEXT_DIM)
            hw["state_lbl"].configure(text=labels[key],
                                      text_color=hw["color"] if on else TEXT_DIM)

        # Temperature graph
        temp_val = d["temp"]
        if not math.isnan(temp_val):
            self.temp_history.append(temp_val)
        y = list(self.temp_history)
        self.line.set_ydata(y)
        self.fill.remove()
        self.fill = self.ax.fill_between(self.time_steps, y, alpha=0.12, color=ACCENT_CYN)
        self.ax.relim(); self.ax.autoscale_view(); self.canvas.draw_idle()

        # Terminal — live data rows during mission
        if self._mission_running:
            ts = datetime.now().strftime("%H:%M:%S")
            self.terminal.insert("end",
                f"[{ts}]  RX  ·  MET {met_str}\n"
                f"  T={safe(d['temp'], lambda v: f'{v:+.1f}C')}  "
                f"H={safe(d['hum'],  lambda v: f'{v:.1f}%')}  "
                f"CO2={safe(d['co2'], lambda v: f'{v:.0f}ppm')}  "
                f"P={safe(d['pres'], lambda v: f'{v:.1f}hPa')}  "
                f"LUX-HR={d['accum_lux_hrs']:.2f}\n\n")
            self.terminal.see("end")

        self.after(1000, self._gui_tick)

    # ══════════════════════════════════════════════════════════════════════════
    # MISSION LOOP — exact launch-day logic running in background thread
    # ══════════════════════════════════════════════════════════════════════════
    def _mission_loop(self, filename):
        sensors = self._sensors

        pump_is_running        = False
        pump_stop_time         = 0
        daily_dose_delivered   = False
        accumulated_lux_seconds = 0.0
        day_start_time         = time.time()
        last_loop_time         = time.time()

        try:
            while not self._stop_event.is_set():
                current_time = time.time()
                dt = current_time - last_loop_time
                last_loop_time = current_time

                co2 = bme_t = bme_rh = bme_p = lux = therm_t = float('nan')
                g_heat_dc = w_heat_dc = fan_dc = led_dc = 0.0

                # Day cycle reset
                if current_time - day_start_time >= DAY_CYCLE_SECONDS:
                    accumulated_lux_seconds = 0.0
                    daily_dose_delivered    = False
                    day_start_time          = current_time
                    self.after(0, self._log, "NEW DAY CYCLE — resetting lux-hr and fluid trackers")

                # Sensor reads
                try:
                    if sensors['scd'] and sensors['scd'].data_ready:
                        co2 = sensors['scd'].CO2
                except: pass
                try:
                    if sensors['bme']:
                        bme_t  = sensors['bme'].temperature
                        bme_rh = sensors['bme'].relative_humidity
                        bme_p  = sensors['bme'].pressure
                except: pass
                try:
                    if sensors['veml']:
                        lux = sensors['veml'].lux * LUX_CORRECTION
                except: pass
                try:
                    if sensors['ads_chan']:
                        v_out = sensors['ads_chan'].voltage
                        if 0.1 < v_out < (V_IN - 0.1):
                            res = R_FIXED * ((V_IN / v_out) - 1)
                            s   = math.log(res / R_NOMINAL) / B_COEFFICIENT
                            s  += 1.0 / (25.0 + 273.15)
                            therm_t = (1.0 / s) - 273.15
                except: pass

                # Lighting — lux-hour accumulation (launch day logic)
                if accumulated_lux_seconds < TARGET_LUX_SECONDS:
                    led_dc = MAX_LED_DUTY
                    if not math.isnan(lux) and lux > 0:
                        accumulated_lux_seconds += lux * dt
                else:
                    led_dc = 0.0
                pwm_led.ChangeDutyCycle(led_dc)

                accumulated_lux_hours = accumulated_lux_seconds / 3600.0

                # Climate control — proportional (launch day logic)
                if not math.isnan(bme_t):
                    fan_dc = clamp_pwm(((bme_t - TEMP_THRESHOLD_HIGH) / P_BAND) * 100.0) \
                             if bme_t > TEMP_THRESHOLD_HIGH else 0.0
                    if bme_t < TEMP_THRESHOLD_LOW:
                        g_heat_dc = min(MAX_HEATER_POWER,
                                        clamp_pwm(((TEMP_THRESHOLD_LOW - bme_t) / P_BAND) * 100.0))
                    else:
                        g_heat_dc = 0.0

                if not math.isnan(therm_t):
                    if therm_t < WATER_TEMP_LOW:
                        w_heat_dc = min(MAX_HEATER_POWER,
                                        clamp_pwm(((WATER_TEMP_LOW - therm_t) / P_BAND) * 100.0))
                    else:
                        w_heat_dc = 0.0

                pwm_fan.ChangeDutyCycle(fan_dc)
                pwm_grow.ChangeDutyCycle(g_heat_dc)
                pwm_water.ChangeDutyCycle(w_heat_dc)

                # Pump dosing — non-blocking (launch day logic)
                if not daily_dose_delivered and not pump_is_running:
                    dur = (TARGET_DAILY_VOL_UL / PUMP_FLOW_RATE) * 60.0
                    pump_stop_time       = current_time + dur
                    pump_is_running      = True
                    daily_dose_delivered = True
                    self.after(0, self._log,
                               f"DAILY FEEDING — {TARGET_DAILY_VOL_UL}uL over {dur:.1f}s")
                    gpio_out(PUMP_DIR, True)
                    gpio_out(PUMP_EN,  True)
                    pwm_pump.start(50)

                if pump_is_running and current_time >= pump_stop_time:
                    pwm_pump.stop()
                    gpio_out(PUMP_EN, False)
                    pump_is_running = False
                    self.after(0, self._log, "FLUID DISPENSE COMPLETE")

                # Push live data to GUI
                self._live.update({
                    "temp": bme_t,  "co2": co2,   "hum": bme_rh,
                    "lux":  lux,    "pres": bme_p, "therm": therm_t,
                    "g_heat": g_heat_dc, "w_heat": w_heat_dc,
                    "fan": fan_dc,  "led": led_dc,
                    "pump_active": pump_is_running,
                    "accum_lux_hrs": accumulated_lux_hours,
                })

                log_to_csv(filename, [
                    time.strftime("%H:%M:%S"), co2, bme_t, bme_rh, bme_p,
                    lux, therm_t, g_heat_dc, w_heat_dc, fan_dc, led_dc,
                    pump_is_running, accumulated_lux_hours
                ])

                time.sleep(2)

        finally:
            # Safe all hardware on exit
            for p in [pwm_water, pwm_grow, pwm_fan, pwm_led, pwm_pump]:
                try: p.stop()
                except: pass
            if GPIO_AVAILABLE:
                for pin in [PUMP_EN, PUMP_DIR, PUMP_CLK,
                            WATER_HEAT_PIN, GROW_HEAT_PIN, FAN_PIN, LED_PIN]:
                    try: GPIO.output(pin, GPIO.LOW)
                    except: pass

    # ══════════════════════════════════════════════════════════════════════════
    # MISSION CONTROL ACTIONS
    # ══════════════════════════════════════════════════════════════════════════
    def _start_mission(self):
        if self._mission_running:
            return
        self._mission_running = True
        self._stop_event.clear()
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pathfinder_{ts}.csv"
        threading.Thread(target=self._mission_loop,
                         args=(filename,), daemon=True).start()
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._mission_status_lbl.configure(text="●  MISSION RUNNING", text_color=ACCENT_GRN)
        self._log(f"MISSION START — logging to {filename}")

    def _stop_mission(self):
        self._stop_event.set()
        self._mission_running = False
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._mission_status_lbl.configure(text="●  MISSION STOPPED", text_color=ACCENT_RED)
        self._log("MISSION STOP — autonomous loop terminated")

    # ── Subsystem tests ────────────────────────────────────────────────────────
    def _test_heaters(self):
        def _run():
            self.after(0, self._log, "TEST HEATERS — 25% PWM for 5s")
            pwm_grow.ChangeDutyCycle(25)
            pwm_water.ChangeDutyCycle(25)
            time.sleep(5)
            pwm_grow.ChangeDutyCycle(0)
            pwm_water.ChangeDutyCycle(0)
            self.after(0, self._log, "TEST HEATERS — complete")
        threading.Thread(target=_run, daemon=True).start()

    def _test_pump(self):
        def _run():
            self.after(0, self._log, "TEST PUMP — FWD 3s then REV 3s")
            gpio_out(PUMP_DIR, True); gpio_out(PUMP_EN, True)
            pwm_pump.start(50); time.sleep(3); pwm_pump.stop()
            gpio_out(PUMP_EN, False); time.sleep(0.5)
            gpio_out(PUMP_DIR, False); gpio_out(PUMP_EN, True)
            pwm_pump.start(50); time.sleep(3); pwm_pump.stop()
            gpio_out(PUMP_EN, False)
            self.after(0, self._log, "TEST PUMP — complete")
        threading.Thread(target=_run, daemon=True).start()

    def _test_fans(self):
        def _run():
            self.after(0, self._log, "TEST FANS — 100% for 5s")
            pwm_fan.ChangeDutyCycle(100); time.sleep(5)
            pwm_fan.ChangeDutyCycle(0)
            self.after(0, self._log, "TEST FANS — complete")
        threading.Thread(target=_run, daemon=True).start()

    def _test_leds(self):
        def _run():
            self.after(0, self._log, "TEST LEDs — 100% for 5s")
            pwm_led.ChangeDutyCycle(100); time.sleep(5)
            pwm_led.ChangeDutyCycle(0)
            self.after(0, self._log, "TEST LEDs — complete")
        threading.Thread(target=_run, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # WATER MANAGEMENT (manual pump override, uses same pwm_pump object)
    # ══════════════════════════════════════════════════════════════════════════
    def _pump_load(self):
        self._pump_state = "LOADING"
        gpio_out(PUMP_DIR, True)
        gpio_out(PUMP_EN,  True)
        pwm_pump.start(50)
        self._pump_dot.configure(text_color=ACCENT_BLU)
        self._pump_status_lbl.configure(text="LOADING — PUMP FWD (CW)", text_color=ACCENT_BLU)
        self._btn_load.configure(state="disabled")
        self._btn_unload.configure(state="disabled")
        self._btn_pump_stop.configure(state="normal")
        self._log("PUMP FWD (CW) — water loading initiated")

    def _pump_unload(self):
        self._pump_state = "UNLOADING"
        gpio_out(PUMP_DIR, False)
        gpio_out(PUMP_EN,  True)
        pwm_pump.start(50)
        self._pump_dot.configure(text_color=ACCENT_ORG)
        self._pump_status_lbl.configure(text="UNLOADING — PUMP REV (CCW)", text_color=ACCENT_ORG)
        self._btn_load.configure(state="disabled")
        self._btn_unload.configure(state="disabled")
        self._btn_pump_stop.configure(state="normal")
        self._log("PUMP REV (CCW) — water unloading initiated")

    def _pump_stop(self):
        self._pump_state = "IDLE"
        pwm_pump.stop()
        gpio_out(PUMP_EN,  False)
        gpio_out(PUMP_DIR, False)
        self._pump_dot.configure(text_color=TEXT_DIM)
        self._pump_status_lbl.configure(text="○  IDLE", text_color=TEXT_DIM)
        self._btn_load.configure(state="normal")
        self._btn_unload.configure(state="normal")
        self._btn_pump_stop.configure(state="disabled")
        self._log("PUMP STOP — water flow halted")

    # ══════════════════════════════════════════════════════════════════════════
    # EXPORT + SHUTDOWN
    # ══════════════════════════════════════════════════════════════════════════
    def _export_logs(self):
        fname = f"pathfinder_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(fname, "w") as f:
                f.write(self.terminal.get("1.0", "end"))
            self._log(f"LOGS EXPORTED → {fname}")
        except Exception as e:
            self._log(f"EXPORT FAILED: {e}")

    def _on_close(self):
        self._stop_event.set()
        self._mission_running = False
        for p in [pwm_water, pwm_grow, pwm_fan, pwm_led, pwm_pump]:
            try: p.stop()
            except: pass
        if GPIO_AVAILABLE:
            for pin in [PUMP_EN, PUMP_DIR, PUMP_CLK,
                        WATER_HEAT_PIN, GROW_HEAT_PIN, FAN_PIN, LED_PIN]:
                try: GPIO.output(pin, GPIO.LOW)
                except: pass
            try: GPIO.cleanup()
            except: pass
        self.destroy()


if __name__ == "__main__":
    app = ProfessionalOBCDashboard()
    app.mainloop()
