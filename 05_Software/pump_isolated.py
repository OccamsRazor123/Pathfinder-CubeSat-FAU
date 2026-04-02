# Code used to test if pump hums while stationary
import RPi.GPIO as GPIO
import time

# --- PIN DEFINITIONS (BCM Numbering) ---
PUMP_CLK = 18       # Hardware PWM for the step pulse (Physical Pin 12)
PUMP_EN = 23        # Start/Stop (Physical Pin 16)
PUMP_DIR = 16       # CW/CCW Direction (Physical Pin 36)

# --- TEST CONFIGURATION ---
FREQ_HZ = 4000      # 4000 Hz = 88 uL/min (Based on your bench test)
RUN_TIME_SEC = 10   # Run for 10 seconds per test cycle

def setup_hardware():
    """Configures the GPIO pins securely."""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    # Set pins as outputs
    GPIO.setup(PUMP_CLK, GPIO.OUT)
    GPIO.setup(PUMP_DIR, GPIO.OUT)
    GPIO.setup(PUMP_EN, GPIO.OUT)
    
    # Ensure pump is safely disabled at startup (0 Volts)
    GPIO.output(PUMP_EN, GPIO.LOW)
    GPIO.output(PUMP_CLK, GPIO.LOW)

def test_pump(direction_cw=True):
    """Executes a single fluid delivery cycle."""
    print(f"\n🚀 Waking up driver board...")
    
    # 1. Set Direction (HIGH = Clockwise, LOW = Counter-Clockwise)
    if direction_cw:
        GPIO.output(PUMP_DIR, GPIO.HIGH)
        print("   Direction: Clockwise")
    else:
        GPIO.output(PUMP_DIR, GPIO.LOW)
        print("   Direction: Counter-Clockwise")
        
    # 2. Enable the motor driver (Send 3.3V to wake the chip)
    GPIO.output(PUMP_EN, GPIO.HIGH)
    
    # 3. The CRITICAL 50ms hardware wake-up delay
    time.sleep(0.05) 
    
    # 4. Start the PWM metronome
    print(f"🌊 Pumping fluid at {FREQ_HZ} Hz for {RUN_TIME_SEC} seconds...")
    pwm = GPIO.PWM(PUMP_CLK, FREQ_HZ)
    pwm.start(50) # Always 50% duty cycle for stepper drivers
    
    try:
        # Let the pump run while Python sleeps
        time.sleep(RUN_TIME_SEC)
    except KeyboardInterrupt:
        print("\n⚠️ Test manually aborted early!")

    # 5. Safely stop the pump
    print("🛑 Stopping flow and safing hardware...")
    pwm.stop()
    GPIO.output(PUMP_CLK, GPIO.LOW) # Pull clock completely flat to 0V
    GPIO.output(PUMP_EN, GPIO.LOW)  # Command the driver to sleep

# --- MAIN MENU EXECUTION ---
try:
    setup_hardware()
    print("=======================================")
    print("   STANDALONE PUMP DIAGNOSTIC TOOL   ")
    print("=======================================")
    print(f"Configuration: {FREQ_HZ} Hz | {RUN_TIME_SEC} Sec per run")
    
    while True:
        choice = input("\n👉 Press [ENTER] to run pump test, or type 'q' to quit: ").strip().lower()
        
        if choice == 'q':
            break
            
        test_pump(direction_cw=True)
        print("\n🎧 Listen to the pump. Is it humming right now?")

except KeyboardInterrupt:
    print("\nProcess interrupted by user.")
finally:
    # This runs when you type 'q' or press Ctrl+C
    print("\nCleaning up GPIO pins...")
    GPIO.cleanup() 
    print("Hardware safed. Exiting tool.")

