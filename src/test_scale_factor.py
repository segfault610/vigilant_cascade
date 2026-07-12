# test_scale_factor.py
import numpy as np
import tensorflow as tf
import joblib
import pandas as pd

print("🧪 Finding the right scale factor...")

# Load model
interpreter = tf.lite.Interpreter("model_quantized.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Load scaler
scaler = joblib.load("scaler.joblib")

# Read a real window from STM32
df = pd.read_csv("fault_windows/fault_window.csv")
test_data = df['value'].values[:128]

print(f"Raw STM32 data: min={test_data.min():.4f}, max={test_data.max():.4f}")
print("\nTesting different scale factors (for 0.1 ohm shunt, factor=100):")
print("-" * 60)
print("Factor  | Scaled Range    | Result   | Confidence")
print("-" * 60)

for factor in [10, 50, 100, 200, 500, 1000]:
    scaled = test_data * factor
    scaled_reshaped = scaler.transform(scaled.reshape(-1, 1))
    input_data = scaled_reshaped.reshape(1, 128, 1).astype(np.float32)
    
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    
    pred = np.argmax(output[0])
    conf = output[0][pred]
    result = "FAULT" if pred == 1 else "NORMAL"
    
    print(f"{factor:6d} | {scaled.min():8.2f} to {scaled.max():8.2f} | {result:8s} | {conf:.4f}")

print("-" * 60)
print("\nIf NORMAL with confidence > 0.9, that factor works!")
print("For 0.1 ohm shunt, use factor=100")
print("For other shunt values, use: factor = 10 / shunt_resistor")

