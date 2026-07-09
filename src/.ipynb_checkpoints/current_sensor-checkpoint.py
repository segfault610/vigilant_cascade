from machine import ADC, Pin
import time
import math

# Pin and Sensor Configuration
sensor = ADC(Pin(26))
relay = Pin(22, Pin.OUT)

# Constants based on hardware specs
MA_PER_UNIT = 1.39
STALL_THRESHOLD_MA = 850.0 
SAMPLING_RATE_HZ = 20
WINDOW_SIZE = 128 # The input size your ID-CNN will require

def capture_for_inference(label, duration_sec=60):
    """
    Captures data in 60s bursts. This log acts as the training data
    for the ID-CNN Stage 2 classifier.
    """
    relay.value(1)
    time.sleep(1) # Stabilization period
    
    # Baseline for transient fault detection
    rolling_baseline = float(sorted([sensor.read_u16() for _ in range(20)])[10])
    
    print(f"Starting {duration_sec}s capture for Label: {label}")
    
    try:
        # File is overwritten to maintain a 'current' dataset snapshot
        with open(f"{label}.csv", "w") as f:
            start_time = time.ticks_ms()
            samples_taken = 0
            
            while time.ticks_diff(time.ticks_ms(), start_time) < (duration_sec * 1000):
                # Median filter for signal denoising (DSP Stage 1)
                raw = sorted([sensor.read_u16() for _ in range(7)])[3]
                
                # Baseline update
                rolling_baseline = (rolling_baseline * 0.99) + (raw * 0.01)
                delta = max(0, rolling_baseline - raw)
                current = delta * MA_PER_UNIT
                
                # Automatic Safety Cutoff 
                if current > STALL_THRESHOLD_MA:
                    relay.value(0)
                    print("STALL DETECTED: Safety Relay Triggered.")
                    break
                
                # Log raw data for future Qualcomm AI Hub training
                f.write(f"{raw},{int(rolling_baseline)},{delta:.1f},{current:.1f}\n")
                
                samples_taken += 1
                time.sleep(1.0 / SAMPLING_RATE_HZ)
                
    finally:
        relay.value(0)
        print(f"Capture complete. {samples_taken} samples saved.")

# Workflow commands:
# 1. capture_for_inference("normal")
# 2. capture_for_inference("slowed")
# 3. capture_for_inference("stalled")