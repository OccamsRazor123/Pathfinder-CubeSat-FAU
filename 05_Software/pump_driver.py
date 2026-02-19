# pump_driver.py
import RPi.GPIO as GPIO

class PumpDriver:
    def __init__(self, pin_clk=18, pin_en=24, pin_dir=23):
        self.PIN_CLK = pin_clk   # Controls Speed (PWM)
        self.PIN_EN = pin_en     # Start/Stop
        self.PIN_DIR = pin_dir   # CW/CCW
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup Pins
        GPIO.setup(self.PIN_EN, GPIO.OUT)
        GPIO.setup(self.PIN_DIR, GPIO.OUT)
        GPIO.setup(self.PIN_CLK, GPIO.OUT)
        
        # Initialize PWM on CLK pin (Start at 1000Hz, 0% duty cycle)
        self.pwm = GPIO.PWM(self.PIN_CLK, 1000) 
        self.pwm.start(0) 

    def run(self, speed_percent, clockwise=True):
        """
        Runs the pump.
        speed_percent: 1 to 100
        clockwise: True for forward, False for reverse
        """
        # Set Direction
        GPIO.output(self.PIN_DIR, GPIO.HIGH if clockwise else GPIO.LOW)
        
        # Set Enable (Start)
        GPIO.output(self.PIN_EN, GPIO.HIGH)
        
        # Set Speed (Translating 1-100% to Frequency for the stepper driver)
        target_freq = max(100, int(speed_percent * 40)) # Max 4000Hz based on manual
        self.pwm.ChangeFrequency(target_freq)
        self.pwm.ChangeDutyCycle(50) # 50% duty is standard for stepper clock signals

    def stop(self):
        """Stops the pump safely."""
        GPIO.output(self.PIN_EN, GPIO.LOW)
        self.pwm.ChangeDutyCycle(0)

    def cleanup(self):
        self.stop()
        self.pwm.stop()
