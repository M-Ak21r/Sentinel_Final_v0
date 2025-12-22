/*
 * arduino_servo_controller_all_continuous.ino
 * 
 * Alternate firmware for systems using ALL continuous rotation servos
 * Use this when ALL four servos are continuous rotation type
 * 
 * Hardware Configuration:
 * - S1 (Pin 10): Door Lock - Continuous Rotation
 * - S2 (Pin 9):  Pan/X-axis - Continuous Rotation  
 * - S3 (Pin 11): Tilt/Y-axis - Continuous Rotation
 * - S4 (Pin 6):  Window Lock - Continuous Rotation
 * - Shooter Motor 1 (Pin 5)
 * - Shooter Motor 2 (Pin 4)
 */

#include <Servo.h>

// Pin definitions
const int SERVO1_PIN = 10;  // Door lock
const int SERVO2_PIN = 9;   // Pan/X-axis
const int SERVO3_PIN = 11;  // Tilt/Y-axis
const int SERVO4_PIN = 6;   // Window lock
const int SHOOTER_MOTOR_PIN_1 = 5;
const int SHOOTER_MOTOR_PIN_2 = 4;

// Continuous Rotation Servo constants
const int SERVO_STOP = 90;   // Stop signal
const int SERVO_CW = 180;    // Clockwise (full speed)
const int SERVO_CCW = 0;     // Counter-clockwise (full speed)

// Movement durations (milliseconds)
const unsigned long LOCK_MOVE_DURATION = 2500;    // Door/window locks
const unsigned long TURRET_MOVE_DURATION = 200;   // Short pulses for turret positioning

// Servo state enumeration
enum ServoState {
    IDLE,
    MOVING_CW,
    MOVING_CCW
};

// Servo objects
Servo servo1;  // Door lock
Servo servo2;  // Pan
Servo servo3;  // Tilt
Servo servo4;  // Window lock

// Buffer for incoming serial data
const int BUFFER_SIZE = 16;
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// State management for all servos
ServoState servo1State = IDLE;
ServoState servo2State = IDLE;
ServoState servo3State = IDLE;
ServoState servo4State = IDLE;

unsigned long servo1StartTime = 0;
unsigned long servo2StartTime = 0;
unsigned long servo3StartTime = 0;
unsigned long servo4StartTime = 0;

unsigned long servo1Duration = 0;
unsigned long servo2Duration = 0;
unsigned long servo3Duration = 0;
unsigned long servo4Duration = 0;

void setup() {
    // Initialize serial communication
    Serial.begin(9600);
    
    // Attach servos to pins
    servo1.attach(SERVO1_PIN);
    servo2.attach(SERVO2_PIN);
    servo3.attach(SERVO3_PIN);
    servo4.attach(SERVO4_PIN);
    
    // Set shooter motor pins as outputs
    pinMode(SHOOTER_MOTOR_PIN_1, OUTPUT);
    pinMode(SHOOTER_MOTOR_PIN_2, OUTPUT);
    digitalWrite(SHOOTER_MOTOR_PIN_1, LOW);
    digitalWrite(SHOOTER_MOTOR_PIN_2, LOW);
    
    // Initialize all servos to STOP
    servo1.write(SERVO_STOP);
    servo2.write(SERVO_STOP);
    servo3.write(SERVO_STOP);
    servo4.write(SERVO_STOP);
    
    // Send startup messages
    Serial.println("SERVO_READY");
    Serial.println("S1:IDLE");
    Serial.println("S2:IDLE");
    Serial.println("S3:IDLE");
    Serial.println("S4:IDLE");
    Serial.println("SHOOTER:OFF");
    Serial.println("MODE:ALL_CONTINUOUS_ROTATION");
}

void loop() {
    // Process serial input
    readSerial();
    
    // Update servo states
    updateServoLogic();
}

void readSerial() {
    while (Serial.available() > 0) {
        char inChar = (char)Serial.read();
        
        if (inChar == '\n') {
            inputBuffer[bufferIndex] = '\0';
            processCommand(inputBuffer);
            bufferIndex = 0;
        } else if (bufferIndex < BUFFER_SIZE - 1) {
            inputBuffer[bufferIndex++] = inChar;
        }
    }
}

