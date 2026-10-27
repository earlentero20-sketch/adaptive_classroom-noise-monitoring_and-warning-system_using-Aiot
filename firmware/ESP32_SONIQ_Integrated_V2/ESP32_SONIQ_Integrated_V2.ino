
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>
#include <math.h>

// ======================================
// 1. WIFI AND SONIQ BACKEND
// ======================================

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* SERVER_URL =
  "http://192.168.1.3:8000/api/v1/events";

const char* DEVICE_ID = "ESP32_CLASSROOM_01";

// ======================================
// 2. HARDWARE PINS
// ======================================

#define I2S_WS 25
#define I2S_SCK 26
#define I2S_SD 33

#define GREEN_LED 18
#define YELLOW_LED 19
#define RED_LED 21

#define BUZZER_PIN 23

// ======================================
// 3. NOISE AND WARNING SETTINGS
// ======================================

// These are normalized RMS thresholds,
// NOT calibrated dB SPL values.
const float QUIET_THRESHOLD = 0.008f;
const float LOUD_THRESHOLD = 0.025f;

const int SAMPLE_RATE = 16000;
const int SAMPLE_COUNT = 512;

const unsigned long SEND_INTERVAL_MS = 2000;
const unsigned long WIFI_RETRY_MS = 10000;

const unsigned long BUZZER_DELAY_MS = 5000;

// Backend authorization must remain fresh.
// Must exceed normal 2-second event interval.
const unsigned long RESPONSE_TIMEOUT_MS = 4500;

// IMPORTANT:
// Do not enable physical buzzer operation until
// the complete backend/ML/calibration system
// and end-to-end safety tests are ready.
const bool ENABLE_PHYSICAL_BUZZER = false;

// ======================================
// 4. GLOBAL VARIABLES
// ======================================

float rmsValue = 0.0f;
String noiseLevel = "QUIET";

bool microphoneReady = false;
bool buzzerReady = false;
bool buzzerActive = false;

bool backendWarningAuthorized = false;
bool warningTimerRunning = false;

unsigned long warningStartTime = 0;
unsigned long lastAuthorizedResponseTime = 0;

unsigned long lastSendTime = 0;
unsigned long lastWiFiAttempt = 0;

uint32_t eventCounter = 0;

// ======================================
// 5. MICROPHONE INITIALIZATION
// ======================================

bool setupMicrophone() {
  i2s_config_t config = {};

  config.mode = (i2s_mode_t)(
    I2S_MODE_MASTER | I2S_MODE_RX
  );

  config.sample_rate = SAMPLE_RATE;
  config.bits_per_sample =
    I2S_BITS_PER_SAMPLE_32BIT;

  config.channel_format =
    I2S_CHANNEL_FMT_ONLY_LEFT;

  config.communication_format =
    I2S_COMM_FORMAT_STAND_I2S;

  config.intr_alloc_flags = 0;
  config.dma_buf_count = 4;
  config.dma_buf_len = 256;
  config.use_apll = false;
  config.tx_desc_auto_clear = false;
  config.fixed_mclk = 0;

  i2s_pin_config_t pins = {};

  pins.bck_io_num = I2S_SCK;
  pins.ws_io_num = I2S_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = I2S_SD;

  esp_err_t result = i2s_driver_install(
    I2S_NUM_0,
    &config,
    0,
    NULL
  );

  if (result != ESP_OK) {
    Serial.println("I2S driver installation failed");
    return false;
  }

  result = i2s_set_pin(I2S_NUM_0, &pins);

  if (result != ESP_OK) {
    Serial.println("I2S pin setup failed");
    i2s_driver_uninstall(I2S_NUM_0);
    return false;
  }

  i2s_zero_dma_buffer(I2S_NUM_0);

  Serial.println("INMP441 initialized");
  return true;
}

// ======================================
// 6. READ MICROPHONE RMS
// ======================================

float readMicrophoneRMS() {
  int32_t samples[SAMPLE_COUNT];
  size_t bytesRead = 0;

  esp_err_t result = i2s_read(
    I2S_NUM_0,
    samples,
    sizeof(samples),
    &bytesRead,
    pdMS_TO_TICKS(100)
  );

  if (result != ESP_OK || bytesRead == 0) {
    return NAN;
  }

  int count = bytesRead / sizeof(int32_t);

  if (count <= 0) {
    return NAN;
  }

  double sumSquares = 0.0;

  for (int i = 0; i < count; i++) {
    int32_t sample24 = samples[i] >> 8;

    float normalized =
      (float)sample24 / 8388608.0f;

    sumSquares +=
      (double)normalized * normalized;
  }

  return sqrt(sumSquares / count);
}

