"""
conops_modes.py
This file defines the logic for each CONOPS (Concept of Operations) mode.
Each function is called by main.py when the satellite is in that specific mode.
"""

import time
import hardware_drivers
import global_config
import system_health

# --- Global Timer Variables for Image Capture ---
last_image_time = 0
IMAGE_INTERVAL = 300  # 300 seconds = 5 minutes

def handle_startup(system_state):
    """
    Mode 1: STARTUP
    Runs once on boot. Performs Power-On Self-Test (POST).
    """
    print("[Mode] STARTUP: Running Power-On Self-Tests...")
    
    # Check sensors, memory, etc.
    sensors_ok = hardware_drivers.check_all_sensors()
    memory_ok = hardware_drivers.check_memory()
    
    if sensors_ok and memory_ok:
        print("[Mode] STARTUP: POST successful.")
        system_state["current_mode"] = "INITIALIZE"
    else:
        print("[Mode] STARTUP: POST FAILED. Entering SAFE_MODE.")
        system_state["current_mode"] = "SAFE_MODE"


def handle_initialize(system_state):
    """
    Mode 2: INITIALIZE
    Runs once after STARTUP. Powers on essential components
    and transitions to the default idle state (SAFE_MODE).
    """
    print("[Mode] INITIALIZE: Powering on essential systems...")
    hardware_drivers.power_on_comms_receiver()
    hardware_drivers.power_on_adcs_systems()
    
    # Default to SAFE_MODE to wait for ground commands or scheduled events
    print("[Mode] INITIALIZE: Init complete. Entering SAFE_MODE.")
    system_state["current_mode"] = "SAFE_MODE"


def handle_safe_mode(system_state):
    """
    Mode 3: SAFE_MODE
    This is the default "idle" state.
    - Power-positive (all non-essential systems off)
    - Maintain critical systems (payload survival temps)
    - Listen for commands from ground
    """
    print_once(system_state, "[Mode] SAFE_MODE: System idle. Listening for commands.")
    
    # Per PAY-1, we must keep plants alive. Run thermal control.
    system_health.run_payload_thermal_control(system_state)
    
    # Check for commands from ground (this is a mock function)
    cmd = hardware_drivers.check_for_gnd_command()
    if cmd == "START_EXPERIMENT":
        print("[Mode] SAFE_MODE: Received START_EXPERIMENT command.")
        # As per PAY-3, we must heat water *before* saturation.
        system_state["current_mode"] = "PRE_EXPERIMENT_HEATING"
    elif cmd == "REQUEST_TRANSMIT":
        print("[Mode] SAFE_MODE: Received REQUEST_TRANSMIT command.")
        system_state["current_mode"] = "TRANSMIT_MODE"


def handle_pre_experiment_heating(system_state):
    """
    Mode 4: PRE_EXPERIMENT_HEATING
    As per PAY-3, "water temperature... shall be greater than 15°C
    before initial water saturation."
    """
    print_once(system_state, "[Mode] PRE_EXPERIMENT: Heating water...")
    
    water_temp = system_state["payload_temps"]["water"]
    
    if water_temp < global_config.MIN_WATER_TEMP:
        hardware_drivers.set_heater(global_config.WATER_HEATER, "ON")
    else:
        print(f"[Mode] PRE_EXPERIMENT: Water is at {water_temp}°C. Ready for saturation.")
        hardware_drivers.set_heater(global_config.WATER_HEATER, "OFF")
        system_state["current_mode"] = "WATER_SATURATION"


def handle_water_saturation(system_state):
    """
    Mode 5: WATER_SATURATION
    As per PAY-1, this "denotes the start of the experiment."
    This mode runs the pump to saturate the plant pillows.
    """
    print("[Mode] WATER_SATURATION: Saturating plant pillows...")
    
    # Run the pump for a configured amount of time
    hardware_drivers.run_pump(duration_sec=global_config.SATURATION_TIME_SEC)
    
    print("[Mode] WATER_SATURATION: Complete.")
    system_state["experiment_start_time"] = time.time()
    system_state["current_mode"] = "EXPERIMENT_MODE"


def handle_experiment_mode(system_state):
    """
    Mode 6: EXPERIMENT_MODE
    The main mission.
    - Run payload thermal control (MO-1)
    - Run LED light cycles (PAY-4)
    - Image growth chamber (MO-3)
    """
    global last_image_time  # We need to access the global timer

    print_once(system_state, "[Mode] EXPERIMENT: Running main science mission.")
    
    # 1. Run thermal control (MO-1)
    system_health.run_payload_thermal_control(system_state)
    
    # 2. Run LED cycles (PAY-4: "16 hours on and 8 hours off")
    time_since_start = time.time() - system_state["experiment_start_time"]
    day_cycle_time = time_since_start % (24 * 3600) # Time in seconds into a 24-hr cycle
    
    if day_cycle_time < (16 * 3600): # First 16 hours
        hardware_drivers.set_leds("ON")
    else: # Last 8 hours
        hardware_drivers.set_leds("OFF")
        
    # 3. Check Image Timer (Fixed for Data Budget)
    current_time = time.time()
    
    # Only take a picture if 300 seconds (5 mins) have passed
    if (current_time - last_image_time) >= IMAGE_INTERVAL:
        print(f"[Mode] EXPERIMENT: Timer hit ({IMAGE_INTERVAL}s). Capturing image.")
        hardware_drivers.capture_image()
        last_image_time = current_time  # Reset the timer
    
    # This mode runs until the experiment duration is over
    if time_since_start > global_config.EXPERIMENT_DURATION_SEC:
        print("[Mode] EXPERIMENT: Experiment duration complete. Returning to SAFE_MODE.")
        hardware_drivers.set_leds("OFF")
        system_state["current_mode"] = "SAFE_MODE"


def handle_transmit_mode(system_state):
    """
    Mode 7: TRANSMIT_MODE
    Powers on the high-gain antenna and transmitter to downlink
    sensor and image data.
    """
    print_once(system_state, "[Mode] TRANSMIT: Powering on transmitter.")
    hardware_drivers.power_on_comms_transmitter()
    
    print("[Mode] TRANSMIT: Downlinking data...")
    hardware_drivers.downlink_data_buffer()
    
    print("[Mode] TRANSMIT: Downlink complete. Returning to SAFE_MODE.")
    hardware_drivers.power_off_comms_transmitter()
    system_state["current_mode"] = "SAFE_MODE"


def handle_last_resort_mode(system_state):
    """
    Mode 8: LAST_RESORT_MODE (triggered by system_health)
    Per EPS-2. Critical power failure.
    - Turn off ALL non-essential components, including payload.
    - Orient for maximum sun (ADCS)
    - Wait for power to recover.
    """
    print_once(system_state, "[Mode] LAST_RESORT: CRITICAL POWER. Shutting down non-essentials.")
    
    # This is a "hard-power-off" command
    hardware_drivers.power_off_all_non_essential()
    
    # The system_health module will be responsible for checking
    # if voltage has recovered and can move back to SAFE_MODE.


# --- Utility Function ---

def print_once(system_state, message):
    """
    Helper function to print a message only once when entering a mode.
    """
    if system_state["current_mode"] != system_state["last_mode"]:
        print(message)
        system_state["last_mode"] = system_state["current_mode"]