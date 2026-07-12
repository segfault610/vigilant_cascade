arduino@uno-q:~/motor_monitor$ cat collect_windows_on_faults.py 
# collect_windows_on_faults.py
from arduino.app_utils import Bridge, App
import time
from datetime import datetime
from pathlib import Path

storage_dir = Path("fault_windows")
storage_dir.mkdir(exist_ok=True)

INDIVIDUAL_CSV = storage_dir / "fault_window.csv"
CONSOLIDATED_CSV = storage_dir / "all_fault_windows.csv"

def save_window(window_data_str: str):
    print(f"Received window: {window_data_str[:50]}...")
    
    try:
        parts = window_data_str.split(',')
        if len(parts) != 129:
            print(f"Invalid window: expected 129 values, got {len(parts)}")
            return "ERROR: Invalid data format"
        
        timestamp = int(parts[0])
        samples = [float(x) for x in parts[1:]]
        received_time = datetime.now().isoformat()
        
        with open(INDIVIDUAL_CSV, 'w') as f:
            f.write("sample_index,value,timestamp\n")
            for i, val in enumerate(samples):
                f.write(f"{i},{val},{received_time}\n")
        
        print(f"Window saved to {INDIVIDUAL_CSV}")
        
        file_exists = CONSOLIDATED_CSV.exists()
        with open(CONSOLIDATED_CSV, 'a') as f:
            if not file_exists:
                header = ["timestamp", "received_time"] + [f"s{i}" for i in range(128)]
                f.write(",".join(header) + "\n")
            row = [str(timestamp), received_time] + [str(v) for v in samples]
            f.write(",".join(row) + "\n")
        
        print(f"Appended to {CONSOLIDATED_CSV}")
        
        Bridge.call("command", "ACK")
        print("ACK sent to STM32")
        
        return "ACK: Window saved successfully"
        
    except Exception as e:
        print(f"Error: {e}")
        return f"ERROR: {str(e)}"

def fromQRB(data: int):
    print(f"STM32 status: {data}")

Bridge.provide("save_window", save_window)
Bridge.provide("fromQRB", fromQRB)

def loop():
    time.sleep(1)

if __name__ == "__main__":
    print("="*60)
    print("DRAGONWING FAULT WINDOW RECEIVER")
    print("="*60)
    print(f"Individual: {INDIVIDUAL_CSV.absolute()}")
    print(f"Consolidated: {CONSOLIDATED_CSV.absolute()}")
    print("Waiting for STM32...\n")
    App.run(user_loop=loop)


