
//C4 DE E2 FB D9 68

#define DEBUG_ETHERNET_WEBSERVER_PORT Serial
#define _ETHERNET_WEBSERVER_LOGLEVEL_ 3
#define INT_GPIO 32
#define CS_GPIO 4
#include <WebServer_ESP32_W5500.h>
#include <esp_now.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <esp_wifi.h>
#include <otadrive_esp.h>

// OTA機能は開発中のため無効化
// #define APIKEY ""  // OTAdrive APIkey for this product
// #define FW_VER ""                              // this app version
/* 1.3.5 - remove buzzer sound
         - add request update firmware
   1.3.6 - change address ECDA3BBE5C98 -> ECDA3BBE61E8
   1.3.7 - add more client from [1] to [6]
   1.3.8 - add more client from wizard_bat
   1.3.9 - Nạp code mới cho Nhật
   1.4.0 - Nạp code để reset pin của máy Nhật
   1.4.1 - Development version with local MQTT broker
*/

#define u16 uint16_t
#define u32 uint32_t
#define u8 uint8_t
uint8_t newMACAddress[] = { 0xC4, 0xDE, 0xE2, 0xFB, 0xD9, 0x68 };
uint16_t Battery_wizard_counter[10] = {0,0,0,0,0,0,0,0,0,0}; // Lưu counter esp-now
uint16_t Battery_default[10] = {300,300,300,300,300,300,300,300,300,300};
uint16_t Battery_wizard[10] = {0,0,0,0,0,0,0,0,0,0}; // Lưu % pin 
const String clientESP[7] = { "ECDA3BBE61E8", "B08184044C94","188B0E936AF8","188B0E93DAD8","188B0E91ABD4","188B0E915D9C","188B0E93B5D4" };
//Battery_wizard[i] = 
typedef struct struct_message {
  int fameid;
  int id;
  int cntboot;
  float battery_per;
  bool red;
  bool yellow;
  bool green;
} struct_message;
struct_message myData;
String dataWannaSend = "";
enum statementOfMachine {
  RUN,
  STOP,
  ERROR,
  NOTWORKING
};
statementOfMachine STATE;

#include <ArduinoJson.h>

WebServer server(80);
#define NUMBER_OF_MAC 20

byte mac[][NUMBER_OF_MAC] = {
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x01 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x02 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x03 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x04 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x05 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x06 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x07 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x08 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x09 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x0A },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x0B },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x0C },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x0D },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x0E },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x0F },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x10 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x11 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x12 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x13 },
  { 0xDE, 0xAD, 0xBE, 0xEF, 0xBE, 0x14 },
};

// Select the IP address according to your local network
IPAddress myIP(192, 168, 2, 232);
IPAddress myGW(192, 168, 2, 1);
IPAddress mySN(255, 255, 255, 0);
IPAddress myDNS(8, 8, 8, 8);

#define buzzer 13
#define buzzerON digitalWrite(13, HIGH)
#define buzzerOFF digitalWrite(13, LOW)
#define led_G 14
#define led_R 27
#define led_B 26
#define led_B_OFF digitalWrite(led_B, LOW);
#define led_B_ON digitalWrite(led_B, HIGH);
#define led_G_ON digitalWrite(led_G, LOW);
#define led_G_OFF digitalWrite(led_G, HIGH);
#define led_R_ON digitalWrite(led_R, LOW);
#define led_R_OFF digitalWrite(led_R, HIGH);
int outputPin[5] = { 14, 27, 26, 25, 12 };
int inputPin[4] = { 36, 39, 34, 35 };
#define readPin [i] digitalRead(inputPin[i])
#define setPin [i] digitalWrite(outputPin[i], HIGH)
#define resetPin [i] digitalWrite(outputPin[i], LOW)


// MQTT設定 - 環境に合わせて変更してください
#define clientID "JP_LightTower_GW001"

String superStringData = "";
String defaultTopicSub = "lighttower/gateway/command";  // コマンドを受信するトピック
String defaultTopicPub = "lighttower/gateway/data";     // データを送信するトピック
const char *subMQTT = "lighttower/gateway/command";
const char *subMQTT_test = "#";

