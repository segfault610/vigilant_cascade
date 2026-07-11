#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;
const pin_size_t RELAY_PIN = 13;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  

  Wire.begin();
  Wire.setClock(400000);

  if (!ads.begin(0x48, &Wire)) {
    Serial.println("ADS1115 Pin Error!");
    while(1);
  }
  ads.setGain(GAIN_TWOTHIRDS);
}

void loop() {
  int16_t adcAudioRaw = ads.readADC_SingleEnded(0);
  // Clean, single-variable stream for data logging
  Serial.print("Audio_Raw:");
  Serial.println(adcAudioRaw);
  
  delay(2); // Slightly faster polling to capture acoustic transients
}