#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); } // Wait for serial monitor

  Serial.println("\n--- Testing ADS1115 ADC & MAX9814 Microphone ---");

  // Initialize ADS1115 at standard address 0x48
  Wire.begin();
  if (!ads.begin(0x48)) {
    Serial.println("[ERROR] ADS1115 not found at address 0x48. Check your I2C wires!");
    while (1) { delay(10); } // Halt execution
  }
  Serial.println("[SUCCESS] ADS1115 online.");

  // Set gain to 2/3x to safely accommodate the microphone's peak-to-peak voltage swings
  ads.setGain(GAIN_TWOTHIRDS); 
}

void loop() {
  // Read raw 16-bit value from single-ended channel 0
  int16_t adcAudioRaw = ads.readADC_SingleEnded(0);

  // Use the Serial Plotter (Tools -> Serial Plotter) to see the acoustic wave form
  Serial.print("Audio_Raw:");
  Serial.println(adcAudioRaw);

  // Test observation: The baseline should sit somewhere near the middle of the ADC range (~12000 to 18000 depending on supply).
  // Make a sharp sound (like a clap or snap) near the mic to see the waveform ripple.
  delay(10); // Fast sampling to catch low-frequency audio variations
}