#!/usr/bin/env python3
"""Test inference with motor fault detection model (FP32)"""

import numpy as np
import tensorflow as tf
import joblib
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def test_inference():
    print("🧪 Testing inference with FP32 model...")
    
    # Load TFLite model (use FP32 for best accuracy)
    interpreter = tf.lite.Interpreter(model_path='../models/model_fp32.tflite')
    interpreter.allocate_tensors()
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    print(f"Input shape: {input_details[0]['shape']}")
    print(f"Output shape: {output_details[0]['shape']}")
    
    # Load scaler
    scaler = joblib.load('../models/scaler.joblib')
    print("✅ Scaler loaded")
    
    # Create a synthetic normal window (similar to training data)
    np.random.seed(42)
    window = np.random.normal(4.06, 2.33, 128)
    window = np.clip(window, -0.1, 9.0)
    
    print(f"\n📊 Normal test window: {len(window)} samples")
    print(f"   Mean: {window.mean():.2f}, Std: {window.std():.2f}")
    
    # Normalize using scaler
    window_scaled = scaler.transform(window.reshape(-1, 1))
    input_data = window_scaled.reshape(1, 128, 1).astype(np.float32)
    
    # Run inference
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    
    output = interpreter.get_tensor(output_details[0]['index'])
    probs = np.exp(output[0]) / np.sum(np.exp(output[0]))
    pred = np.argmax(probs)
    
    print(f"\n📊 Result: {'🚨 FAULT' if pred == 1 else '✅ NORMAL'}")
    print(f"   Confidence: {np.max(probs):.4f}")
    
    # Fault pattern
    print("\n" + "="*50)
    print("Testing FAULT pattern...")
    fault_window = np.concatenate([
        np.random.normal(4.0, 2.0, 80),
        np.random.normal(15.0, 3.0, 48)
    ])
    fault_scaled = scaler.transform(fault_window.reshape(-1, 1))
    fault_input = fault_scaled.reshape(1, 128, 1).astype(np.float32)
    
    interpreter.set_tensor(input_details[0]['index'], fault_input)
    interpreter.invoke()
    fault_output = interpreter.get_tensor(output_details[0]['index'])
    fault_probs = np.exp(fault_output[0]) / np.sum(np.exp(fault_output[0]))
    fault_pred = np.argmax(fault_probs)
    
    print(f"📊 Result: {'🚨 FAULT' if fault_pred == 1 else '✅ NORMAL'}")
    print(f"   Confidence: {np.max(fault_probs):.4f}")

if __name__ == "__main__":
    test_inference()

