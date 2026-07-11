#include <Wire.h>

const uint8_t INA219_ADDR = 0x40;
const uint8_t REG_SHUNT_VOLTAGE = 0x01;

const int RELAY_PIN = 13;
const int WINDOW_SIZE = 128;                   
const unsigned long SAMPLE_INTERVAL_US = 1200; 
const int TOTAL_WINDOWS = 10; // 150 windows * 128 = 19,200 samples (~23 seconds active)

void setup() {
  Serial.begin(115200);  
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Relay initially OFF

  Wire.begin();
  Wire.setClock(400000); 
  delay(100);

  Wire.beginTransmission(INA219_ADDR);
  if (Wire.endTransmission() != 0) { while(1); }

  Wire.beginTransmission(INA219_ADDR);
  Wire.write(REG_SHUNT_VOLTAGE);
  Wire.endTransmission();

  // 20-second setup delay with relay OFF for finger positioning
  delay(20000); 
  
  // Turn Relay ON when data streaming begins
  digitalWrite(RELAY_PIN, HIGH);
  
  unsigned long lastSampleTimeUs = micros(); 
  int windowsCollected = 0;
  int sampleCounter = 0;

  while (windowsCollected < TOTAL_WINDOWS) {
    unsigned long currentTimeUs = micros();
    
    if ((unsigned long)(currentTimeUs - lastSampleTimeUs) >= SAMPLE_INTERVAL_US) {
      lastSampleTimeUs = currentTimeUs;

      unsigned long t1 = micros();
      unsigned long t2 = millis();

      Wire.requestFrom(INA219_ADDR, (uint8_t)2);
      if (Wire.available() >= 2) {
        uint8_t msb = Wire.read();
        uint8_t lsb = Wire.read();
        int16_t rawShuntRegister = (int16_t)((msb << 8) | lsb);
        float shunt_mV = (float)rawShuntRegister * 0.01f;

        Serial.print(t1);
        Serial.print(",");
        Serial.print(t2);
        Serial.print(",0.0,");
        Serial.println(shunt_mV, 4);

        sampleCounter++;
        if (sampleCounter >= WINDOW_SIZE) {
          Serial.println("---WINDOW_BOUNDARY---");
          sampleCounter = 0;
          windowsCollected++;
        }
      }
    }
  }

  // Turn Relay OFF immediately when collection completes
  digitalWrite(RELAY_PIN, LOW);
  
  // Send completion flag to signal the Python script to stop
  Serial.println("---CAPTURE_COMPLETE---");
}

void loop() {
  // Do nothing after collection finishes
}