from machine import I2S, Pin
import time

# Pin Configuration
# Adjust these pins based on your specific microcontroller board layout
SCK_PIN = 18
WS_PIN = 19
SD_PIN = 20
RELAY_PIN = 22

# Setup Relay
relay = Pin(RELAY_PIN, Pin.OUT)

# Audio Configuration
SAMPLE_RATE = 20000 
# 512 bytes = 128 samples at 32-bit (4 bytes per sample)
BUFFER_SIZE = 512  

# Initialize I2S
audio_in = I2S(
    0, 
    sck=Pin(SCK_PIN), 
    ws=Pin(WS_PIN), 
    sd=Pin(SD_PIN), 
    mode=I2S.RX, 
    bits=32, 
    format=I2S.MONO, 
    rate=SAMPLE_RATE, 
    ibuf=BUFFER_SIZE
)

def capture_audio(label, duration_sec=3):
    """
    Captures raw I2S audio data to a binary file.
    """
    print(f"Starting {duration_sec}s capture for Label: {label}...")
    
    relay.on()
    time.sleep(0.5) # Allow motor/sensor to stabilize
    
    audio_buffer = bytearray(BUFFER_SIZE)
    bytes_written = 0
    
    try:
        # Open in binary mode ('wb') for speed and efficiency
        with open(f"{label}.bin", "wb") as f:
            start_time = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), start_time) < (duration_sec * 1000):
                # timeout=50 ensures the script doesn't hang if no data is present
                num_read = audio_in.readinto(audio_buffer, timeout=50)
                
                if num_read and num_read > 0:
                    f.write(audio_buffer[:num_read])
                    bytes_written += num_read
                    
    finally:
        relay.off()
        print(f"Capture complete. {bytes_written} bytes saved to {label}.bin.")

# To run:
# capture_audio("free")
# capture_audio("slowed")
