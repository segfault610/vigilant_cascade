# collect_and_infer.py
from arduino.app_utils import Bridge, App
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import joblib
import json

# ---- Inference imports ----
from ai_edge_litert.interpreter import Interpreter, load_delegate

# ===================== CONFIGURATION =====================
STORAGE_DIR = Path("fault_windows")
STORAGE_DIR.mkdir(exist_ok=True)

INDIVIDUAL_CSV = STORAGE_DIR / "fault_window.csv"
CONSOLIDATED_CSV = STORAGE_DIR / "all_fault_windows.csv"

# Model & scaler paths (adjust if needed)
MODEL_PATH = "model_int8.tflite"
SCALER_PATH = "scaler.joblib"

# QNN delegate path (adjust if different)
DELEGATE_PATH = "/usr/lib/libQnnTFLiteDelegate.so"

# Class names (must match training order)
CLASS_NAMES = ["Normal", "Slowed", "Fast"]

# ===================== LOAD MODEL & SCALER =====================
print("Loading scaler...")
scaler = joblib.load(SCALER_PATH)

print("Loading TFLite model with NPU delegate...")
try:
    delegate = load_delegate(
        DELEGATE_PATH,
        options={"backend_type": "htp", "htp_performance_mode": "3"}  # high perf
    )
    interpreter = Interpreter(
        model_path=MODEL_PATH,
        experimental_delegates=[delegate]
    )
except Exception as e:
    print(f"⚠️ NPU delegate failed: {e}")
    print("Falling back to CPU only.")
    interpreter = Interpreter(model_path=MODEL_PATH)

interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
print("✅ Model loaded.")

# ===================== INFERENCE FUNCTION =====================
def predict_window(samples: list):
    """
    samples: list of 128 raw current values (float)
    Returns: (class_name, confidence)
    """
    # 1. Convert to numpy and scale
    x = np.array(samples, dtype=np.float32).reshape(-1, 1)
    x_scaled = scaler.transform(x).reshape(1, 128, 1)
    
    # 2. Run inference
    interpreter.set_tensor(input_details[0]['index'], x_scaled)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0]
    
    # 3. Softmax to get probabilities
    exp = np.exp(output - np.max(output))
    probs = exp / exp.sum()
    pred_idx = np.argmax(probs)
    
    return CLASS_NAMES[pred_idx], float(probs[pred_idx])

# ===================== RPC HANDLER =====================
def save_window(window_data_str: str):
    print(f"📥 Received window: {window_data_str[:50]}...")
    
    try:
        parts = window_data_str.split(',')
        if len(parts) != 129:
            print(f"❌ Invalid window: expected 129 values, got {len(parts)}")
            Bridge.call("command", "ERROR")
            return "ERROR: Invalid data format"
        
        timestamp = int(parts[0])
        samples = [float(x) for x in parts[1:]]
        received_time = datetime.now().isoformat()
        
        # ---- Run inference ----
        try:
            pred_class, confidence = predict_window(samples)
            print(f"🧠 Prediction: {pred_class} (conf={confidence:.3f})")
        except Exception as e:
            print(f"⚠️ Inference failed: {e}")
            pred_class = "Unknown"
            confidence = 0.0
        
        # ---- Save individual CSV (overwrites) ----
        with open(INDIVIDUAL_CSV, 'w') as f:
            f.write("sample_index,value,timestamp,prediction,confidence\n")
            for i, val in enumerate(samples):
                f.write(f"{i},{val},{received_time},{pred_class},{confidence}\n")
        print(f"✅ Saved to {INDIVIDUAL_CSV}")
        
        # ---- Append to consolidated CSV ----
        file_exists = CONSOLIDATED_CSV.exists()
        with open(CONSOLIDATED_CSV, 'a') as f:
            if not file_exists:
                header = ["timestamp", "received_time", "prediction", "confidence"] + [f"s{i}" for i in range(128)]
                f.write(",".join(header) + "\n")
            row = [str(timestamp), received_time, pred_class, str(confidence)] + [str(v) for v in samples]
            f.write(",".join(row) + "\n")
        print(f"✅ Appended to {CONSOLIDATED_CSV}")
        
        # ---- Send ACK back to STM32 ----
        Bridge.call("command", "ACK")
        print("✅ ACK sent to STM32")
        
        return "ACK: Window saved and classified"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return f"ERROR: {str(e)}"

# ===================== RPC REGISTRATION =====================
Bridge.provide("save_window", save_window)

# Optional: register a ping handler for testing
def ping():
    return "pong"
Bridge.provide("ping", ping)

# ===================== MAIN LOOP =====================
def loop():
    time.sleep(1)

if __name__ == "__main__":
    print("="*60)
    print("🚀 DRAGONWING FAULT CLASSIFIER")
    print("="*60)
    print(f"Individual CSV : {INDIVIDUAL_CSV.absolute()}")
    print(f"Consolidated CSV: {CONSOLIDATED_CSV.absolute()}")
    print("Waiting for STM32 windows...\n")
    App.run(user_loop=loop)


