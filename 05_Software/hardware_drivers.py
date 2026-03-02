import time
import board
import math
import adafruit_scd4x
import adafruit_veml7700
import adafruit_bme280.basic as adafruit_bme280
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

class SensorBay:
    def __init__(self):
        self.i2c = board.I2C()
        self.sensors = {'scd': None, 'bme': None, 'veml': None, 'ads_chan': None}
        
        # --- CONFIGURATION (From Team Member) ---
        self.R_FIXED = 20000.0    
        self.R_NOMINAL = 20000.0  
        self.B_COEFFICIENT = 3950.0 
        self.V_IN = 3.3             
        self.THERM_OFFSET = -18.0

        print("\n--- Initializing Hardware ---")
        self._init_sensors()

    def _init_sensors(self):
        # SCD40
        try:
            self.sensors['scd'] = adafruit_scd4x.SCD4X(self.i2c)
            self.sensors['scd'].start_periodic_measurement()
            print(" [OK] SCD40 CO2 Sensor")
        except Exception as e: print(f" [FAIL] SCD40: {e}")

        # BME280
        try:
            for addr in [0x77, 0x76]:
                try:
                    self.sensors['bme'] = adafruit_bme280.Adafruit_BME280_I2C(self.i2c, address=addr)
                    print(f" [OK] BME280 Environment Sensor ({hex(addr)})")
                    break
                except: continue
        except Exception as e: print(f" [FAIL] BME280: {e}")

        # VEML7700
        try:
            self.sensors['veml'] = adafruit_veml7700.VEML7700(self.i2c)
            print(" [OK] VEML7700 Lux Sensor")
        except Exception as e: print(f" [FAIL] VEML7700: {e}")

        # ADS1115
        try:
            ads = ADS.ADS1115(self.i2c)
            self.sensors['ads_chan'] = AnalogIn(ads, 0)
            print(" [OK] ADS1115 ADC/Thermistor")
        except Exception as e: print(f" [FAIL] ADS1115: {e}")

    def read_all(self):
        """
        Reads all sensors and returns a dictionary of values.
        This function is non-blocking and meant to be called by main.py
        """
        data = {
            'co2': float('nan'),
            'temp_scd': float('nan'), # Using BME temp as primary if available, else fallback to SCD? 
            'humidity': float('nan'),
            'pressure': float('nan'),
            'lux': float('nan'),
            'thermistor_volts': float('nan'),
            'thermistor_c': float('nan')
        }

        # Read SCD40
        if self.sensors['scd'] and self.sensors['scd'].data_ready:
            data['co2'] = self.sensors['scd'].CO2
            # We map SCD temp to temp_scd for now, but BME is more accurate for air temp
            data['temp_scd'] = self.sensors['scd'].temperature 

        # Read BME280 (Overrides temp_scd with more accurate BME temp)
        if self.sensors['bme']:
            data['temp_scd'] = self.sensors['bme'].temperature
            data['humidity'] = self.sensors['bme'].relative_humidity
            data['pressure'] = self.sensors['bme'].pressure

        # Read VEML7700
        if self.sensors['veml']:
            data['lux'] = self.sensors['veml'].lux

        # Read ADS1115 (Thermistor)
        if self.sensors['ads_chan']:
            v_out = self.sensors['ads_chan'].voltage
            data['thermistor_volts'] = v_out
            
            if 0.1 < v_out < (self.V_IN - 0.1):
                res = self.R_FIXED * ((self.V_IN / v_out) - 1)
                steinhart = math.log(res / self.R_NOMINAL) / self.B_COEFFICIENT
                steinhart += 1.0 / (25.0 + 273.15)
                therm_t = (1.0 / steinhart) - 273.15
                data['thermistor_c'] = therm_t + self.THERM_OFFSET

        return data
