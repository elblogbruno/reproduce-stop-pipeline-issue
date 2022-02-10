#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "cJSON.h"

#include "esp32_spi_impl.h"
#include "spi_api.hpp"


#include "driver/gpio.h"
#include "driver/i2c.h"
#include "esp_err.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"
#include "freertos/task.h"
#include "sdkconfig.h"


// BLUETOOTH includes
#include "Arduino.h"
#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif
#define MAX_DETECTIONS 2

#include <WiFi.h>
#include <mDNS.h>
// #include <ArduinoOTA.h>

#include "config.h"  // Sustituir con datos de vuestra red
#include "ESP32_Utils.hpp"
#include "ESP32_Utils_OTA.hpp"
#include "name_utils.hpp"


static const char* METASTREAM = "spimetaout";
static const char* METASTREAM_IN = "spimetain";
static const char* PREVIEWSTREAM = "spipreview";

static const char* TAG = "DEMO";

extern "C" {
   void app_main();
}

BluetoothSerial SerialBT;


dai::SpiApi mySpiApi;
dai::Message received_msg;
bool sendImuData = true;
bool receivedStartMessage = false, shouldStop = false, shouldStart = false;


void send_message_to_oak(const char * const key, const char * const message, dai::SpiApi* mySpiApi)
{
    cJSON *root;
    root = cJSON_CreateObject();

    cJSON_AddStringToObject(root, key, message);

    char *my_json_string = cJSON_Print(root);
    
    // print my_json_string value
    ESP_LOGI(TAG, "Sending to OAK: %s\n", my_json_string);

    dai::RawBuffer buf;
    std::string str = my_json_string;
    std::vector<uint8_t> strVec(str.begin(), str.end());

    // ESP_LOGI(TAG, "strVec.size(): %d\n", strVec.size());

    buf.data = strVec;

    mySpiApi->send_message(buf, METASTREAM_IN);
}

void start_camera(){
    while(!mySpiApi.req_message(&received_msg , METASTREAM))
    {
        ESP_LOGI(TAG, "Havent received message yet\n");
        send_message_to_oak("action", "start", &mySpiApi);
    }

    ESP_LOGI(TAG, "Received message on loop shouldStart: %s\n", received_msg.raw_data.data);

    receivedStartMessage = true;
    shouldStart = false;

    SerialBT.println((char *) received_msg.raw_data.data);

    mySpiApi.free_message(&received_msg);
    mySpiApi.spi_pop_messages();
}

void stop_camera(){
    
    // if (receivedStartMessage) {
    //     mySpiApi.free_message(&received_msg);
    //     mySpiApi.spi_pop_messages();
    //     receivedStartMessage = false;
    // }

    while(!mySpiApi.req_message(&received_msg , METASTREAM))
    {
        ESP_LOGI(TAG, "Sending stop\n");
        send_message_to_oak("action", "stop", &mySpiApi);
    }

    ESP_LOGI(TAG,"Received message on loop shouldStop: %s\n", received_msg.raw_data.data);

    receivedStartMessage = false;
    shouldStop = false;

    mySpiApi.free_message(&received_msg);
    mySpiApi.spi_pop_messages();
}

void run_demo(){
    uint8_t req_success = 0;

    long  last_time = millis();
    while(1) {
        if (receivedStartMessage && sendImuData) {
            req_success = mySpiApi.req_message(&received_msg , METASTREAM);
            
            if(req_success)
            {
                ESP_LOGI(TAG,"Received message on loop: %s\n", received_msg.raw_data.data);
                
                // exampleDecodeRawMobilenet(received_msg.raw_data.data, received_msg.raw_data.size); 
                SerialBT.println((char *) received_msg.raw_data.data);

                mySpiApi.free_message(&received_msg);
                mySpiApi.spi_pop_message(METASTREAM);

                send_message_to_oak("action", "ack", &mySpiApi);
            }
            
            // check if something went wrong 
            // if(!req_success)
            // {
            //     ESP_LOGI(TAG,"Error: %d\n", req_success);
            // }
        
            // if (!req_success && millis() - last_time > 5000) {
            //     last_time = millis();

            //     ESP_LOGI(TAG, "TIMEOUT WITH CAMERA \n");

            //     while(!mySpiApi.req_message(&received_msg , METASTREAM))
            //     {
            //         ESP_LOGI(TAG, "Camera not available yet\n");
            //         send_message_to_oak("action", "timeout", &mySpiApi);
            //         sleep(1);
            //     }

            //     ESP_LOGI(TAG,"Received message on TIMEOUT: %s\n", received_msg.raw_data.data);
                
            //     mySpiApi.free_message(&received_msg);
            //     mySpiApi.spi_pop_message(METASTREAM);
            //     // mySpiApi.spi_pop_messages();
            // }
        }
        else{
            // ESP_LOGI(TAG,"No start message\n");
            // wait a little
            sleep(1);
        }

        // if (shouldStart){
        //     start_camera();
        // }

        if (shouldStop){
            stop_camera();
        }
    }
}



void callback(esp_spp_cb_event_t event, esp_spp_cb_param_t *param){
    if(event == ESP_SPP_START_EVT){
        ESP_LOGI(TAG,"Bluetooth Started event");
    }
    else if(event == ESP_SPP_SRV_OPEN_EVT){
        ESP_LOGI(TAG,"Client Connected");
        shouldStart = true;
        start_camera();
    }
    else if(event == ESP_SPP_CLOSE_EVT){
        ESP_LOGI(TAG,"Client disconnected or failed to connect");        
        shouldStop = true;
        // stop_camera();
    }
    else if(event == ESP_SPP_DATA_IND_EVT){
        ESP_LOGI(TAG,"Data received");
        while (SerialBT.available()) { // Mientras haya datos por recibir
            int incoming = SerialBT.read(); // Lee un byte de los datos recibidos
            ESP_LOGI(TAG,"Recibido: ");
            Serial.println(incoming);
            handle_received_byte(incoming);
            sendImuData = incoming != -1;
        }
    }else if(event == ESP_SPP_CONG_EVT){
        ESP_LOGI(TAG,"Connection congestion");
    }
}

void init_bluetooth(){
    String demoName =  MakeMine("Glassear-");
    Serial.println(demoName);

    SerialBT.register_callback(callback);

    if(!SerialBT.begin(demoName)){
        Serial.println("An error occurred initializing Bluetooth");
    }else{
        Serial.println("The device started, now you can pair it with bluetooth!");
    }

    mySpiApi.set_send_spi_impl(&esp32_send_spi);
    mySpiApi.set_recv_spi_impl(&esp32_recv_spi);

    sleep(1);

    dai::Message received_msg;

    while(!mySpiApi.req_message(&received_msg , METASTREAM))
    {
        ESP_LOGI(TAG, "Camera not available yet\n");
        send_message_to_oak("action", "syn", &mySpiApi);
        sleep(1);
    }

    mySpiApi.free_message(&received_msg);
    mySpiApi.spi_pop_messages();

    ESP_LOGI(TAG, "Camera initialized!\n");

}

void init_wifi(){
    ConnectWiFi_STA();

	// InitOTA();

    printWifiStatus();
}



//Main application
void app_main()
{
    initArduino();
    // init server
    // ESP_ERROR_CHECK(start_file_server());
    // init spi for the esp32
    init_esp32_spi();
    // init bluetooth
    init_bluetooth();
    // init wifi and ota
    init_wifi();
    // init imu
    // init_imu();

    ESP_LOGI(TAG, "Starting camera task. Waiting for bluetooth connection!\n");
    // run demo
    run_demo();

    //Never reached.
    deinit_esp32_spi();
}

