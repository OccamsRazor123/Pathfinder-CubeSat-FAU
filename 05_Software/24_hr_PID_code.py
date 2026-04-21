#This code is updated to reflect values in SVMD, focusing on a 24-hr cycle.
#Including logic for LUX conversion to DLI, and after the target DLI is achieved of 12, LEDs shut off.
#Heaters are now able to reach 100%.
#Correction factor will be required for LUX sensor due to placement.
# PID constants have yet to be tweaked.

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
HEATER_KP = 20.0  
HEATER_KI = 0.5   
HEATER_KD = 5.0   
MAX_HEATER_POWER = 100.0 # Uncapped for full thermal control

# Humidity Thresholds
RH_THRESHOLD_HIGH = 60.0 
RH_P_BAND = 10.0 

# Biological Lighting Targets (DLI based on 5:1 Red/Blue LED mix)
DAY_CYCLE_SECONDS = 86400  # Full 24-hour mission cycle
TARGET_DLI = 12.0          # Target Daily Light Integral (mol/m²/d)
LUX_TO_PPFD_FACTOR = 7.5   # 1 PPFD = ~7.5 Lux for this specific spectrum
MAX_LED_DUTY = 100.0 

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
WATER_HEAT_PIN = 17 
GROW_HEAT_PIN = 27  
FAN_PIN = 24        
LED_PIN = 25        
PUMP_CLK = 18       
PUMP_EN = 23        
PUMP_DIR = 16       

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Setup Climate Pins
climate_pins = [WATER_HEAT_PIN, GROW_HEAT_PIN, FAN_PIN, LED_PIN]
for pin in climate_pins:
    GPIO.setup(pin, GPIO.OUT)

# Force pump pins to OUT and default LOW (0 Volts)
pump_pins = [PUMP_CLK, PUMP_EN, PUMP_DIR]
for pin in pump_pins:
    GPIO.setup(pin, GPIO.OUT)
    
GPIO.output(PUMP_EN, GPIO.LOW)
GPIO.output(PUMP_CLK, GPIO.LOW)

# Initialize PWM Objects
pwm_water = GPIO.PWM(WATER_HEAT_PIN, 100)
pwm_grow = GPIO.PWM(GROW_HEAT_PIN, 100)
pwm_fan = GPIO.PWM(FAN_PIN, 100)
pwm_led = GPIO.PWM(LED_PIN, 1000) 

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
        # Anti-windup protection
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
            # Updated Headers to reflect PPFD and DLI tracking
            writer.writerow(["Timestamp", "CO2_ppm", "BME_Temp_C", "BME_RH", "Pressure_hPa", "Lux", "PPFD", "Thermistor_C", "Grow_Heat_%", "Water_Heat_%", "Fans_%", "LEDs_%", "Pump_Active", "Accum_DLI"])
        writer.writerow(data)

