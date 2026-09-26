/*
 * AEGIS XY Jog Test
 *
 * Temporary bring-up firmware for verifying only the X/Y stepper drivers.
 * - No homing required
 * - Z is untouched
 * - Plasma PWM is forced off
 *
 * Arduino IDE setup:
 *   Board: Arduino Mega or Mega 2560
 *   Port: your /dev/cu.usbmodem... port
 *   Serial Monitor: 115200 baud, Newline or Both NL & CR
 *
 * Commands:
 *   XP or X+   tiny X positive nudge
 *   XM or X-   tiny X negative nudge
 *   YP or Y+   tiny Y positive nudge
 *   YM or Y-   tiny Y negative nudge
 *   S or STOP  stop both motors
 *   STATUS     print current step counts
 *   HELP       print commands
 */

#include <AccelStepper.h>

// Current AEGIS pin map from firmware/lib/aegis_pins.h
constexpr uint8_t X_STEP_PIN = 27;
constexpr uint8_t X_DIR_PIN = 25;
constexpr uint8_t Y_STEP_PIN = 24;
constexpr uint8_t Y_DIR_PIN = 22;
constexpr uint8_t PLASMA_PWM_PIN = 6;

constexpr long NUDGE_STEPS = 80;
constexpr long JOG_SPEED = 250;
constexpr long JOG_ACCEL = 200;

AccelStepper xMotor(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper yMotor(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
String line;

void printHelp() {
  Serial.println(F("AEGIS XY JOG TEST - plasma disabled, Z untouched, no homing required"));
  Serial.println(F("Commands: XP XM YP YM = tiny nudge, S = stop, STATUS = positions, HELP = commands"));
}

void printStatus() {
  Serial.print(F("XYJOG X="));
  Serial.print(xMotor.currentPosition());
  Serial.print(F(" Y="));
  Serial.println(yMotor.currentPosition());
}

void stopAll() {
  xMotor.stop();
  yMotor.stop();
  xMotor.moveTo(xMotor.currentPosition());
  yMotor.moveTo(yMotor.currentPosition());
  Serial.println(F("OK STOP"));
}

void nudge(AccelStepper &axis, long steps, const __FlashStringHelper *name) {
  axis.move(steps);
  Serial.print(F("OK NUDGE "));
  Serial.print(name);
  Serial.print(F(" "));
  Serial.println(steps);
}

void process(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  if (cmd == "XP" || cmd == "X+") nudge(xMotor, NUDGE_STEPS, F("X+"));
  else if (cmd == "XM" || cmd == "X-") nudge(xMotor, -NUDGE_STEPS, F("X-"));
  else if (cmd == "YP" || cmd == "Y+") nudge(yMotor, NUDGE_STEPS, F("Y+"));
  else if (cmd == "YM" || cmd == "Y-") nudge(yMotor, -NUDGE_STEPS, F("Y-"));
  else if (cmd == "S" || cmd == "STOP") stopAll();
  else if (cmd == "STATUS") printStatus();
  else if (cmd == "HELP" || cmd == "?") printHelp();
  else Serial.println(F("ERR unknown. Send HELP"));
}

void setup() {
  Serial.begin(115200);
  pinMode(PLASMA_PWM_PIN, OUTPUT);
  analogWrite(PLASMA_PWM_PIN, 0);
  xMotor.setMaxSpeed(JOG_SPEED);
  yMotor.setMaxSpeed(JOG_SPEED);
  xMotor.setAcceleration(JOG_ACCEL);
  yMotor.setAcceleration(JOG_ACCEL);
  printHelp();
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
  xMotor.run();
  yMotor.run();
}
