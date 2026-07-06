from machine import I2S, Pin
import time
import struct

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
BUFFER_SIZE = 512  # 512 bytes = 128 samples at 32-bit (4 bytes per sample)

# The I2S internal DMA buffer needs headroom over a single read. Setting
# ibuf == BUFFER_SIZE leaves none, so readinto() races the DMA and silently
# drops/garbles samples -- this is the most common reason capture looks
# "broken" even when the mic is wired correctly.
IBUF_SIZE = BUFFER_SIZE * 8

# Below this peak amplitude, a captured buffer is treated as silence.
# Tune this to your board's actual noise floor if needed.
SILENCE_THRESHOLD = 500

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
    ibuf=IBUF_SIZE,
)


def decode_samples(buf, num_bytes):
    """Convert raw 32-bit I2S words into signed sample values.

    The INMP441 left-justifies its 24-bit output inside the 32-bit I2S
    frame, so the real sample value sits in the top 24 bits of each word.
    Without this shift, the raw words are not usable audio data.
    """
    count = num_bytes // 4
    words = struct.unpack("<%di" % count, bytes(buf[:num_bytes]))
    return [w >> 8 for w in words]


def check_mic_alive(sample_ms=200):
    """Capture briefly and confirm the mic is producing a real (non-silent)
    signal before starting a long capture. Returns True if a signal was
    detected, False otherwise (with a diagnostic printed either way).
    """
    probe = bytearray(BUFFER_SIZE)
    start = time.ticks_ms()
    peak = 0
    got_data = False

    while time.ticks_diff(time.ticks_ms(), start) < sample_ms:
        num_read = audio_in.readinto(probe, timeout=1000)
        if not num_read:
            continue
        got_data = True
        samples = decode_samples(probe, num_read)
        peak = max(peak, max(abs(s) for s in samples))

    if not got_data:
        print("MIC WARNING: No data returned by I2S within timeout.")
        print(
            "  Check wiring: SCK -> pin %d, WS -> pin %d, SD -> pin %d."
            % (SCK_PIN, WS_PIN, SD_PIN)
        )
        return False

    if peak < SILENCE_THRESHOLD:
        print("MIC WARNING: Signal looks flat (peak=%d)." % peak)
        print(
            "  Data is arriving but reads as near-silence. Most common "
            "cause: the INMP441 L/R pin is floating -- tie it to GND "
            "(left channel) or 3V3 (right channel) to match "
            "format=I2S.MONO."
        )
        return False

    print("Mic check OK (peak amplitude=%d)." % peak)
    return True


def capture_audio(label, duration_sec=3):
    """
    Captures raw I2S audio data to a binary file.
    """
    print(f"Starting {duration_sec}s capture for Label: {label}...")

    relay.on()
    time.sleep(0.5)  # Allow motor/sensor to stabilize

    if not check_mic_alive():
        relay.off()
        print("Aborting capture: microphone self-test failed.")
        return

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