def save_mission_state(filename, day_start, accum_dli, dose_delivered):
    state = {
        "day_start_time": day_start,
        "accumulated_dli": accum_dli,
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
            if time.time() - state["day_start_time"] < cycle_seconds:
                print(f"🔄 MISSION RECOVERY: Resuming previous state from {filename}")
                return state
            else:
                print(f"🌅 RECOVERY OVERRIDE: Previous state is from an old day cycle. Starting fresh.")
        except Exception as e:
            print(f"⚠️ State file corrupted or missing. Starting fresh.")
    return None

def clamp_pwm(value):
    return max(0.0, min(100.0, value))

def start_experiment(sensors, filename):
    print(f"\n🚀 MISSION ACTIVE: Logging to {filename}")
    print("Press Ctrl+C to abort and safe all hardware.\n")
    
    state_filename = filename.replace('.csv', '_state.json')

    # Updated terminal header to accommodate PPFD and DLI
    print("="*165)
    print(f"{'Timestamp':<10} | {'CO2':<5} | {'Temp':<5} | {'RH%':<5} | {'Press':<7} | {'Lux':<7} | {'PPFD':<6} | {'Therm_C':<7} | {'G_Heat%':<7} | {'W_Heat%':<7} | {'Fans%':<5} | {'LEDs%':<5} | {'Acc_DLI'}")
    print("="*165)

    pump_is_running = False
    pump_stop_time = 0
    daily_dose_delivered = False 
    pwm_pump = None 
    
    accumulated_dli = 0.0
    day_start_time = time.time()
    last_loop_time = time.time()

    # Recovery Check (using .get() safely handles legacy JSON files)
    recovered_state = load_mission_state(state_filename, DAY_CYCLE_SECONDS)
    if recovered_state:
        day_start_time = recovered_state.get("day_start_time", day_start_time)
        accumulated_dli = recovered_state.get("accumulated_dli", 0.0)
        daily_dose_delivered = recovered_state.get("daily_dose_delivered", False)

    # Initialize PIDs
    grow_pid = PIDController(HEATER_KP, HEATER_KI, HEATER_KD, TEMP_THRESHOLD_LOW, out_max=MAX_HEATER_POWER)
    water_pid = PIDController(HEATER_KP, HEATER_KI, HEATER_KD, WATER_TEMP_LOW, out_max=MAX_HEATER_POWER)

    try:
        while True:
            current_time = time.time()
            dt = current_time - last_loop_time 
            last_loop_time = current_time
            
            timestamp = time.strftime("%H:%M:%S")
            co2 = bme_t = bme_rh = bme_p = lux = ppfd = therm_t = float('nan')
            
            g_heat_dc = w_heat_dc = fan_dc = led_dc = 0.0
            fan_dc_temp = fan_dc_rh = 0.0 

            # --- 24-HOUR DAY CYCLE RESET ---
            if current_time - day_start_time >= DAY_CYCLE_SECONDS:
                print("\n🌅 NEW DAY CYCLE STARTED. Resetting light and fluid trackers.")
                accumulated_dli = 0.0
                daily_dose_delivered = False 
                day_start_time = current_time

            # --- SENSOR POLLING & CONVERSION ---
            if sensors['scd'] and sensors['scd'].data_ready: co2 = sensors['scd'].CO2
            if sensors['bme']:
                bme_t = sensors['bme'].temperature
                bme_rh = sensors['bme'].relative_humidity
                bme_p = sensors['bme'].pressure
            if sensors['veml']: 
                lux = sensors['veml'].lux * LUX_CORRECTION
                ppfd = lux / LUX_TO_PPFD_FACTOR # Convert Raw Lux to PPFD
            if sensors['ads_chan']:
                v_out = sensors['ads_chan'].voltage
                if 0.1 < v_out < (V_IN - 0.1):
                    res = R_FIXED * ((V_IN / v_out) - 1)
                    steinhart = math.log(res / R_NOMINAL) / B_COEFFICIENT
                    steinhart += 1.0 / (25.0 + 273.15)
                    therm_t = (1.0 / steinhart) - 273.15

            # --- BIOLOGICAL LIGHTING LOGIC (DLI INTEGRATION) ---
            if accumulated_dli < TARGET_DLI:
                led_dc = MAX_LED_DUTY
                pwm_led.ChangeDutyCycle(led_dc)
                if not math.isnan(ppfd) and ppfd > 0:
                    # Accumulate micro-moles per square meter over time
                    accumulated_dli += (ppfd * dt) / 1_000_000.0
            else:
                led_dc = 0.0
                pwm_led.ChangeDutyCycle(led_dc)

            # --- PID CLIMATE CONTROL ---
            if not math.isnan(bme_t):
                if bme_t > TEMP_THRESHOLD_HIGH:
                    fan_dc_temp = clamp_pwm(((bme_t - TEMP_THRESHOLD_HIGH) / (TEMP_THRESHOLD_HIGH - TEMP_THRESHOLD_LOW)) * 100.0)
                
                if bme_t < TEMP_THRESHOLD_LOW:
                    g_heat_dc = grow_pid.compute(bme_t)
                else:
                    g_heat_dc = 0.0
                    grow_pid.reset_integral() 
            
            if not math.isnan(bme_rh):
                if bme_rh > RH_THRESHOLD_HIGH:
                    fan_dc_rh = clamp_pwm(((bme_rh - RH_THRESHOLD_HIGH) / RH_P_BAND) * 100.0)

            # Max Demand Routing for Fans
            fan_dc = max(fan_dc_temp, fan_dc_rh)

            if not math.isnan(therm_t):
                if therm_t < WATER_TEMP_LOW:
                    w_heat_dc = water_pid.compute(therm_t)
                else:
                    w_heat_dc = 0.0
                    water_pid.reset_integral()

            pwm_fan.ChangeDutyCycle(fan_dc)
            pwm_grow.ChangeDutyCycle(g_heat_dc)
            pwm_water.ChangeDutyCycle(w_heat_dc)

            # --- NON-BLOCKING PUMP LOGIC (SILENT FIX) ---
            if not daily_dose_delivered and not pump_is_running:
                # Flow calculation: (Target Volume / Rate) * 60 seconds
                duration_seconds = (TARGET_DAILY_VOLUME_UL / PUMP_FLOW_RATE_UL_MIN) * 60.0
                pump_stop_time = time.time() + duration_seconds
                pump_is_running = True
                daily_dose_delivered = True 
                
                print(f"*** DAILY FEEDING: Dispensing {TARGET_DAILY_VOLUME_UL} uL over {duration_seconds:.1f} seconds ***")
                
                # Wake up sequence
                GPIO.output(PUMP_DIR, GPIO.HIGH) 
                GPIO.output(PUMP_EN, GPIO.HIGH)
                time.sleep(0.05) 
                
                pwm_pump = GPIO.PWM(PUMP_CLK, 4000)
                pwm_pump.start(50)               

            if pump_is_running and time.time() >= pump_stop_time:
                if pwm_pump:
                    pwm_pump.stop()
                
                # Hard shutdown to prevent holding torque hum
                GPIO.output(PUMP_CLK, GPIO.LOW)
                GPIO.output(PUMP_EN, GPIO.LOW)
                    
                pump_is_running = False
                print("*** FLUID DISPENSE COMPLETE ***")

            # --- LOGGING ---
            print(f"{timestamp:<10} | {co2:<5.0f} | {bme_t:<5.1f} | {bme_rh:<5.1f} | {bme_p:<7.1f} | {lux:<7.1f} | {ppfd:<6.1f} | {therm_t:<7.2f} | {g_heat_dc:<7.1f} | {w_heat_dc:<7.1f} | {fan_dc:<5.1f} | {led_dc:<5.1f} | {accumulated_dli:<7.2f}")
            log_to_csv(filename, [timestamp, co2, bme_t, bme_rh, bme_p, lux, ppfd, therm_t, g_heat_dc, w_heat_dc, fan_dc, led_dc, pump_is_running, accumulated_dli])
            save_mission_state(state_filename, day_start_time, accumulated_dli, daily_dose_delivered)

            time.sleep(2) 
            
    except KeyboardInterrupt:
        pwm_grow.stop()
        pwm_water.stop()
        pwm_fan.stop()
        pwm_led.stop()
        
        if pwm_pump:
            pwm_pump.stop()
        
        # Safely ground all pump pins on abort
        GPIO.output(PUMP_CLK, GPIO.LOW)
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


