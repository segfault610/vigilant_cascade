from machine import ADC, Pin
import time

sensor = ADC(Pin(26))
relay = Pin(22, Pin.OUT)

# Calibration constant
MA_PER_UNIT = 1.39 

def run_ml_data_capture(duration_sec=10):
    relay.value(1)
    time.sleep(1) # Allow motor to spin up
    
    # Initialize baseline with a stable value
    rolling_baseline = float(sorted([sensor.read_u16() for _ in range(20)])[10])
    
    print("TIME_MS,RAW_VALUE,BASELINE,DELTA,CURRENT_MA")
    start = time.ticks_ms()
    
    try:
        while time.ticks_diff(time.ticks_ms(), start) < (duration_sec * 1000):
            raw = sorted([sensor.read_u16() for _ in range(7)])[3]
            
            # Update rolling baseline: 99% old value, 1% new raw value
            # This allows the baseline to 'track' normal motor behavior
            rolling_baseline = (rolling_baseline * 0.99) + (raw * 0.01)
            
            # Calculate delta (baseline - raw)
            # We use a threshold to ignore minor noise jitter
            delta = max(0, rolling_baseline - raw)
            current = delta * MA_PER_UNIT
            
            print(f"{time.ticks_ms()},{raw},{int(rolling_baseline)},{delta:.1f},{current:.1f}")
            time.sleep(0.05)
    finally:
        relay.value(0)


