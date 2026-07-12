#include <Wire.h>

// --- INA219 Registers ---
const uint8_t INA219_ADDR = 0x40;
const uint8_t REG_SHUNT_VOLTAGE = 0x01;

// --- Dataset Settings ---
const int WINDOW_SIZE = 128;                   // Uniform length required by MotorFaultCNN
const unsigned long SAMPLE_INTERVAL_US = 1200; // Rigid pacing interval
unsigned long lastSampleTimeUs = 0;
int sampleCounter = 0;

// --- Fixed Duration Controls ---
// 500 windows * 128 samples/window = 64,000 total samples.
// At 1200us per sample, this captures data for exactly 76.8 seconds (~1.28 minutes).
// This provides an excellent data distribution density for Full INT8 Quantization calibration.
const int TOTAL_WINDOWS = 500; 
const long MAX_TOTAL_SAMPLES = (long)TOTAL_WINDOWS * WINDOW_SIZE;
long totalSamplesCollected = 0;
bool collectionComplete = false;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  Wire.begin();
  Wire.setClock(400000); // 400kHz Fast I2C Mode for clean pacing
  delay(100);

  // Validate sensor presence
  Wire.beginTransmission(INA219_ADDR);
  if (Wire.endTransmission() != 0) {
    Serial.println("ERROR: INA219 not found!");
    while(1);
  }

  // Point to shunt voltage register permanently for speed
  Wire.beginTransmission(INA219_ADDR);
  Wire.write(REG_SHUNT_VOLTAGE);
  Wire.endTransmission();

  // --- 10 SECONDS INITIAL DELAY COUNTDOWN ---
  Serial.println("--- READY TO RECORD DATASET ---");
  for (int i = 10; i > 0; i--) {
    Serial.print("Starting capture loop in: ");
    Serial.print(i);
    Serial.println(" seconds...");
    delay(1000);
  }
  Serial.println("--- BEGIN DATA STREAMING ---");
  
  // Prime the clock right before entering the loop to prevent an immediate large time delta jump
  lastSampleTimeUs = micros();
}

void loop() {
  // If the target dataset volume has been filled, halt the execution loop completely
  if (collectionComplete) {
    return;
  }

  unsigned long currentTimeUs = micros();

  // Enforce uniform time interval between samples
  if ((unsigned long)(currentTimeUs - lastSampleTimeUs) >= SAMPLE_INTERVAL_US) {
    lastSampleTimeUs = currentTimeUs;

    Wire.requestFrom(INA219_ADDR, (uint8_t)2);
    if (Wire.available() >= 2) {
      uint8_t msb = Wire.read();
      uint8_t lsb = Wire.read();
      int16_t rawShuntRegister = (int16_t)((msb << 8) | lsb);
      
      // Convert to millivolts (1 LSB = 10uV = 0.01mV)
      float shunt_mV = (float)rawShuntRegister * 0.01f;

      // Print output matching your original notebook's expected shape
      Serial.print("0.0,0.0,0.0,");
      Serial.println(shunt_mV, 4);

      sampleCounter++;
      totalSamplesCollected++;

      // Print an explicit window break marker every 128 elements
      if (sampleCounter >= WINDOW_SIZE) {
        Serial.println("---WINDOW_BOUNDARY---");
        sampleCounter = 0;
      }

      // Check if we hit our overall data profile collection limit
      if (totalSamplesCollected >= MAX_TOTAL_SAMPLES) {
        collectionComplete = true;
        Serial.println("\n--- DATA COLLECTION COMPLETE ---");
        Serial.print("Collected exactly: ");
        Serial.print(totalSamplesCollected);
        Serial.print(" samples (");
        Serial.print(TOTAL_WINDOWS);
        Serial.println(" total windows).");
        Serial.println("Safe to stop your serial capture stream now.");
      }
    }
  }
}


/*
#include <Arduino_RouterBridge.h>
#include <Wire.h>

// INA219 Config
const uint8_t INA219_ADDR = 0x40;
const uint8_t REG_SHUNT_VOLTAGE = 0x01;

// Sampling parameters (same as before)
const int WINDOW_SIZE = 128;
float sampleBuffer[WINDOW_SIZE];
int bufferIndex = 0;
const unsigned long SAMPLE_INTERVAL_US = 1200;   // 1.2 ms
unsigned long lastSampleTimeUs = 0;

// Shunt resistor (Ohms) – adjust to your actual value
const float SHUNT_RESISTOR = 0.1f;   // 100 mΩ

// State machine
enum RecordState { IDLE, RECORDING };
RecordState state = IDLE;
String pendingLabel = "";

void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }

    Bridge.begin();

    // Register RPC functions (must return String)
    Bridge.provide("ping", ping);
    Bridge.provide("record_normal", record_normal);
    Bridge.provide("record_spike", record_spike);
    Bridge.provide("record_stall", record_stall);

    Serial.println("=== Data Collection System (Arduino) ===");

    Wire.begin();
    Wire.setClock(400000);
    delay(100);
    Wire.beginTransmission(INA219_ADDR);
    if (Wire.endTransmission() != 0) {
        Serial.println("INA219 not found!");
        while (1);
    }
    Wire.beginTransmission(INA219_ADDR);
    Wire.write(REG_SHUNT_VOLTAGE);
    Wire.endTransmission();

    lastSampleTimeUs = micros();
    Serial.println("Ready. Use Python script to send commands.");
}

void loop() {
    collectSamples();
    if (state == RECORDING && bufferIndex >= WINDOW_SIZE) {
        sendWindow(pendingLabel);
        state = IDLE;
        bufferIndex = 0;
        pendingLabel = "";
    }
}

void collectSamples() {
    unsigned long currentTimeUs = micros();
    if ((unsigned long)(currentTimeUs - lastSampleTimeUs) >= SAMPLE_INTERVAL_US) {
        lastSampleTimeUs = currentTimeUs;

        Wire.requestFrom(INA219_ADDR, (uint8_t)2);
        if (Wire.available() >= 2) {
            uint8_t msb = Wire.read();
            uint8_t lsb = Wire.read();
            int16_t rawShuntRegister = (int16_t)((msb << 8) | lsb);
            float shunt_mV = (float)rawShuntRegister * 0.01f;
            float current_mA = (shunt_mV / 1000.0f) / SHUNT_RESISTOR * 1000.0f;

            if (bufferIndex < WINDOW_SIZE) {
                sampleBuffer[bufferIndex] = current_mA;
                bufferIndex++;
            }
            // If buffer is full, we keep the last 128 samples until a new command resets it.
        }
    }
}

// ---- RPC Handlers ----
String ping() {
    return "pong";
}

String record_normal() {
    return startRecording("normal");
}
String record_spike() {
    return startRecording("spike");
}
String record_stall() {
    return startRecording("stall");
}

String startRecording(String label) {
    if (state == RECORDING) {
        return "ERROR: Already recording";
    }
    bufferIndex = 0;
    state = RECORDING;
    pendingLabel = label;
    Serial.print("Started recording: ");
    Serial.println(label);
    return "OK: Recording " + label;
}

void sendWindow(String label) {
    // Build data string: baseline (millis), then 128 current values
    String data = String(millis());
    for (int i = 0; i < WINDOW_SIZE; i++) {
        data += "," + String(sampleBuffer[i], 4);
    }
    // Call the appropriate Python function
    String funcName = "save_" + label + "_window";
    bool result = Bridge.call(funcName, data);
    if (result) {
        Serial.print("Window sent for label: ");
        Serial.println(label);
    } else {
        Serial.println("Failed to send window");
    }
}
*/