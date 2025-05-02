#include <WiFi.h>               // WiFi library for ESP32/ESP8266
#include <PubSubClient.h>        // MQTT library

// Define WiFi credentials and MQTT broker details
const char* ssid = "Dawifi";        // WiFi SSID
const char* password = "fxik2354";  // WiFi Password
const char* mqtt_server = "192.168.226.58";  // Laptop's IP (MQTT Broker)
const int mqtt_port = 1883;          // Default MQTT port

// Define MQTT topics
const char* range_topic = "bird/detection/range";      // Receives the range value
const char* deterrent_topic = "bird/detection/deterrent"; // Receives deterrent ON/OFF status
const char* buzzer_pitch_topic = "buzzer/pitch";         // Receives buzzer pitch (Hz)
const char* buzzer_activated_topic = "buzzer/activated"; // New topic to signal buzzer activation

// Define sensor and buzzer pins
const int pirPin = 3;       // PIR sensor output pin
const int buzzerPin = 11;   // Buzzer signal pin
const int triggerPin = 9;   // Ultrasonic sensor trigger pin
const int echoPin = 10;     // Ultrasonic sensor echo pin

// Define the range limit in cm
int maxDistance = 50;  
bool deterrent = true; // Default deterrent mode is ON
int buzzerPitch = 1000; // Default buzzer pitch in Hz (1000 Hz)

// Flag to check if the buzzer is already activated
bool buzzerActivated = false; 

// WiFi and MQTT clients
WiFiClient espClient;
PubSubClient client(espClient);

// Function to connect to WiFi
void setup_wifi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
}

// Function to connect to MQTT broker
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ArduinoClient")) {  
      Serial.println("Connected to MQTT broker!");

      // Subscribe to topics
      client.subscribe(range_topic);
      client.subscribe(deterrent_topic);
      client.subscribe(buzzer_pitch_topic); // New topic for buzzer pitch
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state()); 
      Serial.println(" Trying again in 5 seconds...");
      delay(5000);
    }
  }
}

// Callback function to handle received MQTT messages
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  if (String(topic) == range_topic) {
    maxDistance = message.toInt(); // Convert message to integer
    // If deterrent is off, don't print anything
    if (deterrent) {
      Serial.print("Updated max distance: ");
      Serial.println(maxDistance);
    }
  }

  if (String(topic) == deterrent_topic) {
    deterrent = (message == "true"); // Convert string to boolean
    // If deterrent is off, don't print anything
    if (deterrent) {
      Serial.print("Deterrent mode: ");
      Serial.println("ON");
    } else {
      Serial.println("Deterrent mode: OFF");
    }
  }

  if (String(topic) == buzzer_pitch_topic) {
    buzzerPitch = message.toInt(); // Convert message to integer (pitch in Hz)
    // If deterrent is off, don't print anything
    if (deterrent) {
      Serial.print("Buzzer pitch updated to: ");
      Serial.println(buzzerPitch);
    }
  }
}

// Function to get distance from ultrasonic sensor
int getUltrasonicDistance() {
  long duration;
  int distance;

  digitalWrite(triggerPin, LOW);
  delayMicroseconds(2);
  digitalWrite(triggerPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(triggerPin, LOW);

  duration = pulseIn(echoPin, HIGH);
  distance = (duration / 2) / 29.1;  // Convert to cm

  return distance;
}

// Function to publish the "true" message to MQTT when the buzzer sounds
void publishBuzzerActivation() {
  if (!buzzerActivated) {
    client.publish(buzzer_activated_topic, "true");
    Serial.println("Buzzer activated, published 'true' to buzzer/activated topic.");
    buzzerActivated = true;  // Set flag to prevent further publications
  }
}

void setup() {
  Serial.begin(9600); // Set baud rate to 9600

  setup_wifi(); // Connect to WiFi
  client.setServer(mqtt_server, mqtt_port); // Set MQTT broker
  client.setCallback(callback); // Attach callback function

  pinMode(pirPin, INPUT);       // PIR sensor as input
  pinMode(buzzerPin, OUTPUT);    // Buzzer as output
  pinMode(triggerPin, OUTPUT);   // Ultrasonic trigger as output
  pinMode(echoPin, INPUT);       // Ultrasonic echo as input

  digitalWrite(buzzerPin, LOW);  // Ensure buzzer is off

  reconnect(); // Connect to MQTT
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  
  client.loop(); // Keep MQTT communication alive

  int distance = getUltrasonicDistance();
  int motionDetected = digitalRead(pirPin);

  // If deterrent is ON, print distance and motion status
  if (deterrent) {
    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.print(" cm, Motion: ");
    Serial.println(motionDetected == HIGH ? "YES" : "NO");

    // Buzzer stays on while the conditions are met
    if (distance >= 0 && distance <= maxDistance && motionDetected == HIGH) {
      if (!buzzerActivated) {
        Serial.println("⚠️ Bird detected! Activating deterrent.");
        tone(buzzerPin, buzzerPitch);  // Activate buzzer with specified pitch
        publishBuzzerActivation();    // Publish "true" to the buzzer/activated topic
      }
    } else {
      if (buzzerActivated) {
        Serial.println("No threat detected. Deactivating deterrent.");
        noTone(buzzerPin); // Turn off buzzer when conditions are not met
        buzzerActivated = false; // Reset flag to allow future activation
      }
    }
  }

  delay(1000); // Adjust loop timing if needed
}
