import tkinter as tk
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections
from datetime import datetime
import threading
import random
import time

# --- THEME SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ProfessionalOBCDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PATHFINDER GROUND SEGMENT | OBC TERMINAL")
        self.geometry("1280x800")
        
        # Mission Timing & Data Buffering
        self.start_time = datetime.now()
        self.temp_history = collections.deque([22.0]*50, maxlen=50)
        self.time_steps = list(range(50))

        self.grid_columnconfigure(0, weight=0) 
        self.grid_columnconfigure(1, weight=3) 
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="COMMAND", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkButton(self.sidebar, text="EXPORT LOGS", fg_color="#2ecc71").pack(pady=10, padx=20)
        
        # --- HEADER / MISSION ELAPSED TIME ---
        self.header = ctk.CTkFrame(self, height=50, fg_color="#1e1e1e")
        self.header.grid(row=0, column=1, sticky="new", padx=20, pady=(20, 0))
        
        # Updated Label per your request
        self.met_lbl = ctk.CTkLabel(self.header, text="Mission Elapsed Time (MET): 00:00:00", 
                                    font=("Consolas", 18, "bold"), text_color="cyan")
        self.met_lbl.pack(side="left", padx=20)
        
        # --- MAIN CONTAINER ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=20, pady=(80, 20), sticky="nsew")
        self.main_container.grid_columnconfigure((0, 1), weight=1)
        self.main_container.grid_rowconfigure((0, 1), weight=1)

        # PANEL 1: ENVIRONMENTAL DATA
        self.env_panel = self.create_panel(self.main_container, "ENVIRONMENTAL DATA", 0, 0)
        self.temp_lbl, self.temp_bar = self.create_parameter(self.env_panel, "AIR TEMP", "0.0°C", 40, "cyan")
        self.co2_lbl, self.co2_bar = self.create_parameter(self.env_panel, "CO2 CONC", "0 ppm", 2000, "#2ecc71")
        self.lux_lbl, self.lux_bar = self.create_parameter(self.env_panel, "LUMINOSITY", "0 lux", 1000, "#f1c40f")
        self.pres_lbl, self.pres_bar = self.create_parameter(self.env_panel, "PRESSURE", "0 hPa", 1100, "#9b59b6")

        # PANEL 2: SUBSYSTEM HEALTH
        self.pwr_panel = self.create_panel(self.main_container, "SUBSYSTEM HEALTH", 0, 1)
        self.heater_led = self.create_status_light(self.pwr_panel, "THERMAL STRIPS", "#f1c40f")
        self.pump_led = self.create_status_light(self.pwr_panel, "FLUID PUMP", "#3498db")
        self.fan_led = self.create_status_light(self.pwr_panel, "COOLING FANS", "#1abc9c")
        self.led_status = self.create_status_light(self.pwr_panel, "SYSTEM LEDs", "#ecf0f1")

        # PANEL 3: GRAPHING
        self.graph_panel = self.create_panel(self.main_container, "MISSION TIMELINE (TEMP)", 1, 0)
        self.fig = Figure(figsize=(5, 3), dpi=100, facecolor='#2b2b2b')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.set_xlabel("Time (Seconds)", color='white', fontsize=9)
        self.ax.set_ylabel("Temp (°C)", color='white', fontsize=9)
        self.line, = self.ax.plot(self.time_steps, self.temp_history, color='cyan', linewidth=2)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # PANEL 4: TERMINAL
        self.term_panel = self.create_panel(self.main_container, "UPLINK/DOWNLINK RAW", 1, 1)
        self.terminal = tk.Text(self.term_panel, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10), borderwidth=0)
        self.terminal.pack(fill="both", expand=True, padx=10, pady=10)

        threading.Thread(target=self.mission_simulator, daemon=True).start()

    def create_panel(self, master, title, row, col):
        frame = ctk.CTkFrame(master, border_width=1, border_color="#444")
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=("Arial", 12, "bold"), text_color="gray").pack(pady=5)
        return frame

    def create_parameter(self, master, name, val_text, max_val, color):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(container, text=name, font=("Arial", 10)).pack(side="left")
        val_lbl = ctk.CTkLabel(container, text=val_text, font=("Arial", 12, "bold"), text_color=color)
        val_lbl.pack(side="right")
        bar = ctk.CTkProgressBar(master, height=6, progress_color=color)
        bar.pack(fill="x", padx=15, pady=(0, 8))
        bar.set(0.0)
        return val_lbl, (bar, max_val)

    def create_status_light(self, master, name, on_color):
        container = ctk.CTkFrame(master, fg_color="transparent")
        container.pack(fill="x", padx=15, pady=4)
        light = ctk.CTkLabel(container, text="●", font=("Arial", 24), text_color="#333")
        light.pack(side="left")
        ctk.CTkLabel(container, text=name, font=("Arial", 11)).pack(side="left", padx=10)
        return {"light": light, "on_color": on_color}

    def mission_simulator(self):
        c_temp, c_co2, c_lux, c_pres = 22.0, 450, 800, 1013.25
        while True:
            c_temp += random.uniform(-0.3, 0.3)
            c_co2 += random.randint(-2, 5)
            c_lux += random.randint(-10, 10)
            c_pres += random.uniform(-0.1, 0.1)
            
            sim_data = {
                "temp_scd": c_temp, "co2": c_co2, "lux": c_lux, "pressure": c_pres,
                "Heater_State": "ON" if c_temp < 20.0 else "OFF",
                "Pump_State": "ON" if (int(time.time()) % 15 < 3) else "OFF",
                "Fan_State": "ON" if c_temp > 24.0 else "OFF",
                "LED_State": "ON" if c_lux < 500 else "OFF"
            }
            self.after(0, self.update_display, sim_data)
            time.sleep(1)

    def update_display(self, data):
        elapsed = datetime.now() - self.start_time
        self.met_lbl.configure(text=f"Mission Elapsed Time (MET): {str(elapsed).split('.')[0]}")
        
        updates = [
            (self.temp_lbl, self.temp_bar, data.get('temp_scd', 0), "°C"),
            (self.co2_lbl, self.co2_bar, data.get('co2', 0), " ppm"),
            (self.lux_lbl, self.lux_bar, data.get('lux', 0), " lux"),
            (self.pres_lbl, self.pres_bar, data.get('pressure', 0), " hPa")
        ]
        for lbl, (bar, m), val, unit in updates:
            lbl.configure(text=f"{val:.1f}{unit}" if isinstance(val, float) else f"{val}{unit}")
            bar.set(min(max(val / m, 0), 1.0))

        leds = [
            (self.heater_led, data.get("Heater_State")),
            (self.pump_led, data.get("Pump_State")),
            (self.fan_led, data.get("Fan_State")),
            (self.led_status, data.get("LED_State"))
        ]
        for led_obj, state in leds:
            led_obj["light"].configure(text_color=led_obj["on_color"] if state == "ON" else "#333")
        
        self.temp_history.append(data.get('temp_scd', 0))
        self.line.set_ydata(self.temp_history)
        self.ax.relim(); self.ax.autoscale_view(); self.canvas.draw()
        
        self.terminal.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] RX PKT: T={data.get('temp_scd'):.1f} | MET={str(elapsed).split('.')[0]}\n")
        self.terminal.see("end")

if __name__ == "__main__":
    app = ProfessionalOBCDashboard()
    app.mainloop()
