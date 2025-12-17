// ESP32 Level 3 Sensors + MQTT publishing (telemetry + alerts)
// Paste into your sketch or use as reference. Set Wi-Fi/MQTT creds below.

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <driver/adc.h>

// ============== WIFI & MQTT CONFIG ==============
const char* WIFI_SSID     = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// MQTT broker (use mqtts:// host with port 8883 for TLS, or mqtt:// with 1883)
const char* MQTT_BROKER   = "your-broker-url"; // e.g., broker.hivemq.com
const int   MQTT_PORT     = 8883;               // 1883 if no TLS
const char* MQTT_USER     = "YOUR_MQTT_USER";   // set or leave "" if open
const char* MQTT_PASS     = "YOUR_MQTT_PASS";   // set or leave "" if open

// Topics
const char* TOPIC_TELEMETRY = "security/level3/sensors";
const char* TOPIC_ALERTS    = "security/level3/alerts";

// ============== PIN DEFINITIONS ==============
const uint8_t FLAME_SENSOR_PIN = 32;    // Stable input pin
const uint8_t GAS_SENSOR_PIN   = 34;    // ADC pin (GPIO34 = ADC1_CH6)
const uint8_t RELAY_PIN        = 27;    // Stable output pin

// ============== STATE MACHINE VARIABLES ==============
enum SystemState {
  STATE_SAFE,
  STATE_FLAME_DETECT,
  STATE_GAS_LOW,
  STATE_CRITICAL
};

SystemState currentState = STATE_SAFE;
SystemState previousState = STATE_SAFE;

// ============== TIMING & DEBOUNCING ==============
const uint16_t FLAME_DEBOUNCE = 100;      // ms
const uint16_t GAS_DEBOUNCE   = 200;      // ms
const uint16_t FLAME_STABLE_READS = 5;
const uint16_t GAS_SAMPLE_SIZE    = 10;
const uint16_t PRINT_INTERVAL     = 1500; // ms

unsigned long lastFlameChangeTime = 0;
unsigned long lastGasChangeTime   = 0;
unsigned long lastPrintTime       = 0;

uint16_t flameStableCounter = 0;
int lastFlameReading = HIGH;

// ============== GAS SENSOR CALIBRATION (REVERSED LOGIC) ==============
const float   MQ4_RO_CLEAN_AIR  = 9.83; // not used directly here
const uint16_t GAS_THRESHOLD_PPM = 500;
const uint16_t GAS_THRESHOLD_RAW = 700; // alarm when BELOW this

int gasReadingArray[GAS_SAMPLE_SIZE];
uint8_t gasReadingIndex = 0;
bool gasArrayFull = false;

// ============== STATUS FLAGS ==============
volatile bool alertActive   = false;
volatile bool relayState    = HIGH; // HIGH = OFF (fail-safe)
volatile bool flameDetected = false;
volatile bool gasLow        = false; // TRUE when gas below threshold

// ============== NETWORK & MQTT ==============
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
unsigned long lastMqttReconnect = 0;
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected, IP: " + WiFi.localIP().toString());
}

bool connectMqtt() {
  if (mqttClient.connected()) return true;
  if (millis() - lastMqttReconnect < MQTT_RECONNECT_INTERVAL) return false;
  lastMqttReconnect = millis();

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  Serial.print("Connecting to MQTT...");
  bool ok = strlen(MQTT_USER) > 0
    ? mqttClient.connect("esp32-level3", MQTT_USER, MQTT_PASS)
    : mqttClient.connect("esp32-level3");
  if (ok) {
    Serial.println("connected");
    return true;
  }
  Serial.print("failed, rc=");
  Serial.println(mqttClient.state());
  return false;
}

void publishJson(const char* topic, JsonDocument& doc) {
  char buf[512];
  size_t n = serializeJson(doc, buf);
  mqttClient.publish(topic, buf, n);
}

// ============== SENSOR PROCESSING HELPERS ==============
int calculateGasAverage() {
  long sum = 0;
  for (int i = 0; i < GAS_SAMPLE_SIZE; i++) sum += gasReadingArray[i];
  return (int)(sum / GAS_SAMPLE_SIZE);
}

void sendTelemetry(int gasRaw, int gasAvg) {
  if (!connectMqtt()) return;
  StaticJsonDocument<256> doc;
  doc["deviceId"] = "esp32-level3";
  doc["flame"] = flameDetected;
  doc["gasRaw"] = gasRaw;
  doc["gasAvg"] = gasAvg;
  doc["gasThreshold"] = GAS_THRESHOLD_RAW;
  doc["state"] = (int)currentState;
  doc["timestamp"] = millis();
  publishJson(TOPIC_TELEMETRY, doc);
}

void sendAlert(const char* reason, int gasRaw, int gasAvg) {
  if (!connectMqtt()) return;
  StaticJsonDocument<256> doc;
  doc["deviceId"] = "esp32-level3";
  doc["alert"] = reason; // "flame", "gas_low", "critical"
  doc["flame"] = flameDetected;
  doc["gasRaw"] = gasRaw;
  doc["gasAvg"] = gasAvg;
  doc["gasThreshold"] = GAS_THRESHOLD_RAW;
  doc["timestamp"] = millis();
  // doc["snapshotUrl"] = "http://your-host/snapshots/level3.jpg"; // optional
  publishJson(TOPIC_ALERTS, doc);
}

