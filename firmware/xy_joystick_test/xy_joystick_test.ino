/*
 * AEGIS XY Joystick Jog Test
 *
 * Temporary bring-up firmware for manual X/Y movement with the analog joystick.
 * - No homing required
 * - Z is untouched
 * - Plasma is untouched/disabled on this test pin
 * - Serial prints joystick raw values and position counts for debugging
 *
 * Current breadboard driver wiring:
 *   X STEP/PUL- -> Arduino D7
 *   X DIR/DIR-  -> Arduino D6
 *   Y STEP/PUL- -> Arduino D5
 *   Y DIR/DIR-  -> Arduino D4
 *   PUL+/DIR+   -> Arduino 5V rail
 *   ENA empty
 *
 * Joystick wiring assumption from original gantry sketch:
 *   joystick X axis -> A11
 *   joystick Y axis -> A12
 *   joystick switch -> D13, optional
 *
 * Serial Monitor: 115200 baud
 * Commands:
 *   STATUS       print raw joystick and position
 *   CAL          capture current joystick center
 *   ARM          enable joystick motion after calibration
 *   ZERO         reset software step counters to 0
 *   STOP         disarm and stop motion
 */

#include <AccelStepper.h>

constexpr uint8_t X_STEP_PIN = 7;
constexpr uint8_t X_DIR_PIN = 6;
constexpr uint8_t Y_STEP_PIN = 5;
constexpr uint8_t Y_DIR_PIN = 4;
constexpr uint8_t JOY_X_PIN = A11;
constexpr uint8_t JOY_Y_PIN = A12;
constexpr uint8_t JOY_SW_PIN = 13;
constexpr uint8_t UNUSED_PLASMA_SAFE_PIN = 44;

constexpr int DEFAULT_CENTER = 512;
constexpr int JOY_DEADZONE = 150;
constexpr float MAX_SPEED_STEPS_PER_S = 450.0f;
constexpr float ACCEL_STEPS_PER_S2 = 350.0f;
constexpr unsigned long STATUS_PERIOD_MS = 250;

AccelStepper xMotor(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper yMotor(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
String line;
unsigned long lastStatusMs = 0;
bool armed = false;
int xCenter = DEFAULT_CENTER;
int yCenter = DEFAULT_CENTER;

float joystickToSpeed(int raw, int center) {
  int delta = raw - center;
  if (abs(delta) <= JOY_DEADZONE) return 0.0f;
  float scaled = (abs(delta) - JOY_DEADZONE) / float(511 - JOY_DEADZONE);
  scaled = constrain(scaled, 0.0f, 1.0f);
  return (delta > 0 ? 1.0f : -1.0f) * scaled * MAX_SPEED_STEPS_PER_S;
}

bool joystickCentered(int xRaw, int yRaw) {
  return abs(xRaw - xCenter) <= JOY_DEADZONE && abs(yRaw - yCenter) <= JOY_DEADZONE;
}

void printStatus(int xRaw = analogRead(JOY_X_PIN), int yRaw = analogRead(JOY_Y_PIN)) {
  Serial.print(F("JOY XRAW=")); Serial.print(xRaw);
  Serial.print(F(" YRAW=")); Serial.print(yRaw);
  Serial.print(F(" XCENTER=")); Serial.print(xCenter);
  Serial.print(F(" YCENTER=")); Serial.print(yCenter);
  Serial.print(F(" XPOS=")); Serial.print(xMotor.currentPosition());
  Serial.print(F(" YPOS=")); Serial.print(yMotor.currentPosition());
  Serial.print(F(" ARMED=")); Serial.println(armed ? F("YES") : F("NO"));
}

void stopMotion() {
  xMotor.setSpeed(0);
  yMotor.setSpeed(0);
  xMotor.moveTo(xMotor.currentPosition());
  yMotor.moveTo(yMotor.currentPosition());
}

void calibrateCenter() {
  long xSum = 0;
  long ySum = 0;
  constexpr int samples = 25;
  for (int i = 0; i < samples; ++i) {
    xSum += analogRead(JOY_X_PIN);
    ySum += analogRead(JOY_Y_PIN);
    delay(5);
  }
  xCenter = xSum / samples;
  yCenter = ySum / samples;
  Serial.print(F("OK CAL XCENTER=")); Serial.print(xCenter);
  Serial.print(F(" YCENTER=")); Serial.println(yCenter);
}

void process(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  if (cmd == "STATUS") printStatus();
  else if (cmd == "CAL") calibrateCenter();
  else if (cmd == "ARM") {
    int xRaw = analogRead(JOY_X_PIN);
    int yRaw = analogRead(JOY_Y_PIN);
    if (!joystickCentered(xRaw, yRaw)) {
      Serial.println(F("ERR center joystick before ARM"));
    } else {
      armed = true;
      Serial.println(F("OK ARM"));
    }
  }
  else if (cmd == "ZERO") {
    xMotor.setCurrentPosition(0);
    yMotor.setCurrentPosition(0);
    Serial.println(F("OK ZERO"));
  } else if (cmd == "STOP" || cmd == "S") {
    armed = false;
    stopMotion();
    Serial.println(F("OK STOP. Send CAL then ARM to re-enable joystick motion."));
  } else {
    Serial.println(F("Commands: STATUS, CAL, ARM, ZERO, STOP"));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(JOY_X_PIN, INPUT);
  pinMode(JOY_Y_PIN, INPUT);
  pinMode(JOY_SW_PIN, INPUT_PULLUP);
  pinMode(UNUSED_PLASMA_SAFE_PIN, OUTPUT);
  analogWrite(UNUSED_PLASMA_SAFE_PIN, 0);

  xMotor.setMaxSpeed(MAX_SPEED_STEPS_PER_S);
  yMotor.setMaxSpeed(MAX_SPEED_STEPS_PER_S);
  xMotor.setAcceleration(ACCEL_STEPS_PER_S2);
  yMotor.setAcceleration(ACCEL_STEPS_PER_S2);

  Serial.println(F("AEGIS XY JOYSTICK JOG TEST - no homing, X/Y only, Z untouched"));
  Serial.println(F("SAFE MODE: joystick is disarmed on boot. Send CAL, then ARM, then move gently."));
  delay(500);
  calibrateCenter();
  printStatus();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line.length()) process(line);
      line = "";
    } else if (line.length() < 32) {
      line += c;
    }
  }

  int xRaw = analogRead(JOY_X_PIN);
  int yRaw = analogRead(JOY_Y_PIN);
  bool buttonPressed = digitalRead(JOY_SW_PIN) == LOW;
  if (buttonPressed) {
    armed = false;
    stopMotion();
  }

  if (!armed) {
    stopMotion();
  } else {
    xMotor.setSpeed(joystickToSpeed(xRaw, xCenter));
    yMotor.setSpeed(joystickToSpeed(yRaw, yCenter));
    xMotor.runSpeed();
    yMotor.runSpeed();
  }

  if (millis() - lastStatusMs >= STATUS_PERIOD_MS) {
    lastStatusMs = millis();
    printStatus(xRaw, yRaw);
  }
}