String funcDefine[10] = {
  "heartbeat", "checklimsw", "masterlock", "open_cell", "close_cell", "control_rack"
};
String bizDefine[10] = {
  "biz", "common"
};
//String nameOfCabinet = CABINET_NAME;
String langSel = "";
String transCode = "";
String client_tp = "";
String object = "";
String input[4] = { "", "", "", "" };
String dataMQTT = "";
String topicMQTT = "";
String funcRev = "";

const char *pubMQTT = "lighttower/gateway/data";
int counterCon = 0;
// WiFi設定 (ESP-NOWに必要) - 必要に応じて変更してください
const char *ssid = "";         // WiFi SSID (ESP-NOWのみ使用する場合は空でOK)
const char *password = "";     // WiFi Password
// MQTTブローカー設定 - ローカルMosquittoの場合
const char *mqtt_broker = "192.168.2.1";  // ゲートウェイのデフォルトゲートウェイ、または実際のMQTTサーバーIP
const char *mqtt_username = "";           // 認証なしの場合は空
const char *mqtt_password = "";           // 認証なしの場合は空
const int mqtt_port = 1883;
void update_FOTA();
WiFiClient ethClient;
void blinkLed(String color, int times, int delayTime);

void onUpdateProgress(int progress, int totalt);

void callback(char *topic, byte *payload, unsigned int length);
PubSubClient client(mqtt_broker, 1883, callback, ethClient);
void callback(char *topic, byte *payload, unsigned int length) {
  topicMQTT = topic;
  String dataRev = "";
  for (int i = 0; i < length; i++) {
    dataRev += (char)payload[i];
  }
  dataMQTT = dataRev.substring(0, length);
  //  Serial.println(topicMQTT);
  //  Serial.println(dataMQTT);
}