// ============== ORIGINAL LOGIC (UNCHANGED WHERE POSSIBLE) ==============
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\nESP32 DUAL SENSOR FIRE/GAS SAFETY SYSTEM - MQTT-ENABLED\n");

  pinMode(FLAME_SENSOR_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  analogSetWidth(12);
  analogSetAttenuation(ADC_11db);

  digitalWrite(RELAY_PIN, HIGH);
  relayState = HIGH;

  for (int i = 0; i < GAS_SAMPLE_SIZE; i++) gasReadingArray[i] = 0;

  connectWiFi();
  connectMqtt();
}

int gasAverageCached = 0; // to reuse in alert functions
int gasRawCached = 0;

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  connectMqtt();
  mqttClient.loop();

  updateFlameState();
  updateGasState();
  updateSystemState();
  updateRelayState();

  gasRawCached = analogRead(GAS_SENSOR_PIN);
  gasAverageCached = gasArrayFull ? calculateGasAverage() : gasRawCached;

  // Periodic telemetry
  if (millis() - lastPrintTime >= PRINT_INTERVAL) {
    sendTelemetry(gasRawCached, gasAverageCached);
    printSystemStatus();
    lastPrintTime = millis();
  }

  // Alerts on conditions (simple, can be edge-triggered if preferred)
  if (flameDetected) sendAlert("flame", gasRawCached, gasAverageCached);
  if (gasLow)        sendAlert("gas_low", gasRawCached, gasAverageCached);
  if (currentState == STATE_CRITICAL) sendAlert("critical", gasRawCached, gasAverageCached);

  delay(20);
}

// ============== FLAME SENSOR PROCESSING ==============
void updateFlameState() {
  int flameReading = digitalRead(FLAME_SENSOR_PIN);
  if (flameReading == lastFlameReading) {
    flameStableCounter++;
  } else {
    flameStableCounter = 0;
    lastFlameReading = flameReading;
  }
  if (flameStableCounter >= FLAME_STABLE_READS) {
    if (flameReading == LOW) {
      if (!flameDetected) {
        flameDetected = true;
        lastFlameChangeTime = millis();
        alertActive = true;
      }
    } else {
      if (flameDetected) {
        flameDetected = false;
        lastFlameChangeTime = millis();
        alertActive = false;
      }
    }
    flameStableCounter = 0;
  }
}

// ============== GAS SENSOR PROCESSING (REVERSED LOGIC) ==============
void updateGasState() {
  int gasRawValue = analogRead(GAS_SENSOR_PIN);
  gasReadingArray[gasReadingIndex] = gasRawValue;
  gasReadingIndex = (gasReadingIndex + 1) % GAS_SAMPLE_SIZE;
  if (gasReadingIndex == 0) gasArrayFull = true;

  if (gasArrayFull) {
    int gasAverage = calculateGasAverage();
    if (gasAverage < GAS_THRESHOLD_RAW) {
      if (!gasLow) {
        gasLow = true;
        lastGasChangeTime = millis();
        alertActive = true;
      }
    } else {
      if (gasLow) {
        gasLow = false;
        lastGasChangeTime = millis();
        alertActive = false;
      }
    }
  }
}

// ============== SYSTEM STATE MACHINE ==============
void updateSystemState() {
  SystemState newState = STATE_SAFE;
  if (flameDetected && gasLow) newState = STATE_CRITICAL;
  else if (flameDetected)      newState = STATE_FLAME_DETECT;
  else if (gasLow)             newState = STATE_GAS_LOW;
  else                         newState = STATE_SAFE;
  if (newState != currentState) {
    previousState = currentState;
    currentState = newState;
  }
}

// ============== RELAY CONTROL ==============
void updateRelayState() {
  bool newRelayState = (currentState != STATE_SAFE) ? HIGH : LOW;
  if (newRelayState != relayState) {
    relayState = newRelayState;
    digitalWrite(RELAY_PIN, relayState);
  }
}

// ============== STATUS PRINTING ==============
void printSystemStatus() {
  int flameValue = digitalRead(FLAME_SENSOR_PIN);
  int gasRawValue = analogRead(GAS_SENSOR_PIN);
  int gasAverage = gasArrayFull ? calculateGasAverage() : gasRawValue;

  Serial.print("| T: ");
  Serial.printf("%04lu ms | ", millis() % 10000);
  Serial.print("Flame: ");
  Serial.print(flameValue == LOW ? "YES" : "NO ");
  Serial.print(" | Gas: ");
  Serial.printf("%d (%s) | ", gasAverage, gasAverage < GAS_THRESHOLD_RAW ? "LOW" : "OK");
  Serial.print("State: ");
  switch (currentState) {
    case STATE_SAFE:         Serial.print("SAFE    | "); break;
    case STATE_FLAME_DETECT: Serial.print("FLAME   | "); break;
    case STATE_GAS_LOW:      Serial.print("GASLOW  | "); break;
    case STATE_CRITICAL:     Serial.print("CRIT    | "); break;
  }
  Serial.print("Relay: ");
  Serial.println(relayState == HIGH ? "OFF" : "ON");
}
