import time
import board
import math
import csv
import os
import sys
import adafruit_scd4x
import adafruit_veml7700
import adafruit_bme280.basic as adafruit_bme280
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- CONFIGURATION ---
R_FIXED = 20000.0    # 20k Fixed resistor (Pull-Down configuration)
R_NOMINAL = 20000.0  # 20k Thermistor
B_COEFFICIENT = 3950.0 
V_IN = 3.3             
LUX_CORRECTION = 0.88  # Reduces VEML7700 reading by 12% to match reference meter

i2c = board.I2C()

def setup_sensors():
    sensors = {'scd': None, 'bme': None, 'veml': None, 'ads_chan': None}
    print("\n--- Initializing Hardware ---")
    
    # SCD40
    try:
        sensors['scd'] = adafruit_scd4x.SCD4X(i2c)
        sensors['scd'].start_periodic_measurement()
        print(" [OK] SCD40 CO2 Sensor")
    except Exception as e: print(f" [FAIL] SCD40: {e}")

    # BME280
    try:
        for addr in [0x77, 0x76]:
            try:
                sensors['bme'] = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=addr)
                print(f" [OK] BME280 Environment Sensor ({hex(addr)})")
                break
            except: continue
    except Exception as e: print(f" [FAIL] BME280: {e}")

    # VEML7700
    try:
        sensors['veml'] = adafruit_veml7700.VEML7700(i2c)
        print(" [OK] VEML7700 Lux Sensor")
    except Exception as e: print(f" [FAIL] VEML7700: {e}")

    # ADS1115
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
            writer.writerow(["Timestamp", "CO2_ppm", "BME_Temp_C", "BME_RH", "Pressure_hPa", "Lux", "Thermistor_C", "Thermocouple_Ref"])
        writer.writerow(data)

def start_experiment(sensors, filename):
    print(f"\n🚀 EXPERIMENT STARTED: Logging to {filename}")
    print("Press Ctrl+C to stop the experiment.\n")
    print("="*85)
    print(f"{'Timestamp':<10} | {'CO2':<5} | {'Temp':<5} | {'RH%':<5} | {'Pres':<7} | {'Lux':<7} | {'Therm_C':<7}")
    print("="*85)

    try:
        while True:
            timestamp = time.strftime("%H:%M:%S")
            # Initialize all variables to NaN to prevent stale data carry-over
            co2 = bme_t = bme_rh = bme_p = lux = therm_t = float('nan')

            if sensors['scd'] and sensors['scd'].data_ready:
                co2 = sensors['scd'].CO2
            if sensors['bme']:
                bme_t = sensors['bme'].temperature
                bme_rh = sensors['bme'].relative_humidity
                bme_p = sensors['bme'].pressure
            if sensors['veml']:
                # Apply the 12% reduction calibration here
                lux = sensors['veml'].lux * LUX_CORRECTION
            if sensors['ads_chan']:
                v_out = sensors['ads_chan'].voltage
                
                if 0.1 < v_out < (V_IN - 0.1):
                    # Correct math for Pull-Down (3.3V -> Thermistor -> Analog -> Resistor -> GND)
                    res = R_FIXED * ((V_IN / v_out) - 1)
                    
                    steinhart = math.log(res / R_NOMINAL) / B_COEFFICIENT
                    steinhart += 1.0 / (25.0 + 273.15)
                    therm_t = (1.0 / steinhart) - 273.15

            # Terminal printout
            print(f"{timestamp:<10} | {co2:<5.0f} | {bme_t:<5.1f} | {bme_rh:<5.1f} | {bme_p:<7.1f} | {lux:<7.1f} | {therm_t:<7.2f}")
            
            # Save to SD/Disk with an empty string "" for the Thermocouple_Ref column
            log_to_csv(filename, [timestamp, co2, bme_t, bme_rh, bme_p, lux, therm_t, ""])
            
            # 5-second delay 
            time.sleep(5) 
            
    except KeyboardInterrupt:
        print("\n\n🛑 Experiment Stopped by User.")
        sys.exit()

# --- MAIN STARTUP UI ---
def main_menu():
    print("\n" + "*"*30)
    print("   CUBESAT PAYLOAD SYSTEM   ")
    print("*"*30)
    
    s = setup_sensors()
    
    print("\n[READY] System is standing by.")
    mission_name = input("Enter a name for this run (or press Enter for 'default'): ").strip()
    if not mission_name: mission_name = "default"
    filename = f"{mission_name}_data.csv"
    
    input(f"\n👉 Press [ENTER] to start logging to {filename}...")
    start_experiment(s, filename)

if __name__ == "__main__":
    main_menu()

