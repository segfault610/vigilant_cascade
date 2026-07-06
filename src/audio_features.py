"""
Turn a raw I2S microphone capture (produced by mic_sensor.py's
capture_audio()) into windowed features usable the same way the
current-sensor CSVs are used in VigilantCascade.ipynb.

Today the acoustic "Multi-Modal Sentry" described in the README is only
ever captured to a raw .bin file and never turned into anything a model
can train on -- the notebook only uses the current sensor. This script
closes that gap with a simple, cheap feature set (RMS energy, peak
amplitude, zero-crossing rate) as a starting point for an acoustic
classifier.

Usage:
    python audio_features.py normal.bin normal 0
    python audio_features.py slowed.bin slowed 1

Run on the host (regular CPython), after copying the .bin file off the
board, not on the microcontroller itself.
"""
import struct
import sys

WINDOW_SIZE = 128  # samples per window, matches the current-sensor CNN input


def load_samples(path):
    with open(path, "rb") as f:
        raw = f.read()
    count = len(raw) // 4
    words = struct.unpack("<%di" % count, raw[: count * 4])
    # INMP441 left-justifies 24-bit audio inside the 32-bit I2S frame.
    return [w >> 8 for w in words]


def windows(samples, window_size=WINDOW_SIZE):
    for i in range(0, len(samples) - window_size, window_size):
        yield samples[i : i + window_size]


def rms(window):
    return (sum(s * s for s in window) / len(window)) ** 0.5


def zero_crossing_rate(window):
    crossings = sum(1 for a, b in zip(window, window[1:]) if (a >= 0) != (b >= 0))
    return crossings / (len(window) - 1)


def main():
    if len(sys.argv) != 4:
        print("Usage: python audio_features.py <input.bin> <output_prefix> <label>")
        sys.exit(1)

    in_path, out_prefix, label = sys.argv[1], sys.argv[2], int(sys.argv[3])
    samples = load_samples(in_path)

    if not samples:
        print(f"No samples decoded from {in_path} -- is the file empty?")
        sys.exit(1)

    out_path = f"../data/{out_prefix}_audio.csv"
    rows_written = 0
    with open(out_path, "w") as f:
        for window in windows(samples):
            peak = max(abs(s) for s in window)
            f.write(f"{rms(window):.2f},{peak},{zero_crossing_rate(window):.4f},{label}\n")
            rows_written += 1

    print(f"Wrote {rows_written} windows to {out_path}")


if __name__ == "__main__":
    main()
