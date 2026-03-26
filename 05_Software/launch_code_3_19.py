import time
import board
import math
import csv
import os
import sys
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
P_BAND = 5.0 # Temperature degrees over threshold to reach max power
MAX_HEATER_POWER = 25 # Max of 25% duty for heaters

# Biological Lighting Targets (Daily Light Integral)
DAY_CYCLE_SECONDS = 120  # (Change to 86400 for a real 24-hour mission)
TARGET_LUX_HOURS = 1     
TARGET_LUX_SECONDS = TARGET_LUX_HOURS * 3600 
MAX_LED_DUTY = 100.0 # Change this to dim the LEDs

# Fluid Delivery Targets
TARGET_DAILY_VOLUME_UL = 88.0 # Total uL to deliver per day cycle
PUMP_FLOW_RATE_UL_MIN = 88.0  # Measured flow rate at current Hz

# Thermistor Calibrations
R_FIXED = 20000.0    
R_NOMINAL = 20000.0  
B_COEFFICIENT = 3950.0 
V_IN = 3.3             
LUX_CORRECTION = 0.88  

# --- GPIO SETUP (Unified RPi.GPIO) ---
WATER_HEAT_PIN = 17 # Physical Pin 11
GROW_HEAT_PIN = 27  # Physical Pin 13
FAN_PIN = 24        # Physical Pin 18
LED_PIN = 25        # Physical Pin 22
PUMP_CLK = 18       # Physical Pin 12 (Hardware PWM)
PUMP_EN = 23        # Physical Pin 16
PUMP_DIR = 16       # Physical Pin 36

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Set all pins as outputs
pins_to_setup = [WATER_HEAT_PIN, GROW_HEAT_PIN, FAN_PIN, LED_PIN, PUMP_CLK, PUMP_EN, PUMP_DIR]
for pin in pins_to_setup:
    GPIO.setup(pin, GPIO.OUT)

GPIO.output(PUMP_EN, GPIO.LOW) # Pump defaults to off

# Initialize PWM Objects
pwm_water = GPIO.PWM(WATER_HEAT_PIN, 100)
pwm_grow = GPIO.PWM(GROW_HEAT_PIN, 100)
pwm_fan = GPIO.PWM(FAN_PIN, 100)
pwm_led = GPIO.PWM(LED_PIN, 1000) 
pwm_pump = GPIO.PWM(PUMP_CLK, 4000) # Running at tested 4000 Hz

# Start all environmental PWMs at 0% Duty Cycle (OFF)
pwm_water.start(0)
pwm_grow.start(0)
pwm_fan.start(0)
pwm_led.start(0)

i2c = board.I2C() 

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

def clamp_pwm(value):
    """Helper function to keep duty cycle strictly between 0.0 and 100.0"""
    return max(0.0, min(100.0, value))

