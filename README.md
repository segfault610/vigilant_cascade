## **Vigilant Cascade: AI-Powered Smart System for Monitoring Industrial Motor Health** 

## **1. Problem Statement** 

Large-scale industrial facilities rely on critical rotating machinery such as motors, pumps and compressors whose unexpected failure causes catastrophic operational and financial losses. While machines exhibit early warning signs like subtle vibration changes or clicking, they are often masked by ambient factory noise. Current solutions rely on hardcoded thresholds, leading to excessive false alarms or missed structural failures. Furthermore, continuously streaming raw, high-frequency sensor data creates unmanageable network bottlenecks. Thus, there is a need for an offline, intelligent system that compresses multi-sensor data locally, validates faults, and provides accurate predictive maintenance. 

## **2. Proposed Solution & Innovation** 

We propose an offline, multi-stage edge system that shifts processing from the cloud to localized hardware. By keeping intelligence at the edge, we eliminate bandwidth issues and ensure robust, offline operation independently of cloud connectivity, setting a new standard for industrial reliability. 

## **The Three-Tier Cascaded Inference Process:** 

- **Stage 1 Multi-Modal Sentry:** The system continuously monitors acoustic and electrical signals using an Arduino Uno Q. It applies a Discrete Wavelet Transform directly at the sensor node to detect hidden transient faults in real-time. 

- **Stage 2 On-Board AI Verification:** To eliminate false positives, a lightweight 1D-CNN binary classifier optimized for the board, filters environmental noise from genuine mechanical defects. For immediate protection, if the current sensor detects a stall/jam, the Arduino triggers an integrated relay for an automatic safety cutoff. 

- **Stage 3 Lifespan Prediction:** Validated anomaly windows are forwarded to a Snapdragon X Copilot+ PC. Leveraging the Qualcomm AI Hub, we deploy a high-performance time-series regression model like LSTM or Temporal Convolutional Network compressed to INT8 precision. Running bare-metal on the Hexagon NPU, this model calculates the asset's remaining useful life (RUL). 

## **3. Architecture** 

The system orchestrates a responsive safety loop across three devices: 

1. **Arduino Uno Q:** Handles high-speed sampling, wavelet DSP and 1D-CNN communicating via an internal RPC bridge for near-zero latency. 

2. **Snapdragon PC:** Performs NPU-accelerated RUL regression using models optimized via the Qualcomm AI Hub and QNN SDK, ensuring ultra-fast, efficient inference. 

3. **Mobile Interface:** Provides a real-time dashboard for technicians, featuring haptic overrides for emergency shutdowns and contextualized maintenance ticketing. 

## **4. Additional Components Required** 

12V DC Motor 

ACS712 Current Sensor INMP441 Microphone Module Single-Channel Electrical Relay Module 12V Power Supply Adapter Breadboard M-M Jumper wires x 10 M-F Jumper wires x 10 F-F Jumper wires x 10 Red and Green LEDs 

> **INMP441 wiring note:** the mic's `L/R` pin must be tied to GND (left channel) or 3V3 (right channel) to match `format=I2S.MONO` in the capture scripts. A floating `L/R` pin is the most common reason the mic appears to capture silence.

## **5. Current Implementation Status**

This README describes the full three-stage hackathon vision. As of this branch, here's what's actually implemented vs. still planned:

**Implemented:**
- Current-sensor capture with median-filter denoising, a rolling baseline, and a stall/jam safety cutoff (`src/current_sensor.py`)
- Microphone (INMP441/I2S) capture, now with a proper DMA buffer size, 24-bit sample decoding, and a startup self-test that flags silent/dead-mic wiring (`src/mic_sensor.py`, `src/mic_test.py`)
- A host-side script to turn raw mic captures into windowed features (RMS energy, peak amplitude, zero-crossing rate) so audio data can be used the same way the current-sensor CSVs are (`src/audio_features.py`)
- A 1D-CNN trained on current-sensor data to classify normal vs. slowed motor behavior, with a shared scaler (no per-class leakage), a held-out test split, and reported accuracy (`src/VigilantCascade.ipynb`)
- Live inference from serial data using the exact scaler saved at training time (`models/motor_scaler.joblib`), instead of a hardcoded normalization guess

**Not yet implemented (still just described above):**
- Discrete Wavelet Transform stage
- Deployment to the Arduino Uno Q (current code targets a MicroPython/RP2040-class board)
- Snapdragon/Qualcomm AI Hub NPU inference and RUL (remaining useful life) regression
- Mobile dashboard and haptic overrides
- Using acoustic features (from `audio_features.py`) in the classifier — currently only the current sensor feeds the model

## **6. Setup**

```bash
pip install -r requirements.txt
jupyter notebook src/VigilantCascade.ipynb
```

Training the notebook produces `models/motor_model_scratch.pth` and `models/motor_scaler.joblib`. Both are needed for live inference — the scaler must match the one used at training time or predictions will be wrong.

