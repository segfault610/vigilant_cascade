#include <Wire.h>
#include <string.h>

// --- INA219 Core Config ---
const uint8_t INA219_ADDR = 0x40;
const uint8_t REG_CONFIG        = 0x00;
const uint8_t REG_SHUNT_VOLTAGE = 0x01;

// --- DWT Window Config ---
const int WINDOW_SIZE = 128; // Must be a power of 2
float sampleBuffer[WINDOW_SIZE];
float tempBuffer[WINDOW_SIZE];
int bufferIndex = 0;

// --- Classification Parameters ---
// Lowered from 15.0 to 4.0 for high sensitivity to light touch/friction
const float STALL_RATIO_THRESHOLD = 4.0f; 

// Sample Pacing (INA219 updates conversions roughly every 1ms under default configuration)
const unsigned long CURRENT_SAMPLE_INTERVAL_US = 1200; 
unsigned long lastSampleTimeUs = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  Wire.begin();
  Wire.setClock(400000);
  delay(100);

  Serial.println("\n--- Initializing High-Sensitivity INA219 Direct Link ---");

  // Verify the sensor is online
  Wire.beginTransmission(INA219_ADDR);
  if (Wire.endTransmission() != 0) {
    Serial.println("[CRITICAL ERROR] INA219 failed to acknowledge!");
    while(1);
  }

  // Point the internal INA219 address register pointer to the Shunt Voltage Register
  Wire.beginTransmission(INA219_ADDR);
  Wire.write(REG_SHUNT_VOLTAGE);
  Wire.endTransmission();

  // Clear tracking history buffers
  for (int i = 0; i < WINDOW_SIZE; i++) sampleBuffer[i] = 0.0f;
  
  Serial.println("[SUCCESS] High-Sensitivity Wavelet Sentry Online.");
}

// Perform a 3-Level In-Place Pyramidal Haar DWT
void performHaarDWT(float *data, int n, float *temp) {
  const float SQRT2_INV = 0.70710678f;
  int length = n;
  
  for (int level = 0; level < 3; level++) {
    if (length <= 1) break;
    int half = length / 2;
    for (int i = 0; i < half; i++) {
      float a = data[2 * i];
      float b = data[2 * i + 1];
      temp[i]        = (a + b) * SQRT2_INV; // Coarse block changes
      temp[half + i] = (a - b) * SQRT2_INV; // Fine detailed changes
    }
    memcpy(data, temp, length * sizeof(float));
    length = half;
  }
}

void loop() {
  unsigned long currentTimeUs = micros();

  // Enforce consistent sampling cadence 
  if ((unsigned long)(currentTimeUs - lastSampleTimeUs) >= CURRENT_SAMPLE_INTERVAL_US) {
    lastSampleTimeUs = currentTimeUs;

    // Request 2 bytes from the INA219 Shunt register
    Wire.requestFrom(INA219_ADDR, (uint8_t)2);

    if (Wire.available() >= 2) {
      uint8_t msb = Wire.read();
      uint8_t lsb = Wire.read();
      int16_t rawShuntRegister = (int16_t)((msb << 8) | lsb);

      // Convert raw register values into true Shunt Millivolts (1 LSB = 0.01 mV)
      float shunt_mV = (float)rawShuntRegister * 0.01f;

      // Fill our mathematical window buffer
      sampleBuffer[bufferIndex] = shunt_mV;
      bufferIndex++;

      // When our processing frame is full, extract the sub-band features
      if (bufferIndex >= WINDOW_SIZE) {
        bufferIndex = 0; // Reset head pointer

        // Duplicate window data for in-place transform processing
        float dwtData[WINDOW_SIZE];
        memcpy(dwtData, sampleBuffer, WINDOW_SIZE * sizeof(float));

        // Compute DWT Coefficients
        performHaarDWT(dwtData, WINDOW_SIZE, tempBuffer);

        // Separate current energy signatures
        float lowFreqEnergy = 0.0f;  
        float highFreqEnergy = 0.0f; 

        for (int i = 0; i < WINDOW_SIZE; i++) {
          if (i == 0) {
            // CRITICAL UPGRADE: Skip index 0! 
            // This drops the massive static DC motor current component out of our math.
            continue; 
          }
          else if (i < 16) {
            // Transients and micro-fluctuations in speed (Macro transitions)
            lowFreqEnergy += dwtData[i] * dwtData[i];
          } else {
            // High-frequency brush noise
            highFreqEnergy += dwtData[i] * dwtData[i];
          }
        }

        // Calculate dynamic energy ratio distribution
        float energyRatio = lowFreqEnergy / (highFreqEnergy + 0.0001f);

        String motorState = "RUNNING_NORMAL";
        if (energyRatio > STALL_RATIO_THRESHOLD) {
          motorState = "SLOWED / LOADED";
        }

        // Output results straight to serial plotter/terminal links
        Serial.print("Current_LowEnergy:");  Serial.print(lowFreqEnergy, 4);   Serial.print(",");
        Serial.print("Current_HighEnergy:"); Serial.print(highFreqEnergy, 4);  Serial.print(",");
        Serial.print("Current_Ratio:");      Serial.print(energyRatio, 2);     Serial.print(",");
        Serial.print("Motor_Status:");       Serial.println(motorState);
      }
    }
  }
}

