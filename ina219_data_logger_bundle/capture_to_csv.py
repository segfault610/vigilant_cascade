"""
Reads the INA219 data logger's Serial output and writes it straight to a
CSV file as it arrives -- the Arduino itself can't write to your PC's
filesystem, so this is the "simultaneous save to CSV" half of the pipeline.

Usage:
    python capture_to_csv.py COM5 loaded_trial01.csv

Stops automatically when the sketch prints "---CAPTURE_COMPLETE---", or
press Ctrl+C to stop early.
"""

import sys
import serial

BAUD_RATE = 115200


def main():
    if len(sys.argv) != 3:
        print("Usage: python capture_to_csv.py <COM_PORT> <output.csv>")
        sys.exit(1)

    port = sys.argv[1]
    output_path = sys.argv[2]

    ser = serial.Serial(port, BAUD_RATE, timeout=1)
    print(f"Listening on {port} -> writing {output_path}")
    print("Waiting for the sketch to finish its positioning/settle delays...")

    with open(output_path, "w", newline="") as f:
        try:
            while True:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                print(line)

                if line == "---CAPTURE_COMPLETE---":
                    print("Capture complete.")
                    break

                f.write(line + "\n")
                f.flush()
        except KeyboardInterrupt:
            print("\nStopped early by user.")

    ser.close()


if __name__ == "__main__":
    main()
