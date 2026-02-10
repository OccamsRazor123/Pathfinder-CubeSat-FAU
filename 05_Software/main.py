import time
import threading
from hardware_drivers import SensorBay
from flight_logger import FlightLogger
# from gui_dashboard import Dashboard # Uncomment if you are ready to run the GUI

def main():
    print("--- PATHFINDER CUBESAT INITIALIZING ---")
    
    # 1. Setup Hardware
    sensors = SensorBay()
    
    # 2. Setup Logger
    logger = FlightLogger()
    
    # 3. Setup GUI (Optional for headless mode)
    # app = Dashboard() 
    
    print("--- SYSTEM READY: STARTING MISSION LOOP ---")
    
    try:
        while True:
            # A. Read Sensors
            data = sensors.read_all()
            
            # B. Log Data
            logger.log(data)
            
            # C. Print Status (For Debugging)
            print(f"Status: CO2={data['co2']}ppm | Temp={data['temp_scd']}C | Volt={data['thermistor_volts']:.2f}V")
            
            # D. Update GUI (If enabled)
            # app.update_display(data)
            # app.update()
            
            # E. Loop Rate (e.g., 1Hz)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n--- MISSION ABORTED (USER INTERRUPT) ---")

if __name__ == "__main__":
    main()
