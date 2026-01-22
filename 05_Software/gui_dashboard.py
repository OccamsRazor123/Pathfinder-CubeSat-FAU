"""
gui_dashboard.py
This file creates a simple Tkinter GUI to monitor the
state of the flight software simulation (main.py).

It runs the simulation in a separate thread and displays
the live data it receives on a "red/yellow/green" dashboard.
"""

import tkinter as tk
from tkinter import font
import threading
import queue
import time

# Import the simulation loop and config from your existing files
import main
import global_config

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pathfinder Flight Software - SITL Dashboard")
        self.root.geometry("600x450")
        
        # Set up a professional-looking theme
        self.root.configure(bg="#2E2E2E")
        self.primary_font = font.Font(family="Helvetica", size=12)
        self.title_font = font.Font(family="Helvetica", size=16, weight="bold")
        self.label_color = "#FFFFFF"
        self.bg_color = "#2E2E2E"
        self.frame_color = "#3E3E3E"

        # This queue is used to pass the 'system_state' dict
        # from the simulation thread to this GUI thread.
        self.data_queue = queue.Queue()
        
        # This event is used to tell the simulation thread to stop
        self.stop_event = threading.Event()

        self.create_widgets()
        
        # Start the simulation in a new thread
        self.start_simulation()
        
        # Start the GUI's own update loop
        self.update_gui()
        
        # Set the protocol for closing the window
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Builds the main GUI layout."""
        
        # --- Main Title ---
        title_label = tk.Label(self.root, text="Pathfinder Mission Dashboard", font=self.title_font, bg=self.bg_color, fg=self.label_color, pady=10)
        title_label.pack()

        # --- System State Frame ---
        state_frame = tk.Frame(self.root, bg=self.frame_color, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        state_frame.pack(fill="x", padx=10, pady=5)
        
        self.state_vars = {
            "Current Mode": tk.StringVar(value="--"),
            "Battery Voltage": tk.StringVar(value="-- V"),
            "Pi Temperature": tk.StringVar(value="-- °C"),
            "Air Temperature": tk.StringVar(value="-- °C"),
            "Water Temperature": tk.StringVar(value="-- °C"),
            "Air Heater": tk.StringVar(value="--"),
            "LEDs": tk.StringVar(value="--"),
        }
        
        # Create labels in a grid
        tk.Label(state_frame, text="Current Mode:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["Current Mode"], font=self.primary_font, bg=self.frame_color, fg="#00FF00").grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(state_frame, text="Battery Voltage:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["Battery Voltage"], font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(state_frame, text="Pi Temperature:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["Pi Temperature"], font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(state_frame, text="Air Temperature:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["Air Temperature"], font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=3, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(state_frame, text="Water Temperature:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=4, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["Water Temperature"], font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=4, column=1, sticky="w", padx=5, pady=2)

        tk.Label(state_frame, text="Air Heater:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=5, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["Air Heater"], font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=5, column=1, sticky="w", padx=5, pady=2)

        tk.Label(state_frame, text="LEDs:", font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=6, column=0, sticky="w", padx=5, pady=2)
        tk.Label(state_frame, textvariable=self.state_vars["LEDs"], font=self.primary_font, bg=self.frame_color, fg=self.label_color).grid(row=6, column=1, sticky="w", padx=5, pady=2)

        # --- Status Light Frame ---
        status_frame = tk.Frame(self.root, bg=self.frame_color, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(status_frame, text="System Health Status", font=self.title_font, bg=self.frame_color, fg=self.label_color).pack()
        
        self.status_lights = {}
        light_frame = tk.Frame(status_frame, bg=self.frame_color)
        light_frame.pack(pady=10)

        for i, (name, text) in enumerate([("voltage", "Battery OK"), ("pi_temp", "Pi Temp OK"), ("air_temp", "Air Temp OK"), ("water_temp", "Water Temp OK")]):
            canvas = tk.Canvas(light_frame, width=20, height=20, bg=self.frame_color, bd=0, highlightthickness=0)
            # Draw a grey circle by default
            canvas.create_oval(2, 2, 18, 18, fill="grey", outline="grey", tags="status_light")
            canvas.grid(row=0, column=i*2, padx=(10, 2))
            
            label = tk.Label(light_frame, text=text, font=self.primary_font, bg=self.frame_color, fg=self.label_color)
            label.grid(row=0, column=i*2+1, padx=(0, 10))
            
            # Store the canvas so we can change its color
            self.status_lights[name] = canvas

    def start_simulation(self):
        """Starts the main.run_simulation_loop in a new daemon thread."""
        print("[GUI] Starting simulation thread...")
        self.sim_thread = threading.Thread(
            target=main.run_simulation_loop,
            args=(self.data_queue, self.stop_event),
            daemon=True  # Daemon threads exit when the main program exits
        )
        self.sim_thread.start()

    def update_gui(self):
        """Periodically checks the queue for new data and updates the GUI."""
        try:
            # Check for new data from the simulation thread
            # Use a loop to clear the queue and get the *latest* state
            while not self.data_queue.empty():
                system_state = self.data_queue.get_nowait()
                self.process_system_state(system_state)

        except queue.Empty:
            # No new data, that's fine
            pass
        
        # Schedule this function to run again after 100ms
        self.root.after(100, self.update_gui)

    def process_system_state(self, state):
        """Updates all GUI elements with the new system_state data."""
        
        # --- Update Labels ---
        self.state_vars["Current Mode"].set(state["current_mode"])
        self.state_vars["Battery Voltage"].set(f"{state['battery_voltage']:.2f} V")
        self.state_vars["Pi Temperature"].set(f"{state['pi_temp']:.1f} °C")
        self.state_vars["Air Temperature"].set(f"{state['payload_temps']['air']:.1f} °C")
        self.state_vars["Water Temperature"].set(f"{state['payload_temps']['water']:.1f} °C")
        
        # Check heater status (this is a bit of a hack, but works for mock)
        # In a real system, you'd have a state variable for this
        if state['payload_temps']['air'] < global_config.IDEAL_PLANT_TEMP_MIN:
             self.state_vars["Air Heater"].set("ON")
        elif state['payload_temps']['air'] > global_config.IDEAL_PLANT_TEMP_MAX:
             self.state_vars["Air Heater"].set("OFF")
        
        # Check LED status
        if state["current_mode"] == "EXPERIMENT_MODE":
             # This logic is from conops_modes.py
             if state["experiment_start_time"]:
                time_since_start = time.time() - state["experiment_start_time"]
                day_cycle_time = time_since_start % (24 * 3600)
                if day_cycle_time < (16 * 3600):
                    self.state_vars["LEDs"].set("ON")
                else:
                    self.state_vars["LEDs"].set("OFF")
             else:
                self.state_vars["LEDs"].set("OFF") # Should not happen
        else:
            self.state_vars["LEDs"].set("OFF")


        # --- Update Status Lights ---
        
        # Voltage Status
        v = state['battery_voltage']
        if v < global_config.LAST_RESORT_VOLTAGE:
            self.set_status_light("voltage", "red")
        elif v < global_config.SAFE_MODE_VOLTAGE:
            self.set_status_light("voltage", "yellow")
        else:
            self.set_status_light("voltage", "green")

        # Pi Temp Status
        pt = state['pi_temp']
        if pt > global_config.MAX_PI_TEMP:
            self.set_status_light("pi_temp", "red")
        elif pt > global_config.MAX_PI_TEMP - 10: # 10C warning margin
             self.set_status_light("pi_temp", "yellow")
        else:
            self.set_status_light("pi_temp", "green")
            
        # Air Temp Status
        at = state['payload_temps']['air']
        if (at < global_config.MIN_PLANT_TEMP or 
            at > global_config.MAX_PLANT_TEMP):
            self.set_status_light("air_temp", "red") # Survival limit breach
        elif (at < global_config.IDEAL_PLANT_TEMP_MIN or
              at > global_config.IDEAL_PLANT_TEMP_MAX):
            self.set_status_light("air_temp", "yellow") # Outside optimal
        else:
            self.set_status_light("air_temp", "green") # In optimal range

        # Water Temp Status (for pre-heating)
        wt = state['payload_temps']['water']
        if state['current_mode'] == "PRE_EXPERIMENT_HEATING":
            if wt < global_config.MIN_WATER_TEMP:
                self.set_status_light("water_temp", "yellow") # Heating...
            else:
                self.set_status_light("water_temp", "green") # Ready
        else:
             self.set_status_light("water_temp", "green") # Not a concern
            
    def set_status_light(self, name, color):
        """Changes the color of a specific status light."""
        canvas = self.status_lights.get(name)
        if canvas:
            canvas.itemconfig("status_light", fill=color, outline=color)

    def on_closing(self):
        """Called when the user clicks the 'X' button."""
        print("[GUI] Closing application...")
        
        # Signal the simulation thread to stop
        self.stop_event.set()
        
        # Wait for the thread to finish (optional, but good practice)
        # self.sim_thread.join() 
        
        # Close the GUI
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()