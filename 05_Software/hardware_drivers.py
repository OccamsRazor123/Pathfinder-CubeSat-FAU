"""
hardware_drivers.py
This is the "Hardware Abstraction Layer" (HAL).
"""
import random
import global_config

# --- INTERNAL SIMULATION STATE ---
# These variables simulate the physical reality of the satellite
_heater_states = {
    global_config.AIR_HEATER: "OFF", 
    global_config.WATER_HEATER: "OFF"
}
_mock_water_temp = 12.0  # Start cold

# --- Self-Test Functions ---
def check_all_sensors():
    print("[Mock HW] Checking all sensors... OK.")
    return True

def check_memory():
    print("[Mock HW] Checking memory... OK.")
    return True

# --- Power/System Functions ---
def power_on_comms_receiver():
    print("[Mock HW] Comms receiver powered ON.")

def power_on_adcs_systems():
    print("[Mock HW] ADCS systems powered ON.")

def power_on_comms_transmitter():
    print("[Mock HW] Comms transmitter (high power) powered ON.")
    
def power_off_comms_transmitter():
    print("[Mock HW] Comms transmitter powered OFF.")

def power_off_all_non_essential():
    print("[Mock HW] CRITICAL: Powering off all non-essential systems.")
    set_heater(global_config.AIR_HEATER, "OFF")
    set_heater(global_config.WATER_HEATER, "OFF")
    set_leds("OFF")

# --- Sensor Read Functions ---
def read_voltage_sensor():
    return 3.8 + random.uniform(-0.1, 0.1) 

def read_temp_sensor(sensor_id):
    # Simulate Real Physics!
    
    # 1. Handle Water Temp (Dynamic)
    if sensor_id == global_config.WATER_TEMP_SENSOR:
        global _mock_water_temp
        
        # If heater is ON, temperature rises
        if _heater_states[global_config.WATER_HEATER] == "ON":
            _mock_water_temp += 0.5  # Heat up by 0.5 deg per second
            
        # If heater is OFF, it slowly cools down (simplified)
        else:
            if _mock_water_temp > 12.0:
                _mock_water_temp -= 0.1
                
        return _mock_water_temp

    # 2. Handle Air Temp (Random fluctuation)
    else:
        return 22.0 + random.uniform(-0.5, 0.5)

# --- Actuator Control Functions ---
def set_heater(heater_id, status):
    # Update our internal state so the sensor knows to heat up
    global _heater_states
    _heater_states[heater_id] = status
    print(f"[Mock HW] Setting heater {heater_id} to {status}")

def set_leds(status):
    print(f"[Mock HW] Setting LEDs to {status}")

def run_pump(duration_sec):
    print(f"[Mock HW] Running pump for {duration_sec} seconds...")
    # We do NOT sleep here, or the GUI would freeze!
    
def capture_image():
    print(f"[Mock HW] Triggering camera. Saving image to disk.")
    
# --- Comms Functions ---
def check_for_gnd_command():
    # Force the start command for testing
    return "START_EXPERIMENT" 

def downlink_data_buffer():
    print(f"[Mock HW] Beginning data downlink... [||||||||||] Complete.")