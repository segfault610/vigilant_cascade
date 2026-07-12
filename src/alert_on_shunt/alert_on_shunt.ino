#include <Arduino_RouterBridge.h>
#include <Wire.h>

// INA219 Config
const uint8_t INA219_ADDR = 0x40;
const uint8_t REG_SHUNT_VOLTAGE = 0x01;

// DWT Config
const int WINDOW_SIZE = 128;
float sampleBuffer[WINDOW_SIZE];
float tempBuffer[WINDOW_SIZE];
int bufferIndex = 0;
const float STALL_RATIO_THRESHOLD = 4.0f;
const unsigned long CURRENT_SAMPLE_INTERVAL_US = 1200;
unsigned long lastSampleTimeUs = 0;

// State
enum State { COLLECTING_WINDOW, ANALYZING, SENDING_WINDOW };
State currentState = COLLECTING_WINDOW;
bool windowReady = false;

// --- RPC callback for ACK from Linux ---
void receiveCommand(String command, String params) {
    Serial.print("Received command: ");
    Serial.println(command);
    if (command == "ACK") {
        Serial.println("Window received by Linux");
        currentState = COLLECTING_WINDOW;
        bufferIndex = 0;
        windowReady = false;
    }
}

// --- DWT Function ---
void performHaarDWT(float *data, int n, float *temp) {
    const float SQRT2_INV = 0.70710678f;
    int length = n;
    for (int level = 0; level < 3; level++) {
        if (length <= 1) break;
        int half = length / 2;
        for (int i = 0; i < half; i++) {
            float a = data[2 * i];
            float b = data[2 * i + 1];
            temp[i] = (a + b) * SQRT2_INV;
            temp[half + i] = (a - b) * SQRT2_INV;
        }
        memcpy(data, temp, length * sizeof(float));
        length = half;
    }
}

void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }
    
    // Initialize Bridge
    Bridge.begin();
    Bridge.provide("command", receiveCommand);
    
    Serial.println("=== STM32 Fault Detector with Bridge ===");
    
    // Setup INA219
    Wire.begin();
    Wire.setClock(400000);
    delay(100);
    
    Wire.beginTransmission(INA219_ADDR);
    if (Wire.endTransmission() != 0) {
        Serial.println("INA219 not found!");
        while(1);
    }
    
    Wire.beginTransmission(INA219_ADDR);
    Wire.write(REG_SHUNT_VOLTAGE);
    Wire.endTransmission();
    
    lastSampleTimeUs = micros();
    Serial.println("Ready! Monitoring started...");
}

void loop() {
    switch(currentState) {
        case COLLECTING_WINDOW:
            collectSamples();
            break;
        case ANALYZING:
            if (windowReady) {
                analyzeWindow();
                windowReady = false;
            }
            break;
        case SENDING_WINDOW:
            sendWindowToLinux();
            break;
    }
}

void collectSamples() {
    unsigned long currentTimeUs = micros();
    
    if ((unsigned long)(currentTimeUs - lastSampleTimeUs) >= CURRENT_SAMPLE_INTERVAL_US) {
        lastSampleTimeUs = currentTimeUs;
        
        Wire.requestFrom(INA219_ADDR, (uint8_t)2);
        if (Wire.available() >= 2) {
            uint8_t msb = Wire.read();
            uint8_t lsb = Wire.read();
            int16_t rawShuntRegister = (int16_t)((msb << 8) | lsb);
            float shunt_mV = (float)rawShuntRegister * 0.01f;
            
            sampleBuffer[bufferIndex] = shunt_mV;
            bufferIndex++;
            
            if (bufferIndex >= WINDOW_SIZE) {
                bufferIndex = 0;
                windowReady = true;
                currentState = ANALYZING;
                Serial.println("Window collected");
            }
        }
    }
}

void analyzeWindow() {
    float dwtData[WINDOW_SIZE];
    memcpy(dwtData, sampleBuffer, WINDOW_SIZE * sizeof(float));
    
    performHaarDWT(dwtData, WINDOW_SIZE, tempBuffer);
    
    float lowFreqEnergy = 0.0f;
    float highFreqEnergy = 0.0f;
    
    for (int i = 0; i < WINDOW_SIZE; i++) {
        if (i == 0) continue;
        else if (i < 16) lowFreqEnergy += dwtData[i] * dwtData[i];
        else highFreqEnergy += dwtData[i] * dwtData[i];
    }
    
    float ratio = lowFreqEnergy / (highFreqEnergy + 0.0001f);
    
    Serial.print("Ratio: ");
    Serial.println(ratio, 2);
    
    if (ratio > STALL_RATIO_THRESHOLD) {
        Serial.println("FAULT DETECTED! Sending window...");
        currentState = SENDING_WINDOW;
    } else {
        Serial.println("NORMAL");
        currentState = COLLECTING_WINDOW;
        bufferIndex = 0;
    }
}

void sendWindowToLinux() {
    Serial.println("Sending window via Bridge...");
    
    // Build CSV string: timestamp,val1,val2,...,val128
    String windowData = String(millis());
    for (int i = 0; i < WINDOW_SIZE; i++) {
        windowData += "," + String(sampleBuffer[i], 4);
    }
    
    // Call the Linux function "save_window"
    bool result = Bridge.call("save_window", windowData);
    
    if (result) {
        Serial.println("Window sent, waiting for ACK...");
        // The ACK will come via the "command" callback
    } else {
        Serial.println("Failed to send! Retrying...");
        currentState = COLLECTING_WINDOW;
        bufferIndex = 0;
    }
}