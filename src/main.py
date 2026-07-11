from machine import ADC, Pin
import time

# Pin and Sensor Configuration
sensor = ADC(Pin(26))
relay = Pin(22, Pin.OUT)

# Constants
MA_PER_UNIT = 1.39
STALL_THRESHOLD_MA = 850.0 
SAMPLING_RATE_HZ = 20

def run_streaming_inference():
    relay.value(1)
    time.sleep(1)
    
    # Simple rolling baseline
    rolling_baseline = float(sensor.read_u16())
    
    while True:
        raw = sorted([sensor.read_u16() for _ in range(7)])[3]
        rolling_baseline = (rolling_baseline * 0.99) + (raw * 0.01)
        delta = max(0, rolling_baseline - raw)
        current = delta * MA_PER_UNIT
        
        # Safety Cutoff
        if current > STALL_THRESHOLD_MA:
            relay.value(0)
            break
        
        # STREAMING: Just print to serial. 
        # No file system overhead!
        print(f"{raw},{int(rolling_baseline)},{delta:.1f},{current:.1f}")
        
        time.sleep(1.0 / SAMPLING_RATE_HZ)

# Automatically run on startup
if __name__ == "__main__":
    run_streaming_inference()

