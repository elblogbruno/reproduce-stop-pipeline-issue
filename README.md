This is a sample code to reproduce errors in SPI communication between an OAK D Lite and ESP32. ESP32 sends the messages to a phone by bluetooth

I want to be able to pass the hand data from hand recognition to esp32 and also the oak to receive messages from esp32 that tell the oak to stop running or run again to reduce battery usage when end user has disconnected from bluetooth.

I am running  esp32-spi-message-demo  commit `ff8d252f211dcd651b34355642bb1578718af944` 
https://github.com/luxonis/esp32-spi-message-demo/commit/ff8d252f211dcd651b34355642bb1578718af944

and depthai commit : `f83ff69db8ad9cc4fe174e59ee48ad81c59867bb`
# How to reproduce:

## Sample code

- Run `demo_learn_script.py`
- Flash `main/main.cpp` to esp32
    -  `idf.py -p <PORT> flash monitor`
- When esp32 and camera have syncronized, esp32 will show message 'Waiting for bluetooth connection'.

Here with an app like https://play.google.com/store/apps/details?id=de.kai_morich.serial_bluetooth_terminal&hl=es&gl=US connect to the generated device name on bluetooth. It should start with `DEMOBUG-xxxxx`

## Problems I have seen.

Transmission is not stable and when user connects to bluetooth and esp32 sends message to oak so it starts sending data back , after some time the oak stops sending data and esp32 tells timeout.

running the same steps before but instead of running `demo_learn_script.py` the hand demo provided here
`python .\hand-demo\demo_spi.py -e -t 1` I see the same instability in the transmission and when I disconnect from bluetooth and so esp32 sends a message to oak to stop the camera pipeline, `ctrl.setStopStreaming()
            node.io['out'].send(ctrl)` does make the camera crash or the messaging between both stop.