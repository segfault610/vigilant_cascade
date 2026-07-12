# infer_on_fault.py - Complete working version with data scaling
import time
import json
import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
from pathlib import Path
from datetime import datetime

# ============= Configuration =============
MODEL_PATH = "model_quantized.tflite"
SCALER_PATH = "scaler.joblib"
WINDOW_CSV = "fault_windows/fault_window.csv"
ALERT_LOG = "alerts.log"
FAULT_THRESHOLD = 0.65
WINDOW_SIZE = 128
POLL_INTERVAL = 0.5

# ---- DATA SCALING CONFIGURATION ----
# Your STM32 sends shunt voltage in mV (-0.05 to 0.01)
# Model was trained on current in mA (0 to 20)
# Scale factor converts mV to mA
# For a 0.1 ohm shunt: I(mA) = V(mV) * 10
# Adjust based on your actual shunt resistor
SHUNT_RESISTOR = 0.1  # Ohms - change to match your actual shunt
SCALE_FACTOR = 10.0 / SHUNT_RESISTOR  # For 0.1 ohm: 100
# =========================================

class FaultInferenceEngine:
    def __init__(self):
        print("="*60)
        print("🔍 MOTOR FAULT INFERENCE ENGINE")
        print("="*60)
        print(f"📊 Shunt resistor: {SHUNT_RESISTOR}Ω")
        print(f"📊 Scale factor: {SCALE_FACTOR}")
        
        # Load TFLite model
        try:
            self.interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
            self.interpreter.allocate_tensors()
            print(f"✅ Model loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            sys.exit(1)
        
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        print(f"   Input shape: {self.input_details[0]['shape']}")
        print(f"   Output shape: {self.output_details[0]['shape']}")
        
        # Load scaler
        try:
            self.scaler = joblib.load(SCALER_PATH)
            print(f"✅ Scaler loaded from {SCALER_PATH}")
        except Exception as e:
            print(f"❌ Failed to load scaler: {e}")
            sys.exit(1)
        
        # Setup
        self.window_csv = Path(WINDOW_CSV)
        self.alert_log = Path(ALERT_LOG)
        self.alert_log.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = None
        
        print(f"\n📁 Watching: {WINDOW_CSV}")
        print(f"📊 Fault threshold: {FAULT_THRESHOLD}")
        print("\n" + "="*60)
        print("🟢 Ready. Waiting for fault windows...\n")
    
    def preprocess_window(self, window_data):
        """
        Preprocess window data for inference.
        
        STM32 sends shunt voltage in mV.
        Convert to current in mA: I(mA) = V(mV) / R(Ω)
        Then scale to match training data range.
        """
        # Convert from mV to mA using Ohm's law
        # I = V / R, where V is in volts, R in ohms
        window_data = np.array(window_data) * SCALE_FACTOR
        
        # Clip extreme values to prevent overflow
        window_data = np.clip(window_data, -5, 30)
        
        # Ensure we have exactly 128 samples
        if len(window_data) != WINDOW_SIZE:
            if len(window_data) < WINDOW_SIZE:
                window_data = np.pad(window_data, (0, WINDOW_SIZE - len(window_data)), mode='edge')
            else:
                window_data = window_data[:WINDOW_SIZE]
        
        # Reshape and scale
        window_reshaped = np.array(window_data).reshape(-1, 1)
        window_scaled = self.scaler.transform(window_reshaped)
        
        # Shape: (1, 128, 1) - matches the quantized model's expected input
        return window_scaled.reshape(1, WINDOW_SIZE, 1).astype(np.float32)
    
    def run_inference(self, window_data):
        """Run inference on a window"""
        input_data = self.preprocess_window(window_data)
        
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        pred = np.argmax(output[0])
        confidence = float(output[0][pred])
        
        return {
            'prediction': int(pred),
            'confidence': confidence,
            'is_fault': (pred == 1),
            'label': '🚨 FAULT' if pred == 1 else '✅ NORMAL'
        }
    
    def log_alert(self, result, window_data):
        """Log alert to file and print"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'confidence': result['confidence'],
            'mean': float(np.mean(window_data)),
            'std': float(np.std(window_data)),
            'min': float(np.min(window_data)),
            'max': float(np.max(window_data))
        }
        
        print(f"\n{'='*60}")
        print(f"🔔 FAULT DETECTED at {timestamp}")
        print(f"   Confidence: {result['confidence']:.4f}")
        print(f"   Window stats: mean={log_entry['mean']:.2f}, std={log_entry['std']:.2f}")
        print(f"{'='*60}\n")
        
        with open(self.alert_log, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def get_window_hash(self, data):
        if data is None or len(data) == 0:
            return None
        return hash(tuple(data[:10]))
    
    def read_window(self):
        """Read the current fault window CSV"""
        if not self.window_csv.exists():
            return None
        
        try:
            df = pd.read_csv(self.window_csv)
            if 'value' not in df.columns:
                return None
            values = df['value'].values
            if len(values) >= WINDOW_SIZE:
                return values[:WINDOW_SIZE]
            return None
        except Exception as e:
            print(f"⚠️ Error reading CSV: {e}")
            return None
    
    def run(self):
        """Main monitoring loop"""
        while True:
            try:
                window_data = self.read_window()
                
                if window_data is not None:
                    current_hash = self.get_window_hash(window_data)
                    
                    if current_hash != self.last_hash:
                        self.last_hash = current_hash
                        
                        result = self.run_inference(window_data)
                        
                        print(f"📊 {result['label']} (conf: {result['confidence']:.4f})")
                        
                        if result['is_fault'] and result['confidence'] >= FAULT_THRESHOLD:
                            self.log_alert(result, window_data)
                
                time.sleep(POLL_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n👋 Shutting down...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(POLL_INTERVAL)

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}")
        sys.exit(1)
    
    if not os.path.exists(SCALER_PATH):
        print(f"❌ Scaler not found: {SCALER_PATH}")
        sys.exit(1)
    
    engine = FaultInferenceEngine()
    engine.run()

if __name__ == "__main__":
    main()

