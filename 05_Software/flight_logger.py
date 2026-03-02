# flight_logger.py
import os
import csv
from datetime import datetime

class FlightLogger:
    def __init__(self, folder="mission_logs"):
        self.folder = folder
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        self.filepath = os.path.join(self.folder, f"log_{timestamp}.csv")
        
        # Expanded headers for full mission data
        self.headers = [
            "Timestamp", "CO2_ppm", "Air_Temp_C", "Humidity_PCT", 
            "Pressure_hPa", "Lux", "Heater_State", "Pump_State", 
            "Fan_State", "LED_State"
        ]
        
        with open(self.filepath, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            
        print(f"[LOGGER] Initialized: {self.filepath}")

    def log(self, data):
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        row = [
            timestamp,
            data.get("co2", 0),
            data.get("temp_scd", 0),
            data.get("humidity", 0),
            data.get("pressure", 0),
            data.get("lux", 0),
            data.get("Heater_State", "OFF"),
            data.get("Pump_State", "OFF"),
            data.get("Fan_State", "OFF"),
            data.get("LED_State", "OFF")
        ]
        
        with open(self.filepath, mode='a', newline='') as f:
            csv.writer(f).writerow(row)
