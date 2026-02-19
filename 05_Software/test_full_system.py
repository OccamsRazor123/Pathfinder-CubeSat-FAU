# test_full_system.py
import time
import RPi.GPIO as GPIO
from hardware_drivers import SensorBay
from pump_driver import PumpDriver

# --- CONFIGURATION ---
PIN_FAN = 17
PIN_LED = 27
PIN_HEATER = 22

def setup_system():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup Basic Actuators
    GPIO.setup(PIN_FAN, GPIO.OUT)
    GPIO.setup(PIN_LED, GPIO.OUT)
    GPIO.setup(PIN_HEATER, GPIO.OUT)
    
    # Initialize Subsystems
    print("Initializing Sensor Bay...")
    sensors = SensorBay()
    
    print("Initializing Fluid Pump System...")
    pump = PumpDriver()
    
    return sensors, pump

def main():
    sensors, pump = setup_system()
    print("\n--- FULL SYSTEM INTEGRATION TEST ---")
    print("Testing Sensors, Heaters, Fans, LEDs, and Pumps simultaneously.\n")
    
    try:
        while True:
            # 1. READ SENSORS
            data = sensors.read_all()
            print(f"TELEMETRY | CO2: {data.get('co2', 0)}ppm | Temp: {data.get('temp_scd', 0):.1f}C")
            
            # 2. ACTUATOR SEQUENCE
            print(">>> SEQUENCE: Day Cycle (LEDs ON, Heater ON, Pump Forward 50%)")
            GPIO.output(PIN_LED, GPIO.HIGH)
            GPIO.output(PIN_HEATER, GPIO.HIGH)
            GPIO.output(PIN_FAN, GPIO.LOW)
            pump.run(speed_percent=50, clockwise=True)
            time.sleep(4)
            
            # 3. READ SENSORS AGAIN TO VERIFY NO I2C CRASHES DURING HIGH POWER DRAW
            data = sensors.read_all()
            print(f"TELEMETRY | CO2: {data.get('co2', 0)}ppm | Temp: {data.get('temp_scd', 0):.1f}C")
            
            # 4. ACTUATOR SEQUENCE 
            print(">>> SEQUENCE: Night Cycle (LEDs OFF, Heater OFF, Fan ON, Pump Stop)")
            GPIO.output(PIN_LED, GPIO.LOW)
            GPIO.output(PIN_HEATER, GPIO.LOW)
            GPIO.output(PIN_FAN, GPIO.HIGH)
            pump.stop()
            time.sleep(4)

    except KeyboardInterrupt:
        print("\n--- TEST ABORTED. SAFING SYSTEM ---")
    finally:
        GPIO.output(PIN_FAN, GPIO.LOW)
        GPIO.output(PIN_LED, GPIO.LOW)
        GPIO.output(PIN_HEATER, GPIO.LOW)
        pump.cleanup()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
