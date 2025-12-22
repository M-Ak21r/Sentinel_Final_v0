/*
 * Sentinel Unified - Arduino Servo & Motor Controller
 * =====================================================
 * 
 * This sketch receives commands via Serial and controls:
 * - S1 (Pin 10): Door lock servo (continuous rotation)
 * - S2 (Pin 9):  Pan servo (continuous rotation)
 * - S3 (Pin 11): Tilt servo (continuous rotation)
 * - S4 (Pin 6):  Window lock servo (continuous rotation)
 * - Shooter motors (Pins 4, 5)
 * 
 * Serial Protocol (9600 baud):
 * - "S1,+2500"  - Rotate servo 1 CW for 2500ms (then stop)
 * - "S2,-1500"  - Rotate servo 2 CCW for 1500ms (then stop)
 * - "LOCKDOWN"  - Lock door (S1) and window (S4)
 * - "UNLOCK"    - Unlock door (S1)
 * - "FIRE"      - Activate shooter motors for 500ms
 * - "STOP_ALL"  - Stop all servos and motors immediately
 * 
 * Continuous Rotation Servo Notes:
 * - 90 = stop
 * - 0-89 = one direction (speed varies)
 * - 91-180 = other direction (speed varies)
 * - Full speed CW: 180, Full speed CCW: 0
 */

#include <Servo.h>

// Servo pin definitions
#define SERVO1_PIN 10   // Door lock
#define SERVO2_PIN 9    // Pan (turret horizontal)
#define SERVO3_PIN 11   // Tilt (turret vertical)
#define SERVO4_PIN 6    // Window lock

// Shooter motor pin definitions
#define SHOOTER_PIN1 4
#define SHOOTER_PIN2 5

// Servo speed constants (for continuous rotation)
#define SERVO_STOP 90
#define SERVO_CW_FULL 180
#define SERVO_CCW_FULL 0
#define SERVO_CW_SLOW 120
#define SERVO_CCW_SLOW 60

// Timing constants
#define LOCK_DURATION_MS 2500    // Half-cycle for door/window lock
#define FIRE_DURATION_MS 500     // Shooter activation time
#define SERIAL_BUFFER_SIZE 64

// Servo objects
Servo servo1;  // Door
Servo servo2;  // Pan
Servo servo3;  // Tilt
Servo servo4;  // Window

// Serial input buffer
char serialBuffer[SERIAL_BUFFER_SIZE];
int bufferIndex = 0;

// Active movement tracking (for non-blocking timed movements)
struct ServoMovement {
  Servo* servo;
  unsigned long endTime;
  bool active;
};

ServoMovement movements[4] = {
  {&servo1, 0, false},
  {&servo2, 0, false},
  {&servo3, 0, false},
  {&servo4, 0, false}
};

void setup() {
  Serial.begin(9600);
  
  // Attach servos
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo3.attach(SERVO3_PIN);
  servo4.attach(SERVO4_PIN);
  
  // Initialize servos to stopped position
  servo1.write(SERVO_STOP);
  servo2.write(SERVO_STOP);
  servo3.write(SERVO_STOP);
  servo4.write(SERVO_STOP);
  
  // Setup shooter motor pins
  pinMode(SHOOTER_PIN1, OUTPUT);
  pinMode(SHOOTER_PIN2, OUTPUT);
  digitalWrite(SHOOTER_PIN1, LOW);
  digitalWrite(SHOOTER_PIN2, LOW);
  
  Serial.println("SENTINEL_ARDUINO_READY");
}

void loop() {
  // Check for serial commands
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        serialBuffer[bufferIndex] = '\0';
        processCommand(serialBuffer);
        bufferIndex = 0;
      }
    } else if (bufferIndex < SERIAL_BUFFER_SIZE - 1) {
      serialBuffer[bufferIndex++] = c;
    }
  }
  
  // Check for completed movements (non-blocking)
  checkMovements();
}

