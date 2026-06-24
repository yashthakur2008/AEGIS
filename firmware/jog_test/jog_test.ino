/*
 * AEGIS — Autonomous Epidermal and Germicidal Imaging System
 * 3-Axis Gantry: Stepper Jog Test
 *
 * Bring-up / bench-test sketch. Jogs all three axes together via serial
 * commands so the motor wiring and driver direction can be verified before
 * running the full MechanismCameraControl firmware (vision + homing + toolpath).
 *
 * Serial commands @ 115200 baud:
 *   f / F  -> jog all axes forward   (send s to stop)
 *   b / B  -> jog all axes backward  (send s to stop)
 *   s / S  -> stop
 *
 * Hardware: Arduino Mega 2560 + DM556 microstepper drivers, NEMA 23 (X/Y) +
 * Z-axis stepper. Pin map below is the CURRENT machine wiring (see
 * docs/hardware/pinout.md). NOTE: this supersedes the pin assignments listed
 * in Appendix E of the ME 195B final report, which are from an earlier revision.
 */

#include <AccelStepper.h>

// DM556 stepper driver pins (Pul+/Dir+) — current machine wiring.
// step1 = X-axis, step2 = Y-axis, step3 = Z-axis.
int Stepper1Pulse     = 27;   // X-axis Pul+ (purple)
int Stepper1Direction = 25;   // X-axis Dir+ (yellow)

int Stepper2Pulse     = 24;   // Y-axis Pul+ (green)
int Stepper2Direction = 22;   // Y-axis Dir+ (blue)

int Stepper3Pulse     = 23;   // Z-axis Pul+ (orange)
int Stepper3Direction = 26;   // Z-axis Dir+ (white)

const int jogSpeed = 800;
const int jogAccel = 400;

AccelStepper step1(1, Stepper1Pulse, Stepper1Direction);  // X
AccelStepper step2(1, Stepper2Pulse, Stepper2Direction);  // Y
AccelStepper step3(1, Stepper3Pulse, Stepper3Direction);  // Z

// 0 = stopped, 1 = forward, -1 = backward
int direction = 0;

void setup() {
  Serial.begin(115200);

  pinMode(Stepper1Pulse,     OUTPUT);
  pinMode(Stepper1Direction, OUTPUT);
  pinMode(Stepper2Pulse,     OUTPUT);
  pinMode(Stepper2Direction, OUTPUT);
  pinMode(Stepper3Pulse,     OUTPUT);
  pinMode(Stepper3Direction, OUTPUT);

  step1.setMaxSpeed(jogSpeed);  step1.setAcceleration(jogAccel);
  step2.setMaxSpeed(jogSpeed);  step2.setAcceleration(jogAccel);
  step3.setMaxSpeed(jogSpeed);  step3.setAcceleration(jogAccel);

  Serial.println("Ready.");
  Serial.println("f = forward  b = backward  s = stop");
}

void setDirection(int dir) {
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
  // Check for incoming character
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

  step1.run();
  step2.run();
  step3.run();
}
