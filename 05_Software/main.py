# main.py
import time
from hardware_drivers import SensorBay
from flight_logger import FlightLogger
# We try to import the actuators. If the file is missing, we warn you.
try:
    from actuators import ActuatorBay
    ACTUATORS_PRESENT = True
except ImportError:
    ACTUATORS_PRESENT = False
    print("!! WARNING: actuators.py NOT FOUND. Running Sensors Only !!")

def main():
    print("--- PATHFINDER CUBESAT INITIALIZING ---")
    
    # 1. Setup Sensors
    sensors = SensorBay()
    
    # 2. Setup Logger
    logger = FlightLogger()
    
    # 3. Setup Actuators (Heater/Pump)
    actuators = None
    if ACTUATORS_PRESENT:
        actuators = ActuatorBay()
        print("--- ACTUATOR SELF-TEST: PUMP SPINNING FOR 2 SECONDS ---")
        actuators.run_pump(speed=50)
        time.sleep(2)
        actuators.stop_pump()
        print("--- SELF-TEST COMPLETE ---")

    print("--- SYSTEM READY: STARTING MISSION LOOP ---")
    
    try:
        while True:
            # A. Read Sensors
            data = sensors.read_all()
            current_temp = data.get('temp_scd', 0)
            
            # B. FLIGHT LOGIC (The Brain)
            if actuators:
                # Rule 1: Thermal Control (Heater ON if below 20C)
                if current_temp < 20.0:
                    actuators.set_heater(True)
                else:
                    actuators.set_heater(False)
                
                # Rule 2: Pump Control (Example: Keep OFF for now unless commanded)
                # actuators.run_pump(speed=50) # Uncomment to run pump
                
                # Get Actuator Status for the Log
                status = actuators.get_status()
                data.update(status) # Adds "Heater_State" and "Pump_State" to data
            
            # C. Log Data
            logger.log(data)
            
            # D. Print Status
            heater_status = data.get("Heater_State", "N/A")
            pump_status = data.get("Pump_State", "N/A")
            print(f"Status: CO2={data.get('co2',0)}ppm | Temp={current_temp:.1f}C | Heater={heater_status} | Pump={pump_status}")
            
            # E. Loop Rate
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n--- MISSION ABORTED ---")
    finally:
        if actuators:
            actuators.cleanup()
        print("System Safe.")

if __name__ == "__main__":
    main()main()