void processCommand(char* cmd) {
  Serial.print("CMD: ");
  Serial.println(cmd);
  
  // Handle special commands
  if (strcmp(cmd, "LOCKDOWN") == 0) {
    handleLockdown();
    return;
  }
  
  if (strcmp(cmd, "UNLOCK") == 0) {
    handleUnlock();
    return;
  }
  
  if (strcmp(cmd, "FIRE") == 0) {
    handleFire();
    return;
  }
  
  if (strcmp(cmd, "STOP_ALL") == 0) {
    handleStopAll();
    return;
  }
  
  // Parse servo command: "S#,+/-duration" or "S#,speed"
  if (cmd[0] == 'S' && cmd[1] >= '1' && cmd[1] <= '4') {
    int servoNum = cmd[1] - '0';  // 1-4
    char* valueStr = strchr(cmd, ',');
    
    if (valueStr != NULL) {
      valueStr++;  // Skip the comma
      
      // Check if it's a timed movement (+/-duration) or direct speed
      if (valueStr[0] == '+' || valueStr[0] == '-') {
        // Timed movement
        int direction = (valueStr[0] == '+') ? 1 : -1;
        int duration = atoi(valueStr + 1);
        
        moveServoTimed(servoNum, direction, duration);
      } else {
        // Direct speed (0-180)
        int speed = atoi(valueStr);
        setServoSpeed(servoNum, speed);
      }
    }
    return;
  }
  
  Serial.println("ERR: Unknown command");
}

void moveServoTimed(int servoNum, int direction, int durationMs) {
  Servo* servo = getServo(servoNum);
  if (servo == NULL) return;
  
  // Set direction
  int speed = (direction > 0) ? SERVO_CW_FULL : SERVO_CCW_FULL;
  servo->write(speed);
  
  // Schedule stop
  int idx = servoNum - 1;
  movements[idx].servo = servo;
  movements[idx].endTime = millis() + durationMs;
  movements[idx].active = true;
  
  Serial.print("MOVING S");
  Serial.print(servoNum);
  Serial.print(" ");
  Serial.print((direction > 0) ? "CW" : "CCW");
  Serial.print(" for ");
  Serial.print(durationMs);
  Serial.println("ms");
}

void setServoSpeed(int servoNum, int speed) {
  Servo* servo = getServo(servoNum);
  if (servo == NULL) return;
  
  // Clamp speed to valid range
  speed = constrain(speed, 0, 180);
  servo->write(speed);
  
  Serial.print("S");
  Serial.print(servoNum);
  Serial.print(" SPEED: ");
  Serial.println(speed);
}

Servo* getServo(int num) {
  switch(num) {
    case 1: return &servo1;
    case 2: return &servo2;
    case 3: return &servo3;
    case 4: return &servo4;
    default: return NULL;
  }
}

void checkMovements() {
  unsigned long now = millis();
  
  for (int i = 0; i < 4; i++) {
    if (movements[i].active && now >= movements[i].endTime) {
      movements[i].servo->write(SERVO_STOP);
      movements[i].active = false;
      
      Serial.print("S");
      Serial.print(i + 1);
      Serial.println(" STOPPED");
    }
  }
}

void handleLockdown() {
  Serial.println("LOCKDOWN: Locking door and window");
  
  // Lock door (S1) - CW for LOCK_DURATION
  moveServoTimed(1, 1, LOCK_DURATION_MS);
  
  // Lock window (S4) - CW for LOCK_DURATION
  moveServoTimed(4, 1, LOCK_DURATION_MS);
}

void handleUnlock() {
  Serial.println("UNLOCK: Unlocking door");
  
  // Unlock door (S1) - CCW for LOCK_DURATION
  moveServoTimed(1, -1, LOCK_DURATION_MS);
}

void handleFire() {
  Serial.println("FIRE: Activating shooter");
  
  // Activate shooter motors
  digitalWrite(SHOOTER_PIN1, HIGH);
  digitalWrite(SHOOTER_PIN2, HIGH);
  
  // Hold for fire duration (blocking - intentional for safety)
  delay(FIRE_DURATION_MS);
  
  // Deactivate
  digitalWrite(SHOOTER_PIN1, LOW);
  digitalWrite(SHOOTER_PIN2, LOW);
  
  Serial.println("FIRE: Complete");
}

void handleStopAll() {
  Serial.println("STOP_ALL: Emergency stop");
  
  // Stop all servos
  servo1.write(SERVO_STOP);
  servo2.write(SERVO_STOP);
  servo3.write(SERVO_STOP);
  servo4.write(SERVO_STOP);
  
  // Cancel all pending movements
  for (int i = 0; i < 4; i++) {
    movements[i].active = false;
  }
  
  // Stop shooter motors
  digitalWrite(SHOOTER_PIN1, LOW);
  digitalWrite(SHOOTER_PIN2, LOW);
  
  Serial.println("ALL STOPPED");
}
