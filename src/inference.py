arduino@uno-q:~/motor_monitor$ 
arduino@uno-q:~/motor_monitor$ cat ./inference.py 
# inference.py
import numpy as np
import tensorflow as tf
import joblib
from pathlib import Path

class FaultDetector:
    def __init__(self, model_path="../models/model_fp16.tflite", scaler_path="../models/scaler.joblib"):
        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        self.interpreter = None
        self.scaler = None
        self.load_model()
        self.load_scaler()

    def load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        self.interpreter = tf.lite.Interpreter(model_path=str(self.model_path))
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        print(f"✅ Loaded TFLite model from {self.model_path}")

    def load_scaler(self):
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler not found: {self.scaler_path}")
        self.scaler = joblib.load(self.scaler_path)
        print(f"✅ Loaded scaler from {self.scaler_path}")

    def predict(self, window_samples):
        """
        window_samples: list or numpy array of 128 raw current values
        Returns: (prediction_class, confidence) where 0=Normal, 1=Fault
        """
        if len(window_samples) != 128:
            raise ValueError(f"Expected 128 samples, got {len(window_samples)}")

        # Reshape and scale
        arr = np.array(window_samples, dtype=np.float32).reshape(-1, 1)
        scaled = self.scaler.transform(arr).reshape(1, 128, 1)

        # Run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], scaled)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])[0]

        # Softmax
        exp = np.exp(output)
        probs = exp / np.sum(exp)
        pred = int(np.argmax(probs))
        confidence = float(probs[pred])

        return pred, confidence

    def predict_from_csv(self, csv_path, sample_col='value'):
        """
        Read a CSV with columns: sample_index, value, timestamp (or any with a column named 'value')
        Returns: (prediction, confidence)
        """
        import pandas as pd
        df = pd.read_csv(csv_path)
        if sample_col not in df.columns:
            raise KeyError(f"CSV must contain column '{sample_col}'")
        values = df[sample_col].values[:128]  # take first 128 rows
        if len(values) < 128:
            raise ValueError(f"CSV has only {len(values)} rows, need 128")
        return self.predict(values)

