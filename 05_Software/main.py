# main.py
import time
from hardware_drivers import SensorBay
from flight_logger import FlightLogger
from actuators import ActuatorBay

def main():
    print("--- PATHFINDER CUBESAT INITIALIZING ---")
    sensors = SensorBay()
    logger = FlightLogger()
    actuators = ActuatorBay()

    # STARTUP SELF-TEST
    print("[TEST] Cycling Actuators...")
    actuators.set_fan(True); time.sleep(0.5); actuators.set_fan(False)
    actuators.set_leds(True); time.sleep(0.5); actuators.set_leds(False)
    
    try:
        while True:
            data = sensors.read_all()
            temp = data.get('temp_scd', 0)
            lux = data.get('lux', 0)

            # --- AUTONOMOUS RULES ---
            # 1. Thermal: Heater ON < 20C, Fan ON > 25C
            actuators.set_heater(temp < 20.0)
            actuators.set_fan(temp > 25.0)
            
            # 2. Lighting: LEDs ON if Lux < 500
            actuators.set_leds(lux < 500)

            # 3. Irrigation: Run pump for 5s every 30s (Basic example)
            if int(time.time()) % 30 < 5:
                actuators.run_pump(speed=50)
            else:
                actuators.stop_pump()

            # Merge Actuator data for logging and printing
            status = actuators.get_status()
            data.update(status)
            logger.log(data)

            print(f"MET: {time.process_time():.0f}s | T: {temp:.1f}C | H: {status['Heater_State']} | F: {status['Fan_State']}")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n--- MISSION ABORTED ---")
    finally:
        actuators.cleanup()

if __name__ == "__main__":
    main()