void processCommand(char* command) {
    // Parse command
    if (command[0] == 'S' && command[2] == ',') {
        // Servo movement command: S2,+100 or S2,-50
        int servoNum = command[1] - '0';
        int direction = (command[3] == '+') ? 1 : -1;
        int duration = atoi(&command[4]);
        
        if (duration < 0) duration = -duration;  // Ensure positive
        
        if (servoNum >= 1 && servoNum <= 4 && duration > 0 && duration <= 5000) {
            moveServo(servoNum, direction, duration);
            Serial.print("ACK:S");
            Serial.print(servoNum);
            Serial.print(":");
            Serial.print((direction > 0) ? "CW:" : "CCW:");
            Serial.println(duration);
        } else {
            Serial.println("ERR:INVALID_SERVO_CMD");
        }
    }
    else if (strcmp(command, "LOCKDOWN") == 0) {
        // Lock both door and window
        moveServo(1, 1, LOCK_MOVE_DURATION);  // S1 CW
        moveServo(4, 1, LOCK_MOVE_DURATION);  // S4 CW
        Serial.println("ACK:LOCKDOWN");
    }
    else if (strcmp(command, "UNLOCK") == 0) {
        // Unlock both door and window
        moveServo(1, -1, LOCK_MOVE_DURATION);  // S1 CCW
        moveServo(4, -1, LOCK_MOVE_DURATION);  // S4 CCW
        Serial.println("ACK:UNLOCK");
    }
    else if (strcmp(command, "FIRE") == 0) {
        // Fire shooter
        digitalWrite(SHOOTER_MOTOR_PIN_1, HIGH);
        digitalWrite(SHOOTER_MOTOR_PIN_2, HIGH);
        delay(500);
        digitalWrite(SHOOTER_MOTOR_PIN_1, LOW);
        digitalWrite(SHOOTER_MOTOR_PIN_2, LOW);
        Serial.println("ACK:FIRE");
    }
    else if (strcmp(command, "STOP_ALL") == 0) {
        // Emergency stop all servos
        stopAllServos();
        Serial.println("ACK:STOP_ALL");
    }
    else {
        Serial.println("ERR:UNKNOWN_CMD");
    }
}

void moveServo(int servoNum, int direction, unsigned long duration) {
    int speed = (direction > 0) ? SERVO_CW : SERVO_CCW;
    
    switch (servoNum) {
        case 1:
            servo1.write(speed);
            servo1State = (direction > 0) ? MOVING_CW : MOVING_CCW;
            servo1StartTime = millis();
            servo1Duration = duration;
            break;
        case 2:
            servo2.write(speed);
            servo2State = (direction > 0) ? MOVING_CW : MOVING_CCW;
            servo2StartTime = millis();
            servo2Duration = duration;
            break;
        case 3:
            servo3.write(speed);
            servo3State = (direction > 0) ? MOVING_CW : MOVING_CCW;
            servo3StartTime = millis();
            servo3Duration = duration;
            break;
        case 4:
            servo4.write(speed);
            servo4State = (direction > 0) ? MOVING_CW : MOVING_CCW;
            servo4StartTime = millis();
            servo4Duration = duration;
            break;
    }
}

void updateServoLogic() {
    unsigned long currentTime = millis();
    
    // Servo 1
    if (servo1State != IDLE) {
        if (currentTime - servo1StartTime >= servo1Duration) {
            servo1.write(SERVO_STOP);
            servo1State = IDLE;
        }
    }
    
    // Servo 2
    if (servo2State != IDLE) {
        if (currentTime - servo2StartTime >= servo2Duration) {
            servo2.write(SERVO_STOP);
            servo2State = IDLE;
        }
    }
    
    // Servo 3
    if (servo3State != IDLE) {
        if (currentTime - servo3StartTime >= servo3Duration) {
            servo3.write(SERVO_STOP);
            servo3State = IDLE;
        }
    }
    
    // Servo 4
    if (servo4State != IDLE) {
        if (currentTime - servo4StartTime >= servo4Duration) {
            servo4.write(SERVO_STOP);
            servo4State = IDLE;
        }
    }
}

void stopAllServos() {
    servo1.write(SERVO_STOP);
    servo2.write(SERVO_STOP);
    servo3.write(SERVO_STOP);
    servo4.write(SERVO_STOP);
    
    servo1State = IDLE;
    servo2State = IDLE;
    servo3State = IDLE;
    servo4State = IDLE;
}
