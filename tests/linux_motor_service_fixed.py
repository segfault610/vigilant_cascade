# linux_motor_service_fixed.py
import serial
import time
import json
import torch
import numpy as np
from pathlib import Path
from datetime import datetime
import threading
import queue
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MotorInferenceService:
    def __init__(self, serial_port='/dev/ttyACM0', baudrate=115200):
        self.window_size = 128
        self.model = self.load_model()
        self.serial = None
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.running = True
        self.response_queue = queue.Queue()
        self.command_queue = queue.Queue()
        
        # Start serial communication thread
        self.serial_thread = threading.Thread(target=self.serial_communication)
        self.serial_thread.start()
        
    def load_model(self):
        """Load the trained CNN model"""
        try:
            from MotorFaultCNN import MotorFaultCNN
            
            model = MotorFaultCNN()
            model_path = Path(__file__).parent / "models" / "motor_model.pth"
            
            if model_path.exists():
                model.load_state_dict(torch.load(model_path, map_location='cpu'))
                model.eval()
                logger.info("Model loaded successfully")
                return model
            else:
                logger.error(f"Model not found at {model_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def preprocess_window(self, raw_data):
        """Preprocess the window data for inference"""
        try:
            # Parse the comma-separated values
            values = [float(x) for x in raw_data.split(',')]
            
            if len(values) != self.window_size:
                logger.warning(f"Expected {self.window_size} values, got {len(values)}")
                return None
            
            # Normalize using training parameters
            normalized = np.array(values) / 200.0
            
            # Reshape for CNN [batch, channels, sequence_length]
            input_tensor = torch.tensor(normalized.reshape(1, 1, -1), dtype=torch.float32)
            return input_tensor
            
        except Exception as e:
            logger.error(f"Error preprocessing window: {e}")
            return None
    
    def run_inference(self, tensor_data):
        """Run inference on the preprocessed data"""
        if self.model is None:
            return {'prediction': 0, 'confidence': 0.5, 'is_fault': False}
        
        try:
            with torch.no_grad():
                output = self.model(tensor_data)
                probabilities = torch.softmax(output, dim=1)
                prediction = torch.argmax(output, dim=1).item()
                confidence = probabilities[0][prediction].item()
                
                result = {
                    'prediction': prediction,
                    'confidence': confidence,
                    'is_fault': (prediction == 1 and confidence > 0.7),
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"Inference result: {'FAULT' if result['is_fault'] else 'NORMAL'} "
                           f"(confidence: {confidence:.2f})")
                return result
                
        except Exception as e:
            logger.error(f"Error during inference: {e}")
            return {'prediction': 0, 'confidence': 0.5, 'is_fault': False}
    
    def serial_communication(self):
        """Handle serial communication with STM32"""
        try:
            self.serial = serial.Serial(self.serial_port, self.baudrate, timeout=1)
            logger.info(f"Connected to STM32 on {self.serial_port}")
            
            # Send initial command to start monitoring
            self.send_command("START_MONITORING")
            
            while self.running:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode().strip()
                    if line:
                        self.handle_serial_input(line)
                
                # Check for commands to send
                try:
                    cmd = self.command_queue.get_nowait()
                    self.send_command(cmd)
                except queue.Empty:
                    pass
                
                time.sleep(0.01)
                
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in serial communication: {e}")
    
    def handle_serial_input(self, line):
        """Handle incoming serial data from STM32"""
        logger.info(f"Received: {line}")
        
        # Parse messages from STM32
        if line.startswith("WINDOW_DATA:"):
            # Extract window data
            window_data = line[12:]  # Remove "WINDOW_DATA:"
            result = self.process_window(window_data)
            
            # Send result back to STM32
            if result == "FAULT_CONFIRMED":
                self.send_command("INFERENCE_RESULT", "FAULT_CONFIRMED")
            else:
                self.send_command("INFERENCE_RESULT", "FALSE_ALARM")
                
        elif "FAULT" in line:
            logger.warning(f"Fault detected: {line}")
            self.handle_fault_alert(line)
    
    def send_command(self, command, params=""):
        """Send a command to STM32"""
        try:
            if self.serial and self.serial.is_open:
                # Format: COMMAND:PARAMS
                if params:
                    full_command = f"{command}:{params}\n"
                else:
                    full_command = f"{command}\n"
                self.serial.write(full_command.encode())
                logger.info(f"Sent command: {full_command.strip()}")
        except Exception as e:
            logger.error(f"Error sending command: {e}")
    
    def process_window(self, window_data):
        """Process a window received from STM32"""
        # Preprocess
        tensor_data = self.preprocess_window(window_data)
        if tensor_data is None:
            return "ERROR: Invalid data"
        
        # Run inference
        result = self.run_inference(tensor_data)
        
        # Log result
        self.log_result(result, window_data)
        
        # Return decision to STM32
        if result['is_fault']:
            return "FAULT_CONFIRMED"
        else:
            return "FALSE_ALARM"
    
    def log_result(self, result, window_data):
        """Log the inference result"""
        log_entry = {
            'timestamp': result['timestamp'],
            'prediction': result['prediction'],
            'confidence': result['confidence'],
            'is_fault': result['is_fault']
        }
        
        logger.info(f"Log entry: {json.dumps(log_entry)}")
        
        # Save to JSON file
        try:
            log_file = Path(__file__).parent / "logs" / "inference_log.json"
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'a') as f:
                json.dump(log_entry, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Error logging result: {e}")
    
    def handle_fault_alert(self, message):
        """Handle fault alerts from STM32"""
        # Send notification, trigger alarms, etc.
        logger.warning("⚠️ FAULT ALERT FROM STM32!")
        
    def stop(self):
        """Stop the service"""
        self.running = False
        if self.serial and self.serial.is_open:
            self.send_command("STOP_MONITORING")
            self.serial.close()
        logger.info("Service stopped")

# Main entry point
if __name__ == "__main__":
    try:
        # Try different serial ports if first fails
        ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyS0']
        service = None
        
        for port in ports:
            try:
                service = MotorInferenceService(serial_port=port)
                logger.info(f"Started service on {port}")
                break
            except Exception as e:
                logger.warning(f"Failed on {port}: {e}")
                continue
        
        if service:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        else:
            logger.error("Could not connect to STM32 on any port")
            
    except KeyboardInterrupt:
        if 'service' in locals():
            service.stop()
        logger.info("Shutting down service...")

