import board
import busio
import adafruit_scd4x
import adafruit_veml7700
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_bme280 import basic as adafruit_bme280

class SensorBay:
    def __init__(self):
        self.i2c = board.I2C()
        self.sensors = {
            "SCD40": None,
            "BME280": None,
            "LUX": None,
            "ADC": None
        }
        self.init_hardware()

    def init_hardware(self):
        # 1. SCD40 (CO2)
        try:
            self.sensors["SCD40"] = adafruit_scd4x.SCD4X(self.i2c)
            self.sensors["SCD40"].start_periodic_measurement()
            print("[HARDWARE] SCD40: ONLINE")
        except:
            print("[HARDWARE] SCD40: OFFLINE")

        # 2. BME280 (Atmosphere)
        try:
            try:
                self.sensors["BME280"] = adafruit_bme280.Adafruit_BME280_I2C(self.i2c, address=0x77)
            except:
                self.sensors["BME280"] = adafruit_bme280.Adafruit_BME280_I2C(self.i2c, address=0x76)
            print("[HARDWARE] BME280: ONLINE")
        except:
            print("[HARDWARE] BME280: OFFLINE")

        # 3. VEML7700 (Lux)
        try:
            self.sensors["LUX"] = adafruit_veml7700.VEML7700(self.i2c)
            print("[HARDWARE] VEML7700: ONLINE")
        except:
            print("[HARDWARE] VEML7700: OFFLINE (Check wiring)")

        # 4. ADS1115 (Thermistor)
        try:
            self.ads = ADS1115(self.i2c)
            self.sensors["ADC"] = AnalogIn(self.ads, 0) # Channel 0
            print("[HARDWARE] ADS1115: ONLINE")
        except:
            print("[HARDWARE] ADS1115: OFFLINE")

    def read_all(self):
        """Returns a dictionary of all latest sensor readings"""
        data = {
            "co2": 0, "temp_scd": 0, "humidity": 0,
            "pressure": 0, "temp_bme": 0,
            "lux": 0,
            "thermistor_volts": 0
        }

        # SCD40
        if self.sensors["SCD40"] and self.sensors["SCD40"].data_ready:
            data["co2"] = self.sensors["SCD40"].CO2
            data["temp_scd"] = self.sensors["SCD40"].temperature
            data["humidity"] = self.sensors["SCD40"].relative_humidity

        # BME280
        if self.sensors["BME280"]:
            try:
                data["pressure"] = self.sensors["BME280"].pressure
                data["temp_bme"] = self.sensors["BME280"].temperature
            except: pass

        # Lux
        if self.sensors["LUX"]:
            try:
                data["lux"] = self.sensors["LUX"].lux
            except: pass

        # ADC
        if self.sensors["ADC"]:
            try:
                data["thermistor_volts"] = self.sensors["ADC"].voltage
            except: pass
            
        return data
