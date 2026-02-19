import RPi.GPIO as GPIO

# --- CONFIGURATION ---
PIN_HEATER = 22      # GPIO 22 (Pin 15)
PIN_PUMP_PWM = 18    # GPIO 18 (Pin 12) - Speed
PIN_PUMP_EN = 24     # GPIO 24 (Pin 18) - Start/Stop
PIN_PUMP_DIR = 23    # GPIO 23 (Pin 16) - Direction

class ActuatorBay:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup Heater
        GPIO.setup(PIN_HEATER, GPIO.OUT)
        GPIO.output(PIN_HEATER, GPIO.LOW)
        
        # Setup Pump
        GPIO.setup(PIN_PUMP_EN, GPIO.OUT)
        GPIO.setup(PIN_PUMP_DIR, GPIO.OUT)
        GPIO.setup(PIN_PUMP_PWM, GPIO.OUT)
        
        # Setup Pump Speed Control (PWM)
        self.pump_pwm = GPIO.PWM(PIN_PUMP_PWM, 1000) # 1000Hz default
        self.pump_pwm.start(0)

    def set_heater(self, state):
        """Turn Heater ON (True) or OFF (False)"""
        GPIO.output(PIN_HEATER, GPIO.HIGH if state else GPIO.LOW)

    def run_pump(self, duration_sec, speed=50):
        """Runs the pump for X seconds, then stops automatically"""
        GPIO.output(PIN_PUMP_DIR, GPIO.HIGH) # Clockwise
        GPIO.output(PIN_PUMP_EN, GPIO.HIGH)  # Enable
        self.pump_pwm.ChangeDutyCycle(speed) # Set Speed
        
        # Note: In a real state machine, we avoid time.sleep() blocking!
        # But for simple logic, this works:
        import time
        time.sleep(duration_sec)
        self.stop_pump()

    def stop_pump(self):
        GPIO.output(PIN_PUMP_EN, GPIO.LOW)
        self.pump_pwm.ChangeDutyCycle(0)

    def cleanup(self):
        self.stop_pump()
        GPIO.output(PIN_HEATER, GPIO.LOW)