// ======================================
// 7. BUZZER AND WARNING CONTROL
// ======================================

void keepBuzzerOff() {
  if (buzzerReady) {
    ledcWriteTone(BUZZER_PIN, 0);
  }

  buzzerActive = false;
}

void resetBackendWarning() {
  backendWarningAuthorized = false;
  warningTimerRunning = false;
  warningStartTime = 0;
  lastAuthorizedResponseTime = 0;

  keepBuzzerOff();
}

void processBackendWarning(bool authorized) {
  unsigned long now = millis();

  if (!authorized) {
    resetBackendWarning();

    Serial.println(
      "SONIQ WARNING: NOT AUTHORIZED"
    );
    return;
  }

  // This is an authorization response,
  // not permission to bypass hardware safeguards.
  backendWarningAuthorized = true;
  lastAuthorizedResponseTime = now;

  if (!warningTimerRunning) {
    warningTimerRunning = true;
    warningStartTime = now;

    Serial.println(
      "SONIQ WARNING: 5-second timer started"
    );
  }
}

void updateBuzzerSafety() {
  unsigned long now = millis();

  if (!microphoneReady ||
      WiFi.status() != WL_CONNECTED) {
    resetBackendWarning();
    return;
  }

  if (!backendWarningAuthorized ||
      !warningTimerRunning) {
    keepBuzzerOff();
    return;
  }

  if (now - lastAuthorizedResponseTime >
      RESPONSE_TIMEOUT_MS) {

    Serial.println(
      "SONIQ WARNING: authorization expired"
    );

    resetBackendWarning();
    return;
  }

  if (now - warningStartTime <
      BUZZER_DELAY_MS) {
    keepBuzzerOff();
    return;
  }

  // Physical buzzer remains locked until
  // full system validation is complete.
  if (!ENABLE_PHYSICAL_BUZZER || !buzzerReady) {
    keepBuzzerOff();
    return;
  }

  if (!buzzerActive) {
    ledcWriteTone(BUZZER_PIN, 2000);
    buzzerActive = true;

    Serial.println("SONIQ WARNING: BUZZER ON");
  }
}

// ======================================
// 8. LOCAL LED INDICATORS
// ======================================

void updateLEDs(float rms) {
  if (rms < QUIET_THRESHOLD) {
    noiseLevel = "QUIET";

    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(RED_LED, LOW);
  }
  else if (rms < LOUD_THRESHOLD) {
    noiseLevel = "MODERATE";

    digitalWrite(GREEN_LED, LOW);
    digitalWrite(YELLOW_LED, HIGH);
    digitalWrite(RED_LED, LOW);
  }
  else {
    noiseLevel = "LOUD";

    digitalWrite(GREEN_LED, LOW);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(RED_LED, HIGH);
  }
}

// ======================================
// 9. WIFI CONNECTION
// ======================================

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");

  unsigned long startTime = millis();

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - startTime < 15000
  ) {
    delay(250);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected!");

    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  }
  else {
    Serial.println("WiFi connection failed");
  }

  lastWiFiAttempt = millis();
}

// ======================================
// 10. SEND EVENT AND READ BACKEND RESPONSE
// ======================================

