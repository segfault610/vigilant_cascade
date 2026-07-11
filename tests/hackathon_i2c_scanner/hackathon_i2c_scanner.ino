#include <Wire.h>
#include <Adafruit_INA219.h>
#include <Adafruit_ADS1X15.h>

// Instantiate sensor drivers
Adafruit_INA219 ina219;
Adafruit_ADS1115 ads;

const int RELAY_PIN = 22;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); } // Wait for serial monitor to connect

  Serial.println("\n--- Launching Vigilant Cascade Unified Suite ---");

  // 1. Fire up the high-power loop switch
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);
  Serial.println("[SYSTEM] Relay closed. Power delivered to motor block.");

  // 2. Initialize the Primary I2C Bus (Top-Right SDA/SCL Pins)
  Wire.begin();
  Wire.setClock(400000); // 400kHz fast I2C mode for high-frequency sampling

  // 3. Mount the INA219 current sensor on the primary Wire bus (Default 0x40)
  if (!ina219.begin(&Wire)) {
    Serial.println("[CRITICAL ERROR] INA219 current sensor missing from Top Header Pins!");
    while(1);
  }
  Serial.println("[SUCCESS] INA219 initialized on Top Header Bus.");

  // 4. Mount the ADS1115 Audio ADC on the primary Wire bus (Default 0x48)
  if (!ads.begin(0x48, &Wire)) {
    Serial.println("[CRITICAL ERROR] ADS1115 Audio ADC missing from Top Header Pins!");
    while(1);
  }
  Serial.println("[SUCCESS] ADS1115 initialized on Top Header Bus.");
  
  // Set gain to 2/3 to map the full 3.3V dynamic window of the MAX9814 mic safely
  ads.setGain(GAIN_TWOTHIRDS); 
  
  Serial.println("--- System Active. Streaming Sensor Matrices ---");
}

void loop() {
  // Capture instantaneous telemetry frames from the top header bus
  float shuntVoltage_mV = ina219.getShuntVoltage_mV();
  int16_t adcAudioRaw = ads.readADC_SingleEnded(0);

  // Print in Telemetry Formatter (Compatible with Arduino Serial Plotter)
  Serial.print("Current_Shunt_mV:");
  Serial.print(shuntVoltage_mV);
  Serial.print(",");
  Serial.print("Acoustic_Mic_Raw:");
  Serial.println(adcAudioRaw);

  // 2ms delay targets roughly 500Hz sampling loop baseline
  delay(2); 
}