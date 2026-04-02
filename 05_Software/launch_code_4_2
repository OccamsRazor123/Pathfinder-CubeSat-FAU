#Code with implementation of PID and pump hum fix

import time
import board
import math
import csv
import os
import sys
import json
import RPi.GPIO as GPIO
import adafruit_scd4x
import adafruit_veml7700
import adafruit_bme280.basic as adafruit_bme280
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- CONFIGURATION ---
# Climate Thresholds
TEMP_THRESHOLD_LOW = 20.0   
TEMP_THRESHOLD_HIGH = 22.0  
WATER_TEMP_LOW = 20.0       

# PID Tuning Parameters 
HEATER_KP = 20.0  # Proportional Gain
HEATER_KI = 0.5   # Integral Gain 
HEATER_KD = 5.0   # Derivative Gain
MAX_HEATER_POWER = 25 # Max of 25% duty for heaters

# Humidity Thresholds
RH_THRESHOLD_HIGH = 60.0 
RH_P_BAND = 10.0 # Humidity % over threshold to reach 100% fan power

# Biological Lighting Targets (Daily Light Integral)
DAY_CYCLE_SECONDS = 120  
TARGET_LUX_HOURS = 1     
TARGET_LUX_SECONDS = TARGET_LUX_HOURS * 3600 
MAX_LED_DUTY = 100.0 

# Fluid Delivery Targets
TARGET_DAILY_VOLUME_UL = 88.0 
PUMP_FLOW_RATE_UL_MIN = 88.0  

# Thermistor Calibrations
R_FIXED = 20000.0    
R_NOMINAL = 20000.0  
B_COEFFICIENT = 3950.0 
V_IN = 3.3             
LUX_CORRECTION = 0.88  

# --- GPIO SETUP (Unified RPi.GPIO) ---
WATER_HEAT_PIN = 17 
GROW_HEAT_PIN = 27  
FAN_PIN = 24        
LED_PIN = 25        
PUMP_CLK = 18       
PUMP_EN = 23        
PUMP_DIR = 16       

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

pins_to_setup = [WATER_HEAT_PIN, GROW_HEAT_PIN, FAN_PIN, LED_PIN, PUMP_CLK, PUMP_EN, PUMP_DIR]
for pin in pins_to_setup:
    GPIO.setup(pin, GPIO.OUT)

GPIO.output(PUMP_EN, GPIO.LOW) 

pwm_water = GPIO.PWM(WATER_HEAT_PIN, 100)
pwm_grow = GPIO.PWM(GROW_HEAT_PIN, 100)
pwm_fan = GPIO.PWM(FAN_PIN, 100)
pwm_led = GPIO.PWM(LED_PIN, 1000) 
pwm_pump = GPIO.PWM(PUMP_CLK, 4000) 

pwm_water.start(0)
pwm_grow.start(0)
pwm_fan.start(0)
pwm_led.start(0)

i2c = board.I2C() 

# --- PID CONTROLLER CLASS ---
class PIDController:
    def __init__(self, kp, ki, kd, setpoint, out_min=0.0, out_max=100.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.out_min = out_min
        self.out_max = out_max
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()

    def compute(self, current_value):
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0.0:
            dt = 0.01

        error = self.setpoint - current_value
        self.integral += error * dt
        self.integral = max(min(self.integral, self.out_max), self.out_min)
        derivative = (error - self.last_error) / dt
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        self.last_error = error
        self.last_time = current_time

        return max(self.out_min, min(self.out_max, output))
        
    def reset_integral(self):
        self.integral = 0.0

def setup_sensors():
    sensors = {'scd': None, 'bme': None, 'veml': None, 'ads_chan': None}
    print("\n--- Initializing I2C Hardware ---")
    try:
        sensors['scd'] = adafruit_scd4x.SCD4X(i2c)
        sensors['scd'].start_periodic_measurement()
        print(" [OK] SCD40 CO2 Sensor")
    except Exception as e: print(f" [FAIL] SCD40: {e}")
    try:
        for addr in [0x77, 0x76]:
            try:
                sensors['bme'] = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=addr)
                print(f" [OK] BME280 Environment Sensor ({hex(addr)})")
                break
            except: continue
    except Exception as e: print(f" [FAIL] BME280: {e}")
    try:
        sensors['veml'] = adafruit_veml7700.VEML7700(i2c)
        print(" [OK] VEML7700 Lux Sensor")
    except Exception as e: print(f" [FAIL] VEML7700: {e}")
    try:
        ads = ADS.ADS1115(i2c)
        sensors['ads_chan'] = AnalogIn(ads, 0)
        print(" [OK] ADS1115 ADC/Thermistor")
    except Exception as e: print(f" [FAIL] ADS1115: {e}")
    return sensors

def log_to_csv(filename, data):
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "CO2_ppm", "BME_Temp_C", "BME_RH", "Pressure_hPa", "Lux", "Thermistor_C", "Grow_Heat_%", "Water_Heat_%", "Fans_%", "LEDs_%", "Pump_Active", "Accum_Lux_Hrs"])
        writer.writerow(data)

def save_mission_state(filename, day_start, lux_sec, dose_delivered):
    state = {
        "day_start_time": day_start,
        "accumulated_lux_seconds": lux_sec,
        "daily_dose_delivered": dose_delivered
    }
    temp_file = filename + ".tmp"
    try:
        with open(temp_file, 'w') as f:
            json.dump(state, f)
        os.replace(temp_file, filename) 
    except Exception as e:
        pass 

def load_mission_state(filename, cycle_seconds):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            if time.time() - state["day


