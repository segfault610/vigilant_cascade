# test_communication.py
import serial
import time

def test_communication(port='/dev/ttyACM0', baudrate=115200):
    """
    Test the communication between STM32 and DragonWing SoC
    """
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f" Connected to {port}")
        
        # Send start command
        ser.write(b"START_MONITORING\n")
        print(" Sent START_MONITORING command")
        
        # Wait for responses
        timeout = time.time() + 30  # 30 second timeout
        windows_received = 0
        
        while time.time() < timeout:
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                
                if "WINDOW_START" in line:
                    print(" Window reception started")
                elif "WINDOW_END" in line:
                    windows_received += 1
                    print(f" Window {windows_received} received")
                elif "AWAITING_ACK" in line:
                    ser.write(b"ACK\n")
                    print(" Sent ACK")
                elif "FAULT" in line:
                    print(f" {line}")
                else:
                    print(f"STM32: {line}")
            
            time.sleep(0.1)
        
        print(f" Test complete. Received {windows_received} windows.")
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_communication()
