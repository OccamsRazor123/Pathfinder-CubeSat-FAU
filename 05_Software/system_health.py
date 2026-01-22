"""
system_health.py
This module is responsible for two things:
1. `check_all_systems()`: Reading all sensors and checking for faults
   that would force a mode change (e.g., low battery -> LAST_RESORT_MODE).
2. `run_payload_thermal_control()`: The thermostat logic for the plants.
"""

import hardware_drivers
import global_config

def check_all_systems(system_state):
    """
    Reads all critical health sensors and updates system_state.
    This function can FORCE a mode change if a fault is detected.
    """
    
    # 1. Read Health Sensors
    system_state["battery_voltage"] = hardware_drivers.read_voltage_sensor()
    system_state["pi_temp"] = hardware_drivers.read_temp_sensor(global_config.PI_TEMP_SENSOR)
    
    # 2. Read Payload Sensors
    system_state["payload_temps"]["air"] = hardware_drivers.read_temp_sensor(global_config.AIR_TEMP_SENSOR)
    system_state["payload_temps"]["water"] = hardware_drivers.read_temp_sensor(global_config.WATER_TEMP_SENSOR)
    
    # 3. Check for Faults
    
    # --- Voltage Faults (Ref: EPS-2)
    current_voltage = system_state["battery_voltage"]
    
    if current_voltage < global_config.LAST_RESORT_VOLTAGE:
        # CRITICAL: This overrides everything
        system_state["current_mode"] = "LAST_RESORT_MODE"
        
    elif current_voltage < global_config.SAFE_MODE_VOLTAGE:
        # Low power, but not critical. Shed load.
        # Don't interrupt startup or a transmit.
        if system_state["current_mode"] in ["EXPERIMENT_MODE", "PRE_EXPERIMENT_HEATING"]:
            print(f"[Health] Low voltage ({current_voltage}V). Forcing SAFE_MODE.")
            system_state["current_mode"] = "SAFE_MODE"
            
    elif current_voltage > global_config.RECOVERED_VOLTAGE:
        # If we were in a low-power state, we can now recover
        if system_state["current_mode"] == "LAST_RESORT_MODE":
            print(f"[Health] Voltage recovered ({current_voltage}V). Returning to SAFE_MODE.")
            system_state["current_mode"] = "SAFE_MODE"

    # --- Temperature Faults
    if system_state["pi_temp"] > global_config.MAX_PI_TEMP:
        print(f"[Health] CRITICAL: Pi overheating ({system_state['pi_temp']}°C). Forcing SAFE_MODE.")
        system_state["current_mode"] = "SAFE_MODE"
        # Add logic to power cycle or shut down if necessary

def run_payload_thermal_control(system_state):
    """
    Thermostat logic to meet MO-1.
    Keeps payload air temp within the "optimal" range (PAY-2).
    """
    air_temp = system_state["payload_temps"]["air"]
    
    # Use the "optimal" range (PAY-2) as the target
    if air_temp < global_config.IDEAL_PLANT_TEMP_MIN:
        # Too cold, turn heater on
        hardware_drivers.set_heater(global_config.AIR_HEATER, "ON")
    elif air_temp > global_config.IDEAL_PLANT_TEMP_MAX:
        # Too hot, turn heater off (passive cooling)
        hardware_drivers.set_heater(global_config.AIR_HEATER, "OFF")
    else:
        # In the sweet spot, turn heater off to save power
        hardware_drivers.set_heater(global_config.AIR_HEATER, "OFF")
