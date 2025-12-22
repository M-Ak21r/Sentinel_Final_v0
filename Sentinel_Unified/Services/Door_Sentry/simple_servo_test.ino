/*
 * simple_servo_test.ino
 * 
 * Simple test sketch to verify servo functionality on Pin 10
 * Use this to test if your servo is working before using the full firmware
 * 
 * Upload this sketch, open Serial Monitor at 9600 baud, and type angles 0-180
 */

#include <Servo.h>

Servo testServo;
const int SERVO_PIN = 10;  // Change this to test different pins

// Buffer for serial input
String inputString = "";
boolean stringComplete = false;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Attach servo to pin
  testServo.attach(SERVO_PIN);
  
  // Move to center position
  testServo.write(90);
  
  // Print instructions
  Serial.println("====================================");
  Serial.println("Simple Servo Test - Pin 10");
  Serial.println("====================================");
  Serial.println("Servo attached and centered at 90°");
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  0-180   : Move to specific angle");
  Serial.println("  sweep   : Perform sweep test");
  Serial.println("  center  : Return to center (90°)");
  Serial.println();
  Serial.println("Ready. Enter command:");
}

void loop() {
  // Check for serial input
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
  
  // Process complete command
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
}

void processCommand(String command) {
  command.trim();
  command.toLowerCase();
  
  if (command == "sweep") {
    performSweep();
  } else if (command == "center") {
    testServo.write(90);
    Serial.println("Moved to center (90°)");
  } else {
    // Try to parse as angle
    int angle = command.toInt();
    
    if (angle >= 0 && angle <= 180) {
      testServo.write(angle);
      Serial.print("Moved to angle: ");
      Serial.print(angle);
      Serial.println("°");
    } else {
      Serial.println("Invalid command. Use 0-180, 'sweep', or 'center'");
    }
  }
}

void performSweep() {
  Serial.println("Starting sweep test...");
  
  // Sweep from 0 to 180
  Serial.println("  Sweeping 0° → 180°");
  for (int angle = 0; angle <= 180; angle += 5) {
    testServo.write(angle);
    delay(50);
  }
  
  delay(500);
  
  // Sweep back from 180 to 0
  Serial.println("  Sweeping 180° → 0°");
  for (int angle = 180; angle >= 0; angle -= 5) {
    testServo.write(angle);
    delay(50);
  }
  
  // Return to center
  testServo.write(90);
  Serial.println("Sweep complete. Returned to center.");
}