void OnDataRecv(const uint8_t *mac_addr, const uint8_t *incomingData, int len) {
  char macStr[18];
  StaticJsonDocument<200> dataJson;

  //  Serial.print("Packet received from: ");
  snprintf(macStr, sizeof(macStr), "%02x%02x%02x%02x%02x%02x",
           mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
  memcpy(&myData, incomingData, sizeof(myData));
  String addStr = "";
  addStr = String(macStr);
  addStr.toUpperCase();
  String gatewayMac = "JP:00:00:00:00:01";
  gatewayMac.replace(":", "");
  gatewayMac.toUpperCase();
  if (addStr == clientESP[0] || addStr == clientESP[1]|| addStr == clientESP[2] || addStr == clientESP[3] || addStr == clientESP[4]|| addStr == clientESP[5] || addStr == clientESP[6]   ) {
    int index_add = 0;
    for(int i = 1; i < 7; i++)
    {
      if(addStr==clientESP[i])
      {
        index_add =i;
      }
    }
    
    Battery_wizard_counter[index_add]++;
    float temp_bat = Battery_wizard_counter[index_add]/Battery_default[index_add];
    Battery_wizard[index_add] = 100-int(temp_bat);
    
    dataJson["gateway_id"] = gatewayMac;
    dataJson["addr"] = addStr;
    dataJson["error_code"] = "TMS001";
    dataJson["error"] = "Successful";
    Serial.println(addStr);
    JsonArray data = dataJson.createNestedArray("data");
    Serial.print(myData.green);
    Serial.print("\t");
    Serial.print(myData.yellow);
    Serial.print("\t");
    Serial.print(myData.red);
    Serial.print("\t");
    if (myData.red == 1 && myData.green == 0 && myData.yellow == 0) {
      STATE = RUN;
    } else if (myData.red == 0 && myData.green == 1 && myData.yellow == 0) {
      STATE = ERROR;
    } else if (myData.red == 0 && myData.green == 0 && myData.yellow == 1) {
      STATE = STOP;
    } else if (myData.red == 0 && myData.green == 0 && myData.yellow == 0) {
      STATE = NOTWORKING;
    } else {
      STATE = RUN;
    }
    switch (STATE) {
      case RUN:
        data.add("01"), data.add("Running");
        break;
      case STOP:
        data.add("02"), data.add("Stop");
        break;
      case ERROR:
        data.add("03"), data.add("Error");
        break;
      case NOTWORKING:
        data.add("00"), data.add("Not Working");
        break;
      default:
        break;
    }
    int perbat = 0;
    if(index_add==0)
    {
    perbat = int(myData.battery_per);
    
    }
    else if(index_add!=0)
    {
       perbat = Battery_wizard[index_add];
    }
    data.add(perbat);
    char dataWannaSend2mqtt[500];
    serializeJson(dataJson, dataWannaSend2mqtt);
    Serial.println(dataWannaSend2mqtt);
    client.publish(pubMQTT, dataWannaSend2mqtt);
    //  dataWannaSend2mqtt="";
    //  Serial.println();
    blinkLed("G", 1, 100);
  }
}
void pongPubMQTT(String lang)  // ok
{
  StaticJsonDocument<500> dataSend;
  dataSend["trans_code"] = transCode;
  dataSend["res_code"] = 1;
  dataSend["error_code"] = "ok";
  dataSend["error_cont"] = "JP_OK";
  JsonArray matrix = dataSend.createNestedArray("data");
  matrix.add("pong");
  char jsonString[500];
  serializeJson(dataSend, jsonString);
  client.publish(pubMQTT, jsonString);
}
void processDataMQTT() {
  StaticJsonDocument<2000> docs;
  if (dataMQTT != "" && topicMQTT == defaultTopicSub) {
    char bufferJson[2000];
    dataMQTT.toCharArray(bufferJson, 2000);
    DeserializationError error = deserializeJson(docs, String(bufferJson));
    if (error) {
      ;
    }
    String str = docs["comp_id"], langSelProcess = docs["lang"], transCodeProcess = docs["trans_code"], client_tpProcess = docs["client_tp"];
    String objectProcess = docs["object"], funcRevProcess = docs["funct"], input0Process = docs["input"][0], input1Process = docs["input"][1];
    String input2Process = docs["input"][2], input3Process = docs["input"][3];

    langSel = langSelProcess, transCode = transCodeProcess, client_tp = client_tpProcess, object = objectProcess, funcRev = funcRevProcess;
    input[0] = input0Process;  //mã tủ
    input[1] = input1Process;  //
    input[2] = input2Process;
    input[3] = input3Process;
    Serial.print("data: "), Serial.print('\t'), Serial.print(input[0]), Serial.print('\t'), Serial.print(input[1]), Serial.print('\t');
    Serial.print(input[2]), Serial.print('\t'), Serial.print(input[3]), Serial.print('\t'), Serial.println();
    if (funcRev == funcDefine[0]) {
      Serial.println("Pong Response");
      pongPubMQTT("vn");
    }
    // OTA機能は開発中のため無効化
    if(funcRev == "update_fw" && input[0] == "JP0001")
    {
      StaticJsonDocument<500> dataSend;
      dataSend["trans_code"] = transCode;
      dataSend["res_code"] = 0;
      dataSend["error_code"] = "disabled";
      dataSend["error_cont"] = "OTA update is disabled in development mode";
      JsonArray matrix = dataSend.createNestedArray("data");
      matrix.add("OTA disabled");
      char jsonString[500];
      serializeJson(dataSend, jsonString);
      client.publish(pubMQTT, jsonString);
      // delay(100);
      // ESP.restart();  // 開発中は再起動しない
    }
    dataMQTT = "", langSel = "", transCode = "", client_tp = "", object = "", funcRev = "", input[0] = "", input[1] = "", input[2] = "", input[3] = "";
  }
}
void setup() {

  gpioInit();
  Serial.begin(115200);

  while (!Serial && (millis() < 5000))
    ;
  ESP32_W5500_onEvent();
  ETH.begin(MISO_GPIO, MOSI_GPIO, SCK_GPIO, CS_GPIO, INT_GPIO, SPI_CLOCK_MHZ, ETH_SPI_HOST);
  ESP32_W5500_waitForConnect();

  WiFi.mode(WIFI_STA);
  esp_wifi_set_mac(WIFI_IF_STA, &newMACAddress[0]);
  //  Serial.print("[NEW] ESP32 Board MAC Address:  ");
  Serial.println(WiFi.macAddress());
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  esp_now_register_recv_cb(OnDataRecv);
  Serial.println("GWI001");
//  buzzerBeep(3, 100);
  mqttInit();
  char myintro[200];
  sprintf(myintro, "Light Tower Gateway \nCopyright by Bui-Van Thanh\nVersion 1.4.1 (Development)\r\n");
  Serial.print(myintro);

  // OTA機能は開発中のため無効化
  /*
  OTADRIVE.setInfo(APIKEY, FW_VER);
  OTADRIVE.onUpdateFirmwareProgress(onUpdateProgress);

#ifdef ESP8266
  if (!LittleFS.begin()) {
    Serial.println("LittleFS Mount Failed");
    LittleFS.format();
    return;
  }
#elif defined(ESP32)
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS Mount Failed");
    return;
  }
#endif
  updateInfo inf = OTADRIVE.updateFirmwareInfo();
  Serial.printf("\nfirmware info: %s ,%dBytes\n%s\n",
                inf.version.c_str(), inf.size, inf.available ? "New version available" : "No newer version");
  if (inf.available)
    OTADRIVE.updateFirmware();
  OTADRIVE.syncResources();

  listDir(OTA_FILE_SYS, "/", 0);
  String c = OTADRIVE.getConfigs();
  Serial.printf("\nconfiguration: %s\n", c.c_str());
  */

  Serial.println("Gateway initialization complete!");
}

#define MQTT_PUBLISH_INTERVAL_MS 5000L

void loop() {
  client.loop();
  if (!client.connected()) {
    Serial.println("MQTT LOST CONNECTION");
    Serial.println("reconnect to MQTT...");
    mqttInit();
  }
  processDataMQTT();
}

void blinkLed(String color, int times, int delayTime) {
  for (int i = 0; i < times; i++) {
    if (color == "G") {
      led_R_ON;
      led_G_OFF;
    } else if (color == "R") {
      led_G_ON;
      led_R_OFF;
    }
  }
}
void buzzerBeep(int times, int delayTime) {
  for (int i = 0; i < times; i++) {
    buzzerON;
    delay(delayTime / 2);
    buzzerOFF;
    delay(delayTime / 2);
  }
}
void gpioInit() {
  pinMode(buzzer, OUTPUT);
//  buzzerBeep(1, 100);
  pinMode(led_G, OUTPUT);
  blinkLed("G", 1, 100);
  pinMode(led_G, OUTPUT);
  blinkLed("R", 1, 100);
  for (int i = 0; i < 5; i++) {
    pinMode(outputPin[i], OUTPUT);
    digitalWrite(outputPin[i], LOW);
  }
  for (int i = 0; i < 4; i++) {
    pinMode(inputPin[i], INPUT_PULLUP);
  }
}
void mqttInit() {
  Serial.println("connecting to broker");
  delay(200);
  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);
  while (!client.connected()) {

    String client_id = clientID;
    client_id += String(random(0xffff), HEX);
    if (client.connect(client_id.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("Connected to MQTT server");
      client.subscribe(subMQTT);
      counterCon = 0;

    } else {
//      buzzerBeep(2, 200);
      blinkLed("R", 1, 100);
      Serial.print("failed, rc=");
      Serial.println(client.state());
      delay(1500);
    }
  }
  delay(500);
}
void onUpdateProgress(int progress, int totalt) {
  static int last = 0;
  int progressPercent = (100 * progress) / totalt;
  Serial.print("*");
  if (last != progressPercent && progressPercent % 10 == 0) {
    Serial.printf("%d", progressPercent);
  }
  last = progressPercent;
}
void listDir(fs::FS &fs, const char *dirname, uint8_t levels) {
  Serial.printf("Listing directory: %s\r\n", dirname);

  File root = fs.open(dirname, "r");
  if (!root) {
    Serial.println("- failed to open directory");
    return;
  }
  if (!root.isDirectory()) {
    Serial.println(" - not a directory");
    return;
  }

  File file = root.openNextFile();
  while (file) {
    if (file.isDirectory()) {
      Serial.print("  DIR : ");
      Serial.println(file.name());
      if (levels) {
        listDir(fs, file.name(), levels - 1);
      }
    } else {
      Serial.print("  FILE: ");
      Serial.print(file.name());
      Serial.print("\tSIZE: ");
      Serial.println(file.size());
    }
    file = root.openNextFile();
  }
}
