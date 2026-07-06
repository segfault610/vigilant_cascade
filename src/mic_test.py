from machine import I2S, Pin
import struct

relay = Pin(22, Pin.OUT)

# Audio Configuration
SCK_PIN = 18
WS_PIN = 19
SD_PIN = 20
SAMPLE_RATE = 20000  # 16kHz is typical for voice
BUFFER_SIZE = 512    # Size of the buffer to hold audio samples

# Give the DMA buffer headroom over a single read. With ibuf == BUFFER_SIZE
# there is no headroom, so readinto() races the DMA and silently
# drops/garbles samples (see mic_sensor.py for the full explanation).
IBUF_SIZE = BUFFER_SIZE * 8

SILENCE_THRESHOLD = 500

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
    ibuf=IBUF_SIZE,
)

# Buffer to store incoming audio data
audio_buffer = bytearray(BUFFER_SIZE)


def decode_samples(buf, num_bytes):
    """Convert raw 32-bit I2S words into signed sample values. The INMP441
    left-justifies its 24-bit output inside the 32-bit frame, so the real
    sample sits in the top 24 bits -- shift right by 8 to read it."""
    count = num_bytes // 4
    words = struct.unpack("<%di" % count, bytes(buf[:num_bytes]))
    return [w >> 8 for w in words]


print("Starting microphone capture...")

relay.on()
try:
    while True:
        # A timeout stops the board from hanging forever if the mic never
        # sends data (bad wiring, wrong pins, or a dead sensor). Previously
        # this call had no timeout, so a silent/dead mic would just freeze
        # the script with no error.
        num_read = audio_in.readinto(audio_buffer, timeout=1000)

        if not num_read:
            print("No data received from I2S within timeout -- check wiring.")
            continue

        samples = decode_samples(audio_buffer, num_read)
        peak = max(abs(s) for s in samples)
        print(f"Captured {num_read} bytes, {len(samples)} samples, peak amplitude={peak}")
        if peak < SILENCE_THRESHOLD:
            print("  -> looks like silence. Check the INMP441 L/R pin (tie to GND or 3V3).")
except KeyboardInterrupt:
    relay.off()
