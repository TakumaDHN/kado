
#include <esp_now.h>
#include <WiFi.h>
#include "DFRobot_MAX17043.h"
#include "Wire.h"
#include <esp_wifi.h>
#ifdef __AVR__
#define ALR_PIN       2
#else
#define ALR_PIN       D2
#endif

DFRobot_MAX17043        gauge;
uint8_t       intFlag = 0;

#define GPin D1
#define YPin D2
#define RPin D3

#define idOfDevice 1

#define uS_TO_S_FACTOR 1000000  /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP  57       /* Time ESP32 will go to sleep (in seconds) */
uint8_t broadcastAddress[] = {0xc4, 0xde, 0xe2, 0xfb, 0xd9, 0x68};

#define onehundredperBat 4.0

RTC_DATA_ATTR int _wizard_variables = 0;
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR int startRun = 0;
RTC_DATA_ATTR int _Vbat = 0;
RTC_DATA_ATTR int counterWakeup = 0;
RTC_DATA_ATTR int stateOfMachine = 0; // State == 1 -> Change state, State == 0 -> unchanguue state // if State == 1 and counter %10 !=0 -> counter ++ &&  send data
RTC_DATA_ATTR unsigned char _pre_inputDigital[3] = {1, 1, 1};
unsigned char _cur_inputDigital[3] = {0, 0, 0};
uint8_t inputPin[3] = {GPin, YPin, RPin};
uint8_t _percentage_always = 100;
typedef struct struct_message {
  int fameid; // must be unique for each sender board
  int id;
  int cntboot;
  float battery_per;
  bool red;
  bool yellow;
  bool green;
} struct_message;

struct_message myData;

esp_now_peer_info_t peerInfo;

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}


void setup() {
  uint8_t _Vbat = 0;
  pinMode(0, INPUT);         // AD
  pinMode(1, INPUT);
  pinMode(2, INPUT);
//  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  uint16_t sensorValue[3] = {0, 0, 0};
  uint8_t analogPin[3] = {A0, A1, A2};
  for (int i = 0; i < 3; i ++)
  {
    if (analogRead(analogPin[i]) > 1000)
    {
      _cur_inputDigital[i] = 1;
    }
    else if (analogRead(analogPin[i]) < 1000)
    {
      _cur_inputDigital[i] = 0;
    }
  }
  if (_cur_inputDigital[0] != _pre_inputDigital[0] ||
      _cur_inputDigital[1] != _pre_inputDigital[1] ||
      _cur_inputDigital[2] != _pre_inputDigital[2]) {
    stateOfMachine  = 1;
    _pre_inputDigital[0] = _cur_inputDigital[0];
    _pre_inputDigital[1] = _cur_inputDigital[1];
    _pre_inputDigital[2] = _cur_inputDigital[2];
  }
  if (bootCount > 60 || startRun <3)
  {
//   _Vbat =  int(_percentage_always - (_wizard_variables /1500));

    while (gauge.begin() != 0);
    delay(2);
    float vb = 0;
    while (vb == 0)
    {
      vb = gauge.readPercentage();
     _Vbat =  constrain( map(int(vb), 40, 140, 0, 100), 0, 100);
     (_Vbat > 100) ? 100 : _Vbat;
    }
    bootCount = 0;
  }
  
  if (stateOfMachine == 1 || bootCount < 3)
  {
    myData.id = idOfDevice;
    myData.fameid = bootCount;
    myData.battery_per = _Vbat;
    myData.red = _cur_inputDigital[1];
    myData.green = _cur_inputDigital[0];
    myData.yellow = _cur_inputDigital[2];
    ++counterWakeup;
    if (esp_now_init() != ESP_OK) {
      return;
    }
    esp_now_register_send_cb(OnDataSent);

    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    // Connect with gateway
    if (esp_now_add_peer(&peerInfo) == ESP_OK) {
      // connected to gateway
      esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &myData, sizeof(myData));
      if (result == ESP_OK) {
      }
    }
    stateOfMachine = 0;
  }
  delay(1);
  _wizard_variables++;
  bootCount++;
  startRun++;
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  delay(1);
  esp_deep_sleep_start();
}

void loop() {
//
//   uint16_t sensorValue[3] = {0, 0, 0};
//  uint8_t analogPin[3] = {A0, A1, A2};
//  for (int i = 0; i < 3; i ++)
//  {
//    if (analogRead(analogPin[i]) > 1000)
//    {
//      _cur_inputDigital[i] = 1;
//    }
//    else if (analogRead(analogPin[i]) < 1000)
//    {
//      _cur_inputDigital[i] = 0;
//    }
//  }
//  if (_cur_inputDigital[0] != _pre_inputDigital[0] ||
//      _cur_inputDigital[1] != _pre_inputDigital[1] ||
//      _cur_inputDigital[2] != _pre_inputDigital[2]) {
//    stateOfMachine  = 1;
//    _pre_inputDigital[0] = _cur_inputDigital[0];
//    _pre_inputDigital[1] = _cur_inputDigital[1];
//    _pre_inputDigital[2] = _cur_inputDigital[2];
//  }
//  if (bootCount > 60 || startRun <3)
//  {
//    while (gauge.begin() != 0);
//    delay(2);
//    float vb = 0;
//    while (vb == 0)
//    {
//      vb = gauge.readPercentage();
//      _Vbat = int(vb);
//
//    }
//    bootCount = 0;
//  }
//  
//  if (stateOfMachine == 1 || bootCount < 3)
//  {
//    myData.id = idOfDevice;
//    myData.fameid = bootCount;
//    myData.battery_per = _Vbat;
//    myData.red = _cur_inputDigital[1];
//    myData.green = _cur_inputDigital[0];
//    myData.yellow = _cur_inputDigital[2];
//    ++counterWakeup;
//    if (esp_now_init() != ESP_OK) {
//      return;
//    }
//    esp_now_register_send_cb(OnDataSent);
//
//    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
//    peerInfo.channel = 0;
//    peerInfo.encrypt = false;
//    // Connect with gateway
//    if (esp_now_add_peer(&peerInfo) == ESP_OK) {
//      // connected to gateway
//      esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &myData, sizeof(myData));
//      if (result == ESP_OK) {
//      }
//    }
//    stateOfMachine = 0;
//  }
//  Serial.println("OK");
//  
//  delay(5000);

      
}
