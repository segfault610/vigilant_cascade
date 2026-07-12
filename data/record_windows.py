#!/usr/bin/env python3
"""
Record labeled windows from Arduino streaming data.

Arduino sketch should output:
- 128 lines of "0.0,0.0,0.0,<current>"
- Then a line containing "---WINDOW_BOUNDARY---"

Usage:
    python record_windows.py /dev/ttyACM0

Press:
    n  → save as NORMAL
    s  → save as SPIKE
    t  → save as STALL
    q  → quit
"""

import serial
import sys
import time
from pathlib import Path
import csv

# --- Configuration ---
WINDOW_SIZE = 128
DATA_DIR = Path("../data")          # adjust as needed
DATA_DIR.mkdir(exist_ok=True)

HEADER = ["raw", "baseline", "delta", "current"]

def parse_current(line):
    """Extract current value from a line like '0.0,0.0,0.0,<value>'"""
    parts = line.strip().split(',')
    if len(parts) == 4:
        try:
            return float(parts[3])
        except ValueError:
            return None
    return None

def save_window(label, samples, timestamp_ms):
    """Append a window to the appropriate CSV file."""
    csv_path = DATA_DIR / f"{label}_data.csv"
    file_exists = csv_path.exists()

    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)
        for val in samples:
            # raw and baseline use the same timestamp; delta = 0
            writer.writerow([timestamp_ms, timestamp_ms, 0.0, val])

    print(f"✅ Appended window to {csv_path}")

def main(port):
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"Connected to {port}")
    except Exception as e:
        print(f"Error opening {port}: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("WINDOW RECORDER")
    print("Collecting 128-sample windows from Arduino.")
    print("When a window is ready, press:")
    print("  n  → save as NORMAL")
    print("  s  → save as SPIKE")
    print("  t  → save as STALL")
    print("  q  → quit")
    print("="*60 + "\n")

    samples = []
    window_count = 0
    timestamp_ms = int(time.time() * 1000)  # baseline timestamp

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            # Check for window boundary
            if "---WINDOW_BOUNDARY---" in line:
                if len(samples) == WINDOW_SIZE:
                    window_count += 1
                    print(f"\n--- Window #{window_count} captured ---")
                    # Prompt for label
                    while True:
                        key = input("Label? (n/s/t/q): ").strip().lower()
                        if key in ['n', 's', 't']:
                            label_map = {'n': 'normal', 's': 'spike', 't': 'stall'}
                            save_window(label_map[key], samples, timestamp_ms)
                            break
                        elif key == 'q':
                            print("Quitting...")
                            ser.close()
                            return
                        else:
                            print("Invalid input. Press n, s, t, or q.")

                    # Reset for next window
                    samples = []
                    timestamp_ms = int(time.time() * 1000)
                else:
                    print("Warning: boundary received but not enough samples?")
                continue

            # Parse current value
            cur = parse_current(line)
            if cur is not None:
                samples.append(cur)
                if len(samples) > WINDOW_SIZE:
                    # Should not happen, but keep buffer at WINDOW_SIZE
                    samples = samples[-WINDOW_SIZE:]

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        ser.close()
        print("Serial port closed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python record_windows.py <serial_port>")
        print("Example: python record_windows.py /dev/ttyACM0")
        sys.exit(1)
    main(sys.argv[1])
