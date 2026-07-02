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

