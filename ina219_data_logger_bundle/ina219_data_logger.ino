/*
  INA219 training-data logger -- one-shot, fixed-duration capture for
  building labeled datasets (free-spin / loaded / near-stall / stalled).

  Sequence: finger/brake positioning delay (motor off) -> relay ON ->
  POST_START_DELAY_MS gap (motor spinning, not yet logging, letting it
  reach steady speed) -> CSV stream over Serial for RECORD_SECONDS ->
  relay OFF, done.

  Change RECORD_SECONDS before each upload depending on which state
  you're capturing -- see the accompanying capture script for the
  recommended duration per class.
*/

#include <Wire.h>

const uint8_t INA219_ADDR = 0x40;
const uint8_t REG_SHUNT_VOLTAGE = 0x01;

const int RELAY_PIN = 13;
const unsigned long SAMPLE_INTERVAL_US = 1200;  // ~833 Hz

const unsigned long POSITIONING_DELAY_MS = 20000;  // motor OFF: time to position finger/brake
const unsigned long POST_START_DELAY_MS = 20000;   // motor ON, NOT logging yet: let speed settle

// Set this per capture run: how long to actually log once recording starts.
// Keep STALLED trials short (thermal risk, not just fatigue -- see chat).
const unsigned long RECORD_SECONDS = 20;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  Wire.begin();
  Wire.setClock(400000);
  delay(100);

  Wire.beginTransmission(INA219_ADDR);
  if (Wire.endTransmission() != 0) {
    Serial.println("[CRITICAL] INA219 not found.");
    while (1) {}
  }

  Wire.beginTransmission(INA219_ADDR);
  Wire.write(REG_SHUNT_VOLTAGE);
  Wire.endTransmission();

  Serial.println("Positioning window -- motor OFF...");
  delay(POSITIONING_DELAY_MS);

  digitalWrite(RELAY_PIN, HIGH);
  Serial.println("Motor ON -- settling before recording starts...");
  delay(POST_START_DELAY_MS);

  Serial.println("Micros,Millis,Placeholder,ShuntMV");

  const unsigned long totalSamples = (RECORD_SECONDS * 1000000UL) / SAMPLE_INTERVAL_US;
  unsigned long lastSampleTimeUs = micros();
  unsigned long samplesTaken = 0;
  int sampleCounter = 0;

  while (samplesTaken < totalSamples) {
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

        samplesTaken++;
        sampleCounter++;
        if (sampleCounter >= 128) {
          Serial.println("---WINDOW_BOUNDARY---");
          sampleCounter = 0;
        }
      }
    }
  }

  digitalWrite(RELAY_PIN, LOW);
  Serial.println("---CAPTURE_COMPLETE---");
}

void loop() {
  // Nothing -- one-shot capture.
}
