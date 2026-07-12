from machine import I2S, Pin

relay = Pin(22, Pin.OUT)

# Audio Configuration
SCK_PIN = 18
WS_PIN = 19
SD_PIN = 20
SAMPLE_RATE = 20000 # 16kHz is typical for voice
BUFFER_SIZE = 512   # Size of the buffer to hold audio samples

# Initialize I2S
# id=0 is usually the first I2S peripheral
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

# Buffer to store incoming audio data
# Using a bytearray to store 32-bit samples
audio_buffer = bytearray(BUFFER_SIZE)

print("Starting microphone capture...")

relay.on()
try:
    while True:
        # Read audio samples into the buffer
        num_read = audio_in.readinto(audio_buffer)
        
        # Print the raw data to the console
        # In a real application, you would process this buffer here
        if num_read > 0:
            print(f"Captured {num_read} bytes")
            # Example: print the first few bytes to verify signal
            print(list(audio_buffer[:8]))
except (KeyboardInterrupt):
    relay.off()
