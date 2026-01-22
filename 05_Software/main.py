"""
FAU RVM - Main Flight Software (GNC/Software Team)
main.py
"""
import time
import copy  # IMPORTANT: Needed to send data safely to the GUI
import conops_modes
import system_health
import global_config

def run_simulation_loop(data_queue=None, stop_event=None):
    """
    The main loop, refactored to work with threading for the GUI.
    """
    # This dictionary holds the entire "state" of the satellite.
    system_state = {
        "current_mode": "STARTUP",
        "last_mode": "",
        "boot_time": time.time(),
        "experiment_start_time": None,
        "battery_voltage": 0.0,
        "pi_temp": 0.0,
        "payload_temps": {"air": 0.0, "substrate": 0.0, "water": 0.0},
        "soil_moisture": 0.0,
        "humidity": 0.0,
        "gnd_command_received": None, 
    }

    print("--- Pathfinder Flight Software Initializing ---")

    # Main Loop: Runs until the stop_event is set (when you close the GUI)
    while not (stop_event and stop_event.is_set()):
        
        # 1. --- CHECK SYSTEM HEALTH ---
        try:
            system_health.check_all_systems(system_state)
        except Exception as e:
            print(f"CRITICAL ERROR in system_health: {e}")
            system_state["current_mode"] = "SAFE_MODE" 

        # 2. --- EXECUTE STATE LOGIC ---
        current_mode = system_state["current_mode"]
        try:
            if current_mode == "STARTUP": conops_modes.handle_startup(system_state)
            elif current_mode == "INITIALIZE": conops_modes.handle_initialize(system_state)
            elif current_mode == "SAFE_MODE": conops_modes.handle_safe_mode(system_state)
            elif current_mode == "PRE_EXPERIMENT_HEATING": conops_modes.handle_pre_experiment_heating(system_state)
            elif current_mode == "WATER_SATURATION": conops_modes.handle_water_saturation(system_state)
            elif current_mode == "EXPERIMENT_MODE": conops_modes.handle_experiment_mode(system_state)
            elif current_mode == "TRANSMIT_MODE": conops_modes.handle_transmit_mode(system_state)
            elif current_mode == "LAST_RESORT_MODE": conops_modes.handle_last_resort_mode(system_state)
            else: system_state["current_mode"] = "SAFE_MODE"
        except Exception as e:
            print(f"ERROR: {e}")
            system_state["current_mode"] = "SAFE_MODE"

        # 3. --- GUI UPDATE ---
        if data_queue:
            data_queue.put(copy.deepcopy(system_state))

        # 4. --- DELAY ---
        time.sleep(global_config.MAIN_LOOP_DELAY)

    print("--- Flight Software Stopping ---")

if __name__ == "__main__":
    run_simulation_loop()