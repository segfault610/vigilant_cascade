# collect_windows_on_faults.py
from arduino.app_utils import *
import time
from datetime import datetime
from pathlib import Path

# --- Setup storage ---
storage_dir = Path("fault_windows")
storage_dir.mkdir(exist_ok=True)

# Fixed filename that will be overwritten each time
INDIVIDUAL_CSV = storage_dir / "fault_window.csv"
CONSOLIDATED_CSV = storage_dir / "all_fault_windows.csv"

# Track if we've written headers
headers_written = False

# --- Function called by STM32 when fault is detected ---
def save_window(window_data_str: str):
    """
    Receives window data from STM32 via Bridge.call()
    Data format: "timestamp,val1,val2,...,val128"
    OVERWRITES the individual CSV file each time.
    """
    global headers_written
    
    print(f"Received window: {window_data_str[:50]}...")
    
    try:
        # Parse the data
        parts = window_data_str.split(',')
        if len(parts) != 129:  # timestamp + 128 samples
            print(f"Invalid window: expected 129 values, got {len(parts)}")
            return "ERROR: Invalid data format"
        
        timestamp = int(parts[0])
        samples = [float(x) for x in parts[1:]]
        received_time = datetime.now().isoformat()
        
        # --- OVERWRITE individual CSV file ---
        with open(INDIVIDUAL_CSV, 'w') as f:
            f.write("sample_index,value,timestamp\n")
            for i, val in enumerate(samples):
                f.write(f"{i},{val},{timestamp}\n")
        
        print(f"Window overwritten to {INDIVIDUAL_CSV}")
        
        # --- APPEND to consolidated CSV (keeps history) ---
        # If you want to overwrite consolidated too, change 'a' to 'w' below
        file_exists = CONSOLIDATED_CSV.exists()
        
        with open(CONSOLIDATED_CSV, 'a') as f:
            if not file_exists:
                header = ["timestamp", "received_time"] + [f"s{i}" for i in range(128)]
                f.write(",".join(header) + "\n")
            
            row = [str(timestamp), received_time] + [str(v) for v in samples]
            f.write(",".join(row) + "\n")
        
        print(f"Appended to {CONSOLIDATED_CSV}")
        
        # Send ACK back to STM32
        Bridge.call("command", "ACK")
        print("ACK sent to STM32")
        
        return "ACK: Window saved successfully"
        
    except Exception as e:
        print(f"Error: {e}")
        return f"ERROR: {str(e)}"

# --- Function called by STM32 for status updates ---
def fromQRB(data: int):
    print(f"STM32 status: {data}")

# --- Register functions ---
Bridge.provide("save_window", save_window)
Bridge.provide("fromQRB", fromQRB)

# --- Main loop ---
def loop():
    time.sleep(1)

if __name__ == "__main__":
    print("="*60)
    print("DRAGONWING FAULT WINDOW RECEIVER")
    print("Using RPC Bridge")
    print("="*60)
    print(f"Individual window: {INDIVIDUAL_CSV.absolute()} (OVERWRITTEN each time)")
    print(f"Consolidated log: {CONSOLIDATED_CSV.absolute()} (APPENDED)")
    print("Waiting for STM32 to detect faults...\n")
    
    App.run(user_loop=loop)

