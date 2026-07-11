#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;
const int RELAY_PIN = 13;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Engage motor loop

  Wire.begin();
  Wire.setClock(400000);

  if (!ina219.begin(&Wire)) {
    Serial.println("INA219 Pin Error!");
    while(1);
  }
}

void loop() {
  float shuntVoltage_mV = ina219.getShuntVoltage_mV();
  
  // Clean, single-variable stream for data logging
  Serial.print("Shunt_mV:");
  Serial.println(shuntVoltage_mV);
  
  delay(5); 
}