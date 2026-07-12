import numpy as np
from ai_edge_litert.interpreter import Interpreter, load_delegate

# 1. Load the QNN Delegate for NPU (HTP backend)
# The 'options' dictionary tells the delegate to use the NPU.
qnn_delegate = load_delegate(
    "libQnnTFLiteDelegate.so",
    options={"backend_type": "htp"}  # 'htp' is the Hexagon Tensor Processor (NPU)
)

# 2. Load your quantized TFLite model with the delegate
interpreter = Interpreter(
    model_path="model_int8.tflite",  # Path to your model on the device
    experimental_delegates=[qnn_delegate]
)
interpreter.allocate_tensors()

# 3. Get input and output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# 4. Prepare your input data
# Your input shape is (1, 128, 1). The data must be float32.
input_data = np.array(your_window_of_128_samples, dtype=np.float32).reshape(1, 128, 1)

# 5. Run inference
interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()

# 6. Get the output
output_data = interpreter.get_tensor(output_details[0]['index'])
predicted_class = np.argmax(output_data[0])
print(f"Predicted class: {predicted_class}")

