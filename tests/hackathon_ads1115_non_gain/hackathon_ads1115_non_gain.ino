#include <Wire.h>

// ADS1115 Hardware Config
const uint8_t ADS1115_ADDR = 0x48;
const uint8_t REG_CONVERSION = 0x00;
const uint8_t REG_CONFIG     = 0x01;

// --- DFT Parameters ---
const int N = 32;             // Window size (Keep it a power of 2 for memory alignment)
int16_t sampleBuffer[N];      // Rolling audio buffer
int bufferIndex = 0;          // Track current buffer head

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  Wire.begin();
  Wire.setClock(400000);
  delay(100);

  // Initialize buffer with zeros
  for (int i = 0; i < N; i++) {
    sampleBuffer[i] = 0;
  }

  // Configure ADS1115 to Continuous 860 SPS Mode
  uint16_t configValue = 0b1100000011100011; 
  uint8_t configMSB = (uint8_t)(configValue >> 8);
  uint8_t configLSB = (uint8_t)(configValue & 0xFF);

  Wire.beginTransmission(ADS1115_ADDR);
  Wire.write(REG_CONFIG);
  Wire.write(configMSB);
  Wire.write(configLSB);
  if (Wire.endTransmission() != 0) {
    Serial.println("[CRITICAL ERROR] ADS1115 Communication Breakdown!");
    while(1);
  }

  // Lock pointer to Conversion Register
  Wire.beginTransmission(ADS1115_ADDR);
  Wire.write(REG_CONVERSION);
  Wire.endTransmission();

  Serial.println("[SUCCESS] Continuous 860 SPS Processing Node Online.");
}

void loop() {
  Wire.requestFrom(ADS1115_ADDR, (uint8_t)2);

  if (Wire.available() >= 2) {
    uint8_t msb = Wire.read();
    uint8_t lsb = Wire.read();
    int16_t rawAudio = (int16_t)((msb << 8) | lsb);

    // 1. Insert new data point into our rolling circular buffer
    sampleBuffer[bufferIndex] = rawAudio;
    bufferIndex = (bufferIndex + 1) % N;

    // 2. Compute the DFT for specific structural frequency target bins
    // Bin 0 is the DC offset (calibration drift) - We skip it entirely!
    // At 860 SPS, Bin 1 = ~27Hz, Bin 2 = ~54Hz... Bin 15 = ~400Hz (Nyquist Limit)
    
    float targetFreqEnergy = 0.0;

    // We scan across the low-mid vibration bands (Bins 2 through 10) 
    // to track changes as the motor undergoes loading friction
    for (int k = 2; k < 10; k++) {
      float realPart = 0.0;
      float imagPart = 0.0;

      for (int n = 0; n < N; n++) {
        // Find historical index placement within circular tracking limits
        int idx = (bufferIndex + n) % N;
        
        // Calculate the standard core Fourier Transform angle matrix 
        float angle = (2.0 * PI * k * n) / (float)N;
        realPart += (float)sampleBuffer[idx] * cos(angle);
        imagPart -= (float)sampleBuffer[idx] * sin(angle);
      }

      // Compute vector magnitude (total energy contained in this band)
      targetFreqEnergy += sqrt((realPart * realPart) + (imagPart * imagPart));
    }

    // 3. Output raw vs filtered data to monitor
    // Notice how the dynamic energy scale completely removes the 7k-14k shift!
    Serial.print("Raw_Signal:");
    Serial.print(rawAudio);
    Serial.print(",");
    Serial.print("Filtered_Vibration_Energy:");
    Serial.println(targetFreqEnergy);
  }

  // Exact 860 SPS timing sync
  delayMicroseconds(1160); 
}