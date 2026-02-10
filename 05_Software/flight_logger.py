import os
import csv
from datetime import datetime

class FlightLogger:
    def __init__(self, folder="mission_logs"):
        self.folder = folder
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        
        # Create unique filename: log_2026-02-09_1430.csv
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        self.filepath = os.path.join(self.folder, f"log_{timestamp}.csv")
        
        # Initialize file with headers
        self.headers = ["Timestamp", "CO2_ppm", "Air_Temp_C", "Humidity_PCT", "Pressure_hPa", "Lux", "Thermistor_V"]
        with open(self.filepath, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            
        print(f"[LOGGER] Recording to: {self.filepath}")

    def log(self, sensor_data):
        """
        Accepts the dictionary from SensorBay and writes a row
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        row = [
            timestamp,
            sensor_data.get("co2", 0),
            sensor_data.get("temp_scd", 0),
            sensor_data.get("humidity", 0),
            sensor_data.get("pressure", 0),
            sensor_data.get("lux", 0),
            sensor_data.get("thermistor_volts", 0)
        ]
        
        try:
            with open(self.filepath, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"[LOGGER ERROR] Could not write to file: {e}")
