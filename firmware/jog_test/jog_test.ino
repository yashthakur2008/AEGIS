/*
 * AEGIS — Autonomous Epidermal and Germicidal Imaging System
 * 3-Axis Gantry: Stepper Jog Test
 *
 * Bring-up / bench-test sketch. Jogs all three axes together via serial
 * commands so motor wiring, driver direction, and limit switches can be
 * verified before running the full controller firmware.
 *
 * Serial commands @ 115200 baud:
 *   f / F  -> jog all axes forward   (send s to stop)
 *   b / B  -> jog all axes backward  (send s to stop)
 *   s / S  -> stop
 */

#include <AccelStepper.h>
#include "aegis_pins.h"

const int jogSpeed = 800;
const int jogAccel = 400;

AccelStepper step1(AccelStepper::DRIVER, AEGIS_X_STEP_PIN, AEGIS_X_DIR_PIN);  // X
AccelStepper step2(AccelStepper::DRIVER, AEGIS_Y_STEP_PIN, AEGIS_Y_DIR_PIN);  // Y
AccelStepper step3(AccelStepper::DRIVER, AEGIS_Z_STEP_PIN, AEGIS_Z_DIR_PIN);  // Z

// 0 = stopped, 1 = forward, -1 = backward
int direction = 0;

bool limitHit(uint8_t pin) {
  return digitalRead(pin) == HIGH;
}

bool limitsClearForDirection(int dir) {
  if (dir >= 0) {
    return true;
  }
  return !limitHit(AEGIS_X_LIMIT_PIN) &&
         !limitHit(AEGIS_Y_LIMIT_PIN) &&
         !limitHit(AEGIS_Z_LIMIT_PIN);
}

void setupAxis(AccelStepper &axis) {
  axis.setMaxSpeed(jogSpeed);
  axis.setAcceleration(jogAccel);
}

void setup() {
  Serial.begin(115200);

  pinMode(AEGIS_X_LIMIT_PIN, INPUT);
  pinMode(AEGIS_Y_LIMIT_PIN, INPUT);
  pinMode(AEGIS_Z_LIMIT_PIN, INPUT);

  setupAxis(step1);
  setupAxis(step2);
  setupAxis(step3);

  Serial.println("Ready.");
  Serial.println("f = forward  b = backward  s = stop");
}

void setDirection(int dir) {
  if (!limitsClearForDirection(dir)) {
    Serial.println("Limit switch active. Refusing negative jog.");
    dir = 0;
  }

  direction = dir;
  if (dir == 1) {
    step1.move( 999999999L);
    step2.move( 999999999L);
    step3.move( 999999999L);
  } else if (dir == -1) {
    step1.move(-999999999L);
    step2.move(-999999999L);
    step3.move(-999999999L);
  } else {
    step1.stop();
    step2.stop();
    step3.stop();
  }
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'f' || c == 'F') {
      Serial.println("Moving forward — send s to stop.");
      setDirection(1);
    } else if (c == 'b' || c == 'B') {
      Serial.println("Moving backward — send s to stop.");
      setDirection(-1);
    } else if (c == 's' || c == 'S') {
      Serial.println("Stopped.");
      setDirection(0);
    }
  }

  if (direction < 0 && !limitsClearForDirection(direction)) {
    Serial.println("Limit reached. Stopping.");
    setDirection(0);
  }

  step1.run();
  step2.run();
  step3.run();
}
