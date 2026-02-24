# actuators.py
import RPi.GPIO as GPIO
import time

class ActuatorBay:
    def __init__(self):
        # --- CONFIGURATION ---
        self.PIN_HEATER_1 = 22    # GPIO 22 (Pin 15)
        self.PIN_HEATER_2 = 25    # GPIO 25 (Pin 22) - NEW
        self.PIN_PUMP_PWM = 18    # GPIO 18 (Pin 12)
        self.PIN_PUMP_EN = 24     # GPIO 24 (Pin 18)
        self.PIN_PUMP_DIR = 23    # GPIO 23 (Pin 16)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup Pins
        GPIO.setup(self.PIN_HEATER_1, GPIO.OUT)
        GPIO.setup(self.PIN_HEATER_2, GPIO.OUT)
        GPIO.setup(self.PIN_PUMP_EN, GPIO.OUT)
        GPIO.setup(self.PIN_PUMP_DIR, GPIO.OUT)
        GPIO.setup(self.PIN_PUMP_PWM, GPIO.OUT)
        
        # Initialize Pump
        self.pump_pwm = GPIO.PWM(self.PIN_PUMP_PWM, 1000) 
        self.pump_pwm.start(0)
        
        # Initialize States
        self.heater_state = False
        self.pump_state = False

    def set_heater(self, state):
        """Turn BOTH Heaters ON (True) or OFF (False)"""
        self.heater_state = state
        # We fire both to ensure the payload heats evenly
        GPIO.output(self.PIN_HEATER_1, GPIO.HIGH if state else GPIO.LOW)
        GPIO.output(self.PIN_HEATER_2, GPIO.HIGH if state else GPIO.LOW)

    def run_pump(self, speed=50, clockwise=True):
        """Runs the pump continuously"""
        self.pump_state = True
        GPIO.output(self.PIN_PUMP_DIR, GPIO.HIGH if clockwise else GPIO.LOW)
        GPIO.output(self.PIN_PUMP_EN, GPIO.HIGH)
        self.pump_pwm.ChangeDutyCycle(speed)

    def stop_pump(self):
        """Stops the pump"""
        self.pump_state = False
        GPIO.output(self.PIN_PUMP_EN, GPIO.LOW)
        self.pump_pwm.ChangeDutyCycle(0)

    def get_status(self):
        return {
            "Heater_State": "ON" if self.heater_state else "OFF",
            "Pump_State": "ON" if self.pump_state else "OFF"
        }

    def cleanup(self):
        self.stop_pump()
        self.set_heater(False)
        GPIO.cleanup()