def start_experiment(sensors, filename):
    print(f"\n🚀 MISSION ACTIVE: Logging to {filename}")
    print("Press Ctrl+C to abort and safe all hardware.\n")
    
    print("="*155)
    print(f"{'Timestamp':<10} | {'CO2':<5} | {'Temp':<5} | {'RH%':<5} | {'Press':<7} | {'Lux':<7} | {'Therm_C':<7} | {'G_Heat%':<7} | {'W_Heat%':<7} | {'Fans%':<5} | {'LEDs%':<5} | {'Acc_LuxHr'}")
    print("="*155)

    # Tracking Variables
    pump_is_running = False
    pump_stop_time = 0
    daily_dose_delivered = False # Start false so it feeds on the very first loop
    
    accumulated_lux_seconds = 0.0
    day_start_time = time.time()
    last_loop_time = time.time()

    try:
        while True:
            current_time = time.time()
            dt = current_time - last_loop_time 
            last_loop_time = current_time
            
            timestamp = time.strftime("%H:%M:%S")
            co2 = bme_t = bme_rh = bme_p = lux = therm_t = float('nan')
            
            # Duty Cycle Trackers
            g_heat_dc = w_heat_dc = fan_dc = led_dc = 0.0

            # --- 24-HOUR DAY CYCLE RESET ---
            if current_time - day_start_time >= DAY_CYCLE_SECONDS:
                print("\n🌅 NEW DAY CYCLE STARTED. Resetting light and fluid trackers.")
                accumulated_lux_seconds = 0.0
                daily_dose_delivered = False # Reset the feeding flag for the new day
                day_start_time = current_time

            # --- SENSOR POLLING ---
            if sensors['scd'] and sensors['scd'].data_ready: co2 = sensors['scd'].CO2
            if sensors['bme']:
                bme_t = sensors['bme'].temperature
                bme_rh = sensors['bme'].relative_humidity
                bme_p = sensors['bme'].pressure
            if sensors['veml']: lux = sensors['veml'].lux * LUX_CORRECTION
            if sensors['ads_chan']:
                v_out = sensors['ads_chan'].voltage
                if 0.1 < v_out < (V_IN - 0.1):
                    res = R_FIXED * ((V_IN / v_out) - 1)
                    steinhart = math.log(res / R_NOMINAL) / B_COEFFICIENT
                    steinhart += 1.0 / (25.0 + 273.15)
                    therm_t = (1.0 / steinhart) - 273.15

            # --- BIOLOGICAL LIGHTING LOGIC (PWM) ---
            if accumulated_lux_seconds < TARGET_LUX_SECONDS:
                led_dc = MAX_LED_DUTY
                pwm_led.ChangeDutyCycle(led_dc)
                if not math.isnan(lux) and lux > 0:
                    accumulated_lux_seconds += (lux * dt)
            else:
                led_dc = 0.0
                pwm_led.ChangeDutyCycle(led_dc)

            accumulated_lux_hours = accumulated_lux_seconds / 3600.0

            # --- CLIMATE CONTROL (PROPORTIONAL PWM) ---
            if not math.isnan(bme_t):
                # Calculate Fan Speed (Cools down)
                if bme_t > TEMP_THRESHOLD_HIGH:
                    fan_dc = clamp_pwm(((bme_t - TEMP_THRESHOLD_HIGH) / P_BAND) * 100.0)
                else:
                    fan_dc = 0.0
                
                # Calculate Grow Heater (Warms up)
                if bme_t < TEMP_THRESHOLD_LOW:
                    raw_grow_power = clamp_pwm(((TEMP_THRESHOLD_LOW - bme_t) / P_BAND) * 100.0)
                    g_heat_dc = min(MAX_HEATER_POWER, raw_grow_power) 
                else:
                    g_heat_dc = 0.0

            if not math.isnan(therm_t):
                # Calculate Water Heater (Warms up)
                if therm_t < WATER_TEMP_LOW:
                    raw_power = clamp_pwm(((WATER_TEMP_LOW - therm_t) / P_BAND) * 100.0)
                    w_heat_dc = min(MAX_HEATER_POWER, raw_power) 
                else:
                    w_heat_dc = 0.0

            # Apply the calculated duty cycles to the hardware
            pwm_fan.ChangeDutyCycle(fan_dc)
            pwm_grow.ChangeDutyCycle(g_heat_dc)
            pwm_water.ChangeDutyCycle(w_heat_dc)

            # --- NON-BLOCKING PUMP LOGIC (DAILY SCHEDULE) ---
            if not daily_dose_delivered and not pump_is_running:
                # Math: (88 uL / 88 uL/min) * 60 seconds = 60.0 seconds of run time
                duration_seconds = (TARGET_DAILY_VOLUME_UL / PUMP_FLOW_RATE_UL_MIN) * 60.0
                pump_stop_time = time.time() + duration_seconds
                pump_is_running = True
                daily_dose_delivered = True # Mark as fed for this cycle
                
                print(f"*** DAILY FEEDING: Dispensing {TARGET_DAILY_VOLUME_UL} uL over {duration_seconds:.1f} seconds ***")
                GPIO.output(PUMP_DIR, GPIO.HIGH) # Clockwise
                GPIO.output(PUMP_EN, GPIO.HIGH)  # Enable Driver
                pwm_pump.start(50)               

            if pump_is_running and time.time() >= pump_stop_time:
                pwm_pump.stop()
                GPIO.output(PUMP_EN, GPIO.LOW)
                pump_is_running = False
                print("*** FLUID DISPENSE COMPLETE ***")

            # --- OUTPUT & LOGGING ---
            print(f"{timestamp:<10} | {co2:<5.0f} | {bme_t:<5.1f} | {bme_rh:<5.1f} | {bme_p:<7.1f} | {lux:<7.1f} | {therm_t:<7.2f} | {g_heat_dc:<7.1f} | {w_heat_dc:<7.1f} | {fan_dc:<5.1f} | {led_dc:<5.1f} | {accumulated_lux_hours:<7.1f}")
            log_to_csv(filename, [timestamp, co2, bme_t, bme_rh, bme_p, lux, therm_t, g_heat_dc, w_heat_dc, fan_dc, led_dc, pump_is_running, accumulated_lux_hours])
            
            time.sleep(2) 
            
    except KeyboardInterrupt:
        pwm_grow.stop()
        pwm_water.stop()
        pwm_fan.stop()
        pwm_led.stop()
        pwm_pump.stop()
        GPIO.output(PUMP_EN, GPIO.LOW)
        print("\n🛑 System Standby. All PWM signals terminated and hardware safed.")
        GPIO.cleanup()
        sys.exit()

def main_menu():
    print("\n" + "*"*30)
    print("   CUBESAT PAYLOAD SYSTEM   ")
    print("*"*30)
    
    s = setup_sensors()
    mission_name = input("\nEnter a name for this run (or press Enter for 'flight'): ").strip()
    if not mission_name: mission_name = "flight"
    filename = f"{mission_name}_data.csv"
    
    input(f"\n👉 Press [ENTER] to ignite experiment...")
    start_experiment(s, filename)

if __name__ == "__main__":
    main_menu()


