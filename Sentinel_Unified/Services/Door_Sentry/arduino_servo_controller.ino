/*
 * arduino_servo_controller.ino
 * 
 * Arduino sketch for receiving servo angle commands from a PC via Serial
 * and controlling servos and motors for the safetronics security system.
 * 
 * Hardware connections:
 * - Servo 1 (Door Lock - Continuous Rotation) signal wire -> Pin 10
 * - Servo 2 (Pan/X-axis) signal wire -> Pin 9
 * - Servo 3 (Tilt/Y-axis) signal wire -> Pin 11
 * - Servo 4 (Window Lock - Continuous Rotation) signal wire -> Pin 6
 * - Shooter Motor 1 -> Pin 5
 * - Shooter Motor 2 -> Pin 4
 * - All servos power -> 5V (or external power for larger servos)
 * - All components ground -> GND
 * 
 * Serial protocol:
 * - Format: "S2,angle\n", "S3,angle\n" for positional servos
 * - Special commands: "LOCKDOWN\n", "UNLOCK\n", "FIRE\n"
 * - LOCKDOWN: Activates continuous rotation servos to close door/window
 * - UNLOCK: Activates continuous rotation servos to open door/window
 * - Single number "90\n" controls servo 2 (backward compatible)
 */

#include <Servo.h>

// Pin definitions
const int SERVO1_PIN = 10;  // Door lock servo (Continuous Rotation)
const int SERVO2_PIN = 9;   // Pan/X-axis servo
const int SERVO3_PIN = 11;  // Tilt/Y-axis servo
const int SERVO4_PIN = 6;   // Window lock servo (Continuous Rotation)
const int SHOOTER_MOTOR_PIN_1 = 5;  // Shooter motor 1
const int SHOOTER_MOTOR_PIN_2 = 4;  // Shooter motor 2

// Continuous Rotation Servo constants
const int SERVO_STOP = 90;   // Stop signal for CR servos
const int SERVO_CW = 180;    // Spin clockwise (CLOSE direction)
const int SERVO_CCW = 0;     // Spin counter-clockwise (OPEN direction)
const unsigned long DOOR_MOVE_DURATION = 2500;  // Milliseconds to fully open/close

// Lock state enumeration
enum LockState {
    IDLE,
    OPENING,
    CLOSING
};

// Servo objects
Servo doorLockServo;   // Servo 1 (Continuous Rotation)
Servo panServo;        // Servo 2
Servo tiltServo;       // Servo 3
Servo windowLockServo; // Servo 4 (Continuous Rotation)

// Buffer for incoming serial data
const int BUFFER_SIZE = 16;
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// Current servo positions (for positional servos only)
int servo2Angle = 90;  // Pan servo starts centered (90 degrees)
int servo3Angle = 90;  // Tilt servo starts centered (90 degrees)

// State management for continuous rotation servos
LockState doorState = IDLE;
LockState windowState = IDLE;
unsigned long doorStartTime = 0;
unsigned long windowStartTime = 0;

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
    
    // Initialize continuous rotation servos to STOP
    doorLockServo.write(SERVO_STOP);
    windowLockServo.write(SERVO_STOP);
    
    // Set initial positions for positional servos
    panServo.write(servo2Angle);         // Pan centered
    tiltServo.write(servo3Angle);        // Tilt centered
    
    // Clear input buffer
    memset(inputBuffer, 0, BUFFER_SIZE);
    
    // Send ready signal
    Serial.println("SERVO_READY");
    Serial.println("S1:IDLE");
    Serial.println("S2:CENTER(90)");
    Serial.println("S3:CENTER(90)");
    Serial.println("S4:IDLE");
    Serial.println("SHOOTER:OFF");
}

void loop() {
    // Non-blocking serial read
    readSerial();
    
    // Update door and window lock state machine
    updateDoorWindowLogic();
    
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
        // Start closing door and window
        doorState = CLOSING;
        windowState = CLOSING;
        doorStartTime = millis();
        windowStartTime = millis();
        
        // Start rotating servos clockwise (close direction)
        doorLockServo.write(SERVO_CW);
        windowLockServo.write(SERVO_CW);
        
        Serial.println("ACK:LOCKDOWN");
        Serial.println("S1:CLOSING");
        Serial.println("S4:CLOSING");
        return;
    }
    
    if (strcmp(command, "UNLOCK") == 0) {
        // Start opening door and window
        doorState = OPENING;
        windowState = OPENING;
        doorStartTime = millis();
        windowStartTime = millis();
        
        // Start rotating servos counter-clockwise (open direction)
        doorLockServo.write(SERVO_CCW);
        windowLockServo.write(SERVO_CCW);
        
        Serial.println("ACK:UNLOCK");
        Serial.println("S1:OPENING");
        Serial.println("S4:OPENING");
        return;
    }
    
    if (strcmp(command, "FIRE") == 0) {
        // Activate shooter motors for 500ms
        // Note: Using blocking delay as specified in requirements
        // For non-blocking implementation, use millis() timing in future version
        digitalWrite(SHOOTER_MOTOR_PIN_1, HIGH);
        digitalWrite(SHOOTER_MOTOR_PIN_2, HIGH);
        Serial.println("ACK:FIRE_START");
        delay(500);
        digitalWrite(SHOOTER_MOTOR_PIN_1, LOW);
        digitalWrite(SHOOTER_MOTOR_PIN_2, LOW);
        Serial.println("ACK:FIRE_END");
        return;
    }
    
    // Check if command format is "S2,angle" or "S3,angle" (positional servos only)
    if (command[0] == 'S' && (command[1] == '2' || command[1] == '3') && command[2] == ',') {
        // Parse servo number and angle
        int servoNum = command[1] - '0';  // Convert '2' or '3' to integer
        int angle = atoi(&command[3]);    // Parse angle after "SX,"
        
        // Validate angle range (0-180 degrees)
        if (angle >= 0 && angle <= 180) {
            if (servoNum == 2) {
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
            }
        } else {
            Serial.println("ERR:INVALID_ANGLE");
        }
    } 
    // Legacy support for S1 and S4 direct commands (ignored for CR servos)
    else if (command[0] == 'S' && (command[1] == '1' || command[1] == '4') && command[2] == ',') {
        Serial.println("ERR:USE_LOCKDOWN_OR_UNLOCK");
    }
    else {
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

void updateDoorWindowLogic() {
    // Non-blocking state machine for door lock (S1)
    if (doorState == OPENING || doorState == CLOSING) {
        if (millis() - doorStartTime >= DOOR_MOVE_DURATION) {
            // Duration elapsed - stop the servo
            doorLockServo.write(SERVO_STOP);
            
            if (doorState == OPENING) {
                Serial.println("S1:OPEN");
            } else {
                Serial.println("S1:LOCKED");
            }
            
            doorState = IDLE;
        }
    }
    
    // Non-blocking state machine for window lock (S4)
    if (windowState == OPENING || windowState == CLOSING) {
        if (millis() - windowStartTime >= DOOR_MOVE_DURATION) {
            // Duration elapsed - stop the servo
            windowLockServo.write(SERVO_STOP);
            
            if (windowState == OPENING) {
                Serial.println("S4:OPEN");
            } else {
                Serial.println("S4:LOCKED");
            }
            
            windowState = IDLE;
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
