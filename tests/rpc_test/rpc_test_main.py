from arduino.app_utils import *
import time

# This function will be called by the STM32
def fromQRB(data: int):
    print(f"Received from MCU: {data}")

Bridge.provide("fromQRB", fromQRB)

def loop():
    time.sleep(1)
    # Call a function on the STM32
    Bridge.call("set_led_state", True)

App.run(user_loop=loop)

