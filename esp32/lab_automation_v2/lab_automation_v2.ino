#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_task_wdt.h>

const char* WIFI_SSID = "CHANGE_ME";
const char* WIFI_PASSWORD = "CHANGE_ME";
const char* MQTT_HOST = "192.168.1.10";
const uint16_t MQTT_PORT = 1883;
const int RELAY_PINS[10] = {33,18,19,21,22,23,25,26,27,32};
const char* BASE = "labos/v2";
WiFiClient wifi;
PubSubClient mqtt(wifi);
unsigned long lastHeartbeat = 0;

void setRelay(int index, bool on) {
  digitalWrite(RELAY_PINS[index], on ? LOW : HIGH);
  char topic[48];
  snprintf(topic, sizeof(topic), "%s/relay/%d/state", BASE, index + 1);
  mqtt.publish(topic, on ? "ON" : "OFF", true);
}

void onMessage(char* topic, byte* payload, unsigned int length) {
  String value;
  for (unsigned int i = 0; i < length; i++) value += (char)payload[i];
  if (value != "ON" && value != "OFF") return;
  for (int i = 0; i < 10; i++) {
    String expected = String(BASE) + "/relay/" + String(i + 1) + "/set";
    if (expected == topic) setRelay(i, value == "ON");
  }
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}

void connectMqtt() {
  while (!mqtt.connected()) {
    String id = "labos-v2-esp32-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (mqtt.connect(id.c_str(), "labos/v2/controller/status", 1, true, "offline")) {
      mqtt.publish("labos/v2/controller/status", "online", true);
      for (int i = 1; i <= 10; i++) mqtt.subscribe((String(BASE) + "/relay/" + i + "/set").c_str(), 1);
    } else delay(2000);
  }
}

void setup() {
  for (int i = 0; i < 10; i++) { pinMode(RELAY_PINS[i], OUTPUT); digitalWrite(RELAY_PINS[i], HIGH); }
  esp_task_wdt_init(30, true);
  esp_task_wdt_add(NULL);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
  connectWifi();
  connectMqtt();
}

void loop() {
  connectWifi();
  connectMqtt();
  mqtt.loop();
  if (millis() - lastHeartbeat > 10000) {
    mqtt.publish("labos/v2/controller/status", "online", true);
    lastHeartbeat = millis();
  }
  esp_task_wdt_reset();
}

