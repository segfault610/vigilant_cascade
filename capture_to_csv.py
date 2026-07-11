import sys
import time
import serial

BAUD_RATE = 115200
DEFAULT_PORT = "/dev/ttyACM0"


def main():
    # Allow passing port via CLI or fallback to default /dev/ttyACM0
    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    output_path = sys.argv[2] if len(sys.argv) > 2 else "normal2.csv"

    print(f"Target file: {output_path}")
    print(f"Continuously attempting to connect to {port} (Press Ctrl+C to exit)...")

    with open(output_path, "w", newline="") as f:
        while True:
            try:
                # Attempt to open serial connection
                ser = serial.Serial(port, BAUD_RATE, timeout=1, dsrdtr=False)
                ser.setDTR(False)
                print(f"\n[Connected] Listening on {port} -> writing {output_path}")
                print("Waiting for Arduino startup and 20s positioning delay...")

                while True:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    # Print to console so you can watch progress
                    if not line.startswith("---"):
                        print(f"Data: {line}")
                    else:
                        print(line)

                    if line == "---CAPTURE_COMPLETE---":
                        print("Capture complete successfully.")
                        ser.close()
                        return

                    # Write clean data lines directly to file
                    if not line.startswith("---"):
                        f.write(line + "\n")
                        f.flush()

            except (serial.SerialException, OSError):
                # Board is offline/resetting, sleep briefly and retry connection
                time.sleep(1.0)
                continue
            except KeyboardInterrupt:
                print("\nStopped early by user.")
                try:
                    ser.close()
                except Exception:
                    pass
                break


if __name__ == "__main__":
    main()