void sendEventToSONIQ() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi offline; event skipped");
    resetBackendWarning();
    return;
  }

  WiFiClient client;
  HTTPClient http;

  http.setTimeout(3000);

  if (!http.begin(client, SERVER_URL)) {
    Serial.println("HTTP initialization failed");
    resetBackendWarning();
    return;
  }

  http.addHeader(
    "Content-Type",
    "application/json"
  );

  eventCounter++;

  static uint32_t bootId = esp_random();

  String eventId =
    String(DEVICE_ID) + "_" +
    String(bootId, HEX) + "_" +
    String(eventCounter);

  // The ESP32 does not yet have:
  // 1. Valid AI classification
  // 2. Calibrated dB SPL measurement
  //
  // Do not substitute RMS for dB SPL.

  JsonDocument event;

  event["schema_version"] = "1.0";
  event["event_id"] = eventId;
  event["device_id"] = DEVICE_ID;
  event["sensor_status"] = "online";

  event["classification"]["label"] = nullptr;
  event["classification"]["confident"] = false;
  event["classification"]["observed_at"] = nullptr;

  event["sound_level"]["value"] = nullptr;
  event["sound_level"]["unit"] = nullptr;
  event["sound_level"]["calibrated"] = false;
  event["sound_level"]["observed_at"] = nullptr;

  String json;
  serializeJson(event, json);

  Serial.println("Sending SONIQ event:");
  Serial.println(json);

  int responseCode = http.POST(json);

  Serial.print("HTTP Response: ");
  Serial.println(responseCode);

  if (responseCode >= 200 && responseCode < 300) {
    String response = http.getString();

    Serial.println("SONIQ response:");
    Serial.println(response);

    JsonDocument doc;

    DeserializationError error =
      deserializeJson(doc, response);

    if (error) {
      Serial.println(
        "ERROR: Invalid backend JSON"
      );

      resetBackendWarning();
    }
    else {
      const char* schema =
        doc["schema_version"] | "";

      const char* responseEventId =
        doc["event_id"] | "";

      const char* responseDeviceId =
        doc["device_id"] | "";

      const char* backendStatus =
        doc["connection_status"]["backend"] | "";

      const char* sensorStatus =
        doc["connection_status"]["sensor"] | "";

      bool warningFieldValid =
        doc["warning"]["triggered"].is<bool>();

      bool validResponse =
        String(schema) == "1.0" &&
        String(responseEventId) == eventId &&
        String(responseDeviceId) == DEVICE_ID &&
        String(backendStatus) == "online" &&
        String(sensorStatus) == "online" &&
        warningFieldValid;

      if (!validResponse) {
        Serial.println(
          "ERROR: Backend response validation failed"
        );

        resetBackendWarning();
      }
      else {
        bool authorized =
          doc["warning"]["triggered"].as<bool>();

        processBackendWarning(authorized);

        Serial.println(
          "SONIQ EVENT SENT SUCCESSFULLY"
        );
      }
    }
  }
  else {
    if (responseCode < 0) {
      Serial.print("HTTP request failed: ");
      Serial.println(
        http.errorToString(responseCode)
      );
    }
    else {
      Serial.println(
        "SONIQ rejected the event"
      );
    }

    resetBackendWarning();
  }

  http.end();
}

// ======================================
// 11. SETUP
// ======================================

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("==========================");
  Serial.println("SONIQ INTEGRATED FIRMWARE V2");
  Serial.println("==========================");

  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  digitalWrite(GREEN_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(RED_LED, LOW);

  buzzerReady = ledcAttach(
    BUZZER_PIN, 2000, 8
  );

  if (!buzzerReady) {
    Serial.println(
      "Buzzer PWM setup failed"
    );
  }

  resetBackendWarning();

  microphoneReady = setupMicrophone();

  if (!microphoneReady) {
    Serial.println(
      "ERROR: Microphone unavailable"
    );
  }

  connectWiFi();

  Serial.println("SONIQ setup complete");
}

// ======================================
// 12. MAIN LOOP
// ======================================

void loop() {
  unsigned long now = millis();

  if (
    WiFi.status() != WL_CONNECTED &&
    now - lastWiFiAttempt >= WIFI_RETRY_MS
  ) {
    lastWiFiAttempt = now;
    WiFi.reconnect();
  }

  // Immediately enforce backend safety rules.
  updateBuzzerSafety();

  if (microphoneReady) {
    float newRMS = readMicrophoneRMS();

    if (!isnan(newRMS)) {
      rmsValue = newRMS;
      updateLEDs(rmsValue);

      Serial.print("RMS: ");
      Serial.print(rmsValue, 6);

      Serial.print(" | Level: ");
      Serial.print(noiseLevel);

      Serial.print(" | Buzzer: ");
      Serial.println(
        buzzerActive ? "ON" : "OFF"
      );
    }
    else {
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(YELLOW_LED, LOW);
      digitalWrite(RED_LED, LOW);

      resetBackendWarning();

      Serial.println(
        "Microphone read failed"
      );
    }
  }
  else {
    resetBackendWarning();
  }

  if (
    millis() - lastSendTime >= SEND_INTERVAL_MS
  ) {
    lastSendTime = millis();

    if (microphoneReady) {
      sendEventToSONIQ();
    }
  }

  // Recheck after any potentially blocking HTTP call.
  updateBuzzerSafety();

  delay(20);
}
