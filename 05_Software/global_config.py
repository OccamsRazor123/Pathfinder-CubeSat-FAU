"""
global_config.py
This file stores all system-wide configuration constants.
This makes it easy to "tune" the software without digging
through all the logic files.
"""

# --- System ---
MAIN_LOOP_DELAY = 1.0  # seconds. The "heartbeat" of the main loop.

# --- Power Thresholds (Ref: EPS-2, EPS-3) ---
LAST_RESORT_VOLTAGE = 3.3  # Volts. Below this, enter LAST_RESORT_MODE.
SAFE_MODE_VOLTAGE = 3.5    # Volts. Below this, shed load and enter SAFE_MODE.
RECOVERED_VOLTAGE = 3.7    # Volts. Above this, system can exit LAST_RESORT.

# --- Thermal Thresholds (Ref: PAY-1, PAY-2, PAY-3) ---
# PAY-1: Absolute survival range
MIN_PLANT_TEMP = 15.0  # °C
MAX_PLANT_TEMP = 40.0  # °C
# PAY-2: Optimal range (our target)
IDEAL_PLANT_TEMP_MIN = 20.0  # °C
IDEAL_PLANT_TEMP_MAX = 25.0  # °C
# PAY-3: Water temp
MIN_WATER_TEMP = 15.0  # °C
# OBC Temp
MAX_PI_TEMP = 80.0     # °C

# --- CONOPS Timings (Ref: PAY-4) ---
SATURATION_TIME_SEC = 30       # How long to run the pump
LED_ON_TIME_SEC = 16 * 3600    # 16 hours
LED_OFF_TIME_SEC = 8 * 3600    # 8 hours
IMAGE_INTERVAL_SEC = 1 * 3600  # Take a picture every 1 hour
EXPERIMENT_DURATION_SEC = 14 * 24 * 3600 # 14 days

# --- Hardware IDs (for hardware_drivers.py) ---
# Sensor IDs
AIR_TEMP_SENSOR = "temp_sensor_air"
WATER_TEMP_SENSOR = "temp_sensor_water"
SUBSTRATE_TEMP_SENSOR = "temp_sensor_substrate"
PI_TEMP_SENSOR = "temp_sensor_pi"

# Actuator IDs
AIR_HEATER = "heater_air"
WATER_HEATER = "heater_water"
