/*
Test for the RPC bridge (i.e. for internal communication between the stm32 microcontroller and the dragonwing SoC)
One of the most important parts of the design
To use, run uv run rpc_test_main.py test script in ~/motor_monitor in the dragonwing shell
*/
#include <Arduino_RouterBridge.h>

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    Bridge.begin();
    // Register the function that Python will call
    Bridge.provide("set_led_state", set_led_state);
}

void loop() {
    static uint32_t iloop = 0;
    iloop++;
    // Call a function on the Linux side
    Bridge.call("fromQRB", iloop);
    delay(2000);
}

void set_led_state(bool state) {
    // Control the LED on the MCU
    digitalWrite(LED_BUILTIN, state ? LOW : HIGH);
}