/*
 * arduino_servo_controller.ino
 * 
 * Arduino sketch for receiving servo angle commands from a PC via Serial
 * and controlling servos and motors for the safetronics security system.
 * 
 * Hardware connections:
 * - Servo 1 (Door Lock) signal wire -> Pin 10
 * - Servo 2 (Pan/X-axis) signal wire -> Pin 9
 * - Servo 3 (Tilt/Y-axis) signal wire -> Pin 11
 * - Servo 4 (Window Lock) signal wire -> Pin 6
 * - Shooter Motor 1 -> Pin 5
 * - Shooter Motor 2 -> Pin 4
 * - All servos power -> 5V (or external power for larger servos)
 * - All components ground -> GND
 * 
 * Serial protocol:
 * - Format: "S1,angle\n", "S2,angle\n", "S3,angle\n", or "S4,angle\n"
 * - Example: "S1,90\n" sets servo 1 (door lock) to 90 degrees
 * - Example: "S2,0\n" sets servo 2 (pan) to 0 degrees
 * - Example: "S3,90\n" sets servo 3 (tilt) to 90 degrees (center)
 * - Special commands: "LOCKDOWN\n", "UNLOCK\n", "FIRE\n"
 * - Single number "90\n" controls servo 2 (backward compatible)
 */

#include <Servo.h>

// Pin definitions
const int SERVO1_PIN = 10;  // Door lock servo
const int SERVO2_PIN = 9;   // Pan/X-axis servo
const int SERVO3_PIN = 11;  // Tilt/Y-axis servo
const int SERVO4_PIN = 6;   // Window lock servo
const int SHOOTER_MOTOR_PIN_1 = 5;  // Shooter motor 1
const int SHOOTER_MOTOR_PIN_2 = 4;  // Shooter motor 2

// Servo objects
Servo doorLockServo;   // Servo 1
Servo panServo;        // Servo 2
Servo tiltServo;       // Servo 3
Servo windowLockServo; // Servo 4

// Buffer for incoming serial data
const int BUFFER_SIZE = 16;
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// Current servo positions
int servo1Angle = 0;   // Door lock starts open (0 degrees)
int servo2Angle = 90;  // Pan servo starts centered (90 degrees)
int servo3Angle = 90;  // Tilt servo starts centered (90 degrees)
int servo4Angle = 0;   // Window lock starts open (0 degrees)

// Timing for non-blocking operations
unsigned long lastUpdateTime = 0;
const unsigned long UPDATE_INTERVAL = 20; // milliseconds

void setup() {
    // Initialize serial communication at 9600 baud
    Serial.begin(9600);
    
    // Attach servos to pins
    doorLockServo.attach(SERVO1_PIN);
    panServo.attach(SERVO2_PIN);
    tiltServo.attach(SERVO3_PIN);
    windowLockServo.attach(SERVO4_PIN);
    
    // Set shooter motor pins as outputs and initialize to OFF
    pinMode(SHOOTER_MOTOR_PIN_1, OUTPUT);
    pinMode(SHOOTER_MOTOR_PIN_2, OUTPUT);
    digitalWrite(SHOOTER_MOTOR_PIN_1, LOW);
    digitalWrite(SHOOTER_MOTOR_PIN_2, LOW);
    
    // Set initial positions
    doorLockServo.write(servo1Angle);    // Door unlocked (0 = OPEN)
    panServo.write(servo2Angle);         // Pan centered
    tiltServo.write(servo3Angle);        // Tilt centered
    windowLockServo.write(servo4Angle);  // Window unlocked (0 = OPEN)
    
    // Clear input buffer
    memset(inputBuffer, 0, BUFFER_SIZE);
    
    // Send ready signal
    Serial.println("SERVO_READY");
    Serial.println("S1:OPEN(0)");
    Serial.println("S2:CENTER(90)");
    Serial.println("S3:CENTER(90)");
    Serial.println("S4:OPEN(0)");
    Serial.println("SHOOTER:OFF");
}

void loop() {
    // Non-blocking serial read
    readSerial();
    
    // Non-blocking servo update (if needed for smooth movement)
    updateServo();
}

void readSerial() {
    // Check if data is available on serial port
    while (Serial.available() > 0) {
        char inChar = Serial.read();
        
        // Check for newline (end of command)
        if (inChar == '\n' || inChar == '\r') {
            if (bufferIndex > 0) {
                // Null-terminate the string
                inputBuffer[bufferIndex] = '\0';
                
                // Parse and process the command
                processCommand(inputBuffer);
                
                // Reset buffer
                bufferIndex = 0;
                memset(inputBuffer, 0, BUFFER_SIZE);
            }
        } else {
            // Add character to buffer if space available
            if (bufferIndex < BUFFER_SIZE - 1) {
                inputBuffer[bufferIndex] = inChar;
                bufferIndex++;
            }
        }
    }
}

void processCommand(const char* command) {
    // Check for special commands first
    if (strcmp(command, "LOCKDOWN") == 0) {
        // Lock both door and window servos
        servo1Angle = 180;
        servo4Angle = 180;
        doorLockServo.write(servo1Angle);
        windowLockServo.write(servo4Angle);
        Serial.println("ACK:LOCKDOWN");
        Serial.println("S1:LOCKED(180)");
        Serial.println("S4:LOCKED(180)");
        return;
    }
    
    if (strcmp(command, "UNLOCK") == 0) {
        // Unlock both door and window servos
        servo1Angle = 0;
        servo4Angle = 0;
        doorLockServo.write(servo1Angle);
        windowLockServo.write(servo4Angle);
        Serial.println("ACK:UNLOCK");
        Serial.println("S1:OPEN(0)");
        Serial.println("S4:OPEN(0)");
        return;
    }
    
    if (strcmp(command, "FIRE") == 0) {
        // Activate shooter motors for 500ms
        digitalWrite(SHOOTER_MOTOR_PIN_1, HIGH);
        digitalWrite(SHOOTER_MOTOR_PIN_2, HIGH);
        Serial.println("ACK:FIRE_START");
        delay(500);
        digitalWrite(SHOOTER_MOTOR_PIN_1, LOW);
        digitalWrite(SHOOTER_MOTOR_PIN_2, LOW);
        Serial.println("ACK:FIRE_END");
        return;
    }
    
    // Check if command format is "S1,angle", "S2,angle", "S3,angle", or "S4,angle"
    if (command[0] == 'S' && (command[1] >= '1' && command[1] <= '4') && command[2] == ',') {
        // Parse servo number and angle
        int servoNum = command[1] - '0';  // Convert '1', '2', '3', or '4' to integer
        int angle = atoi(&command[3]);    // Parse angle after "SX,"
        
        // Validate angle range (0-180 degrees)
        if (angle >= 0 && angle <= 180) {
            if (servoNum == 1) {
                // Control door lock servo
                servo1Angle = angle;
                doorLockServo.write(servo1Angle);
                Serial.print("ACK:S1:");
                Serial.println(servo1Angle);
            } else if (servoNum == 2) {
                // Control pan servo
                servo2Angle = angle;
                panServo.write(servo2Angle);
                Serial.print("ACK:S2:");
                Serial.println(servo2Angle);
            } else if (servoNum == 3) {
                // Control tilt servo
                servo3Angle = angle;
                tiltServo.write(servo3Angle);
                Serial.print("ACK:S3:");
                Serial.println(servo3Angle);
            } else if (servoNum == 4) {
                // Control window lock servo
                servo4Angle = angle;
                windowLockServo.write(servo4Angle);
                Serial.print("ACK:S4:");
                Serial.println(servo4Angle);
            }
        } else {
            Serial.println("ERR:INVALID_ANGLE");
        }
    } else {
        // Backward compatibility: single number controls servo 2 (pan)
        int angle = atoi(command);
        
        if (angle >= 0 && angle <= 180) {
            servo2Angle = angle;
            panServo.write(servo2Angle);
            Serial.print("ACK:S2:");
            Serial.println(servo2Angle);
        } else {
            Serial.println("ERR:INVALID_ANGLE");
        }
    }
}

void updateServo() {
    // This function can be extended for smooth movement
    // Currently servo is updated immediately in processCommand
    
    unsigned long currentTime = millis();
    
    if (currentTime - lastUpdateTime >= UPDATE_INTERVAL) {
        lastUpdateTime = currentTime;
        
        // Additional servo processing can be added here
        // For example: smooth interpolation between angles
    }
}
