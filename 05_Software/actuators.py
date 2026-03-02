# actuators.py
import RPi.GPIO as GPIO

class ActuatorBay:
    def __init__(self):
        # --- CONFIGURATION ---
        self.PIN_FAN = 17          # GPIO 17 (Pin 11)
        self.PIN_LED = 27          # GPIO 27 (Pin 13)
        self.PIN_HEATER_1 = 22     # GPIO 22 (Pin 15)
        self.PIN_HEATER_2 = 25     # GPIO 25 (Pin 22)
        self.PIN_PUMP_PWM = 18     # GPIO 18 (Pin 12)
        self.PIN_PUMP_EN = 24      # GPIO 24 (Pin 18)
        self.PIN_PUMP_DIR = 23     # GPIO 23 (Pin 16)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup All Pins
        GPIO.setup([self.PIN_FAN, self.PIN_LED, self.PIN_HEATER_1, 
                    self.PIN_HEATER_2, self.PIN_PUMP_EN, 
                    self.PIN_PUMP_DIR, self.PIN_PUMP_PWM], GPIO.OUT)
        
        # Initialize Pump
        self.pump_pwm = GPIO.PWM(self.PIN_PUMP_PWM, 1000) 
        self.pump_pwm.start(0)
        
        # Internal States
        self.heater_state = False
        self.pump_state = False
        self.fan_state = False
        self.led_state = False

    def set_heater(self, state):
        self.heater_state = state
        GPIO.output([self.PIN_HEATER_1, self.PIN_HEATER_2], GPIO.HIGH if state else GPIO.LOW)

    def set_fan(self, state):
        self.fan_state = state
        GPIO.output(self.PIN_FAN, GPIO.HIGH if state else GPIO.LOW)

    def set_leds(self, state):
        self.led_state = state
        GPIO.output(self.PIN_LED, GPIO.HIGH if state else GPIO.LOW)

    def run_pump(self, speed=50, clockwise=True):
        self.pump_state = True
        GPIO.output(self.PIN_PUMP_DIR, GPIO.HIGH if clockwise else GPIO.LOW)
        GPIO.output(self.PIN_PUMP_EN, GPIO.HIGH)
        self.pump_pwm.ChangeDutyCycle(speed)

    def stop_pump(self):
        self.pump_state = False
        GPIO.output(self.PIN_PUMP_EN, GPIO.LOW)
        self.pump_pwm.ChangeDutyCycle(0)

    def get_status(self):
        """Returns status for logging and the GUI display"""
        return {
            "Heater_State": "ON" if self.heater_state else "OFF",
            "Pump_State": "ON" if self.pump_state else "OFF",
            "Fan_State": "ON" if self.fan_state else "OFF",
            "LED_State": "ON" if self.led_state else "OFF"
        }

    def cleanup(self):
        self.stop_pump()
        GPIO.output([self.PIN_FAN, self.PIN_LED, self.PIN_HEATER_1, self.PIN_HEATER_2], GPIO.LOW)
        GPIO.cleanup()
