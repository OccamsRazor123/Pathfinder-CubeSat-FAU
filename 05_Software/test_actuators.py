import time
import RPi.GPIO as GPIO

# --- CONFIGURATION ---
# These must match the wiring on your Black Controller Board
PIN_FAN = 17     # GPIO 17 (Pin 11)
PIN_LED = 27     # GPIO 27 (Pin 13)
PIN_HEATER = 22  # GPIO 22 (Pin 15) - Optional/Spare

# --- SETUP ---
def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup Pins as Outputs and default to OFF (Low)
    GPIO.setup(PIN_FAN, GPIO.OUT)
    GPIO.output(PIN_FAN, GPIO.LOW)
    
    GPIO.setup(PIN_LED, GPIO.OUT)
    GPIO.output(PIN_LED, GPIO.LOW)
    
    GPIO.setup(PIN_HEATER, GPIO.OUT)
    GPIO.output(PIN_HEATER, GPIO.LOW)
    
    print("--- ACTUATOR TEST MODE ---")
    print(f"FAN: GPIO {PIN_FAN} | LED: GPIO {PIN_LED} | HEATER: GPIO {PIN_HEATER}")
    print("Commands: 'FAN ON', 'FAN OFF', 'LED ON', 'ALL OFF', 'EXIT'")

# --- MAIN LOOP ---
def main():
    setup()
    
    try:
        while True:
            cmd = input("\nENTER COMMAND > ").strip().upper()
            
            if cmd == "EXIT":
                break
            
            elif cmd == "FAN ON":
                GPIO.output(PIN_FAN, GPIO.HIGH)
                print(">> Fan ENABLED")
                
            elif cmd == "FAN OFF":
                GPIO.output(PIN_FAN, GPIO.LOW)
                print(">> Fan DISABLED")
                
            elif cmd == "LED ON":
                GPIO.output(PIN_LED, GPIO.HIGH)
                print(">> LED ENABLED")
                
            elif cmd == "LED OFF":
                GPIO.output(PIN_LED, GPIO.LOW)
                print(">> LED DISABLED")
                
            elif cmd == "HEATER ON":
                GPIO.output(PIN_HEATER, GPIO.HIGH)
                print(">> Heater ENABLED")
                
            elif cmd == "HEATER OFF":
                GPIO.output(PIN_HEATER, GPIO.LOW)
                print(">> Heater DISABLED")
                
            elif cmd == "ALL ON":
                GPIO.output(PIN_FAN, GPIO.HIGH)
                GPIO.output(PIN_LED, GPIO.HIGH)
                GPIO.output(PIN_HEATER, GPIO.HIGH)
                print(">> ALL SYSTEMS GO")
                
            elif cmd == "ALL OFF":
                GPIO.output(PIN_FAN, GPIO.LOW)
                GPIO.output(PIN_LED, GPIO.LOW)
                GPIO.output(PIN_HEATER, GPIO.LOW)
                print(">> ALL SYSTEMS STOP")
                
            else:
                print("Invalid Command. Try: FAN ON, LED OFF, ALL OFF")
                
    except KeyboardInterrupt:
        print("\nTest Aborted.")
    finally:
        print("Cleaning up GPIO...")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
