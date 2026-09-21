#include <Arduino.h>
#include <AccelStepper.h>
#include "aegis_pins.h"

struct AxisCalibration {
  float stepsPerMm;
  long minSteps;
  long maxSteps;
};

struct MachinePointMm {
  float x;
  float y;
  float z;
};

struct MachinePointSteps {
  long x;
  long y;
  long z;
};

constexpr AxisCalibration X_AXIS{80.0f, 0, 32000};
constexpr AxisCalibration Y_AXIS{80.0f, 0, 32000};
constexpr AxisCalibration Z_AXIS{400.0f, 0, 16000};
constexpr long HOMING_BACKOFF_STEPS = 400;
constexpr long DEFAULT_SPEED = 900;
constexpr long DEFAULT_ACCEL = 500;
constexpr const char *CMD_HOME = "HOME";
constexpr const char *CMD_MOVE = "MOVE";
constexpr const char *CMD_STOP = "STOP";
constexpr const char *CMD_STATUS = "STATUS";
constexpr const char *CMD_PLASMA = "PLASMA";

AccelStepper xMotor(AccelStepper::DRIVER, AEGIS_X_STEP_PIN, AEGIS_X_DIR_PIN);
AccelStepper yMotor(AccelStepper::DRIVER, AEGIS_Y_STEP_PIN, AEGIS_Y_DIR_PIN);
AccelStepper zMotor(AccelStepper::DRIVER, AEGIS_Z_STEP_PIN, AEGIS_Z_DIR_PIN);

String inputLine;
unsigned long plasmaOffAtMs = 0;

long clampSteps(long value, const AxisCalibration &axis) {
  if (value < axis.minSteps) return axis.minSteps;
  if (value > axis.maxSteps) return axis.maxSteps;
  return value;
}

long mmToSteps(float mm, const AxisCalibration &axis) {
  return clampSteps(lround(mm * axis.stepsPerMm), axis);
}

MachinePointSteps machineToSteps(const MachinePointMm &point) {
  return {
    mmToSteps(point.x, X_AXIS),
    mmToSteps(point.y, Y_AXIS),
    mmToSteps(point.z, Z_AXIS),
  };
}

void configureAxis(AccelStepper &axis) {
  axis.setMaxSpeed(DEFAULT_SPEED);
  axis.setAcceleration(DEFAULT_ACCEL);
}

bool limitHit(uint8_t pin) {
  return digitalRead(pin) == HIGH;
}

void stopAll() {
  xMotor.stop();
  yMotor.stop();
  zMotor.stop();
}

void setPlasmaIntensity(float intensity, unsigned long dwellMs) {
  float clamped = intensity;
  if (clamped < 0.0f) clamped = 0.0f;
  if (clamped > 1.0f) clamped = 1.0f;
  analogWrite(AEGIS_PLASMA_PWM_PIN, static_cast<int>(lround(clamped * 255.0f)));
  plasmaOffAtMs = clamped > 0.0f && dwellMs > 0 ? millis() + dwellMs : 0;
}

void disablePlasma() {
  analogWrite(AEGIS_PLASMA_PWM_PIN, 0);
  plasmaOffAtMs = 0;
}

void hardStopAll() {
  disablePlasma();
  xMotor.setSpeed(0);
  yMotor.setSpeed(0);
  zMotor.setSpeed(0);
  xMotor.moveTo(xMotor.currentPosition());
  yMotor.moveTo(yMotor.currentPosition());
  zMotor.moveTo(zMotor.currentPosition());
}

void printStatus() {
  Serial.print("STATUS X=");
  Serial.print(xMotor.currentPosition());
  Serial.print(" Y=");
  Serial.print(yMotor.currentPosition());
  Serial.print(" Z=");
  Serial.println(zMotor.currentPosition());
}

void moveToMachineMm(const MachinePointMm &point) {
  MachinePointSteps target = machineToSteps(point);
  xMotor.moveTo(target.x);
  yMotor.moveTo(target.y);
  zMotor.moveTo(target.z);
  Serial.print("OK MOVE ");
  Serial.print(target.x);
  Serial.print(' ');
  Serial.print(target.y);
  Serial.print(' ');
  Serial.println(target.z);
}

void homeAxis(AccelStepper &axis, uint8_t limitPin, const AxisCalibration &calibration) {
  axis.setMaxSpeed(DEFAULT_SPEED / 2);
  axis.moveTo(calibration.minSteps - 100000L);
  while (!limitHit(limitPin)) {
    axis.run();
  }
  axis.setCurrentPosition(calibration.minSteps);
  axis.moveTo(calibration.minSteps + HOMING_BACKOFF_STEPS);
  while (axis.distanceToGo() != 0) {
    axis.run();
  }
  axis.setCurrentPosition(0);
  axis.setMaxSpeed(DEFAULT_SPEED);
}

void homeAll() {
  Serial.println("OK HOME START");
  homeAxis(zMotor, AEGIS_Z_LIMIT_PIN, Z_AXIS);
  homeAxis(xMotor, AEGIS_X_LIMIT_PIN, X_AXIS);
  homeAxis(yMotor, AEGIS_Y_LIMIT_PIN, Y_AXIS);
  Serial.println("OK HOME DONE");
}

void handleCommand(String line) {
  line.trim();
  line.toUpperCase();

  if (line == "STOP") {
    hardStopAll();
    Serial.println("OK STOP");
    return;
  }

  if (line == "STATUS") {
    printStatus();
    return;
  }

  if (line == "HOME") {
    homeAll();
    return;
  }

  if (line.startsWith("MOVE ")) {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    int parsed = sscanf(line.c_str(), "MOVE %f %f %f", &x, &y, &z);
    if (parsed != 3) {
      Serial.println("ERR MOVE expects: MOVE <x_mm> <y_mm> <z_mm>");
      return;
    }
    moveToMachineMm({x, y, z});
    return;
  }


  if (line.startsWith("PLASMA ")) {
    float intensity = 0.0f;
    unsigned long dwellMs = 0;
    int parsed = sscanf(line.c_str(), "PLASMA %f %lu", &intensity, &dwellMs);
    if (parsed != 2) {
      Serial.println("ERR PLASMA expects: PLASMA <intensity_0_to_1> <dwell_ms>");
      return;
    }
    setPlasmaIntensity(intensity, dwellMs);
    Serial.print("OK PLASMA ");
    Serial.print(intensity);
    Serial.print(' ');
    Serial.println(dwellMs);
    return;
  }

  Serial.println("ERR unknown command. Use HOME, MOVE x y z, PLASMA intensity dwell_ms, STOP, STATUS.");
}

void setup() {
  Serial.begin(115200);
  pinMode(AEGIS_X_LIMIT_PIN, INPUT);
  pinMode(AEGIS_Y_LIMIT_PIN, INPUT);
  pinMode(AEGIS_Z_LIMIT_PIN, INPUT);
  pinMode(AEGIS_PLASMA_PWM_PIN, OUTPUT);
  disablePlasma();
  configureAxis(xMotor);
  configureAxis(yMotor);
  configureAxis(zMotor);
  Serial.println("AEGIS controller ready. Commands: HOME, MOVE x_mm y_mm z_mm, PLASMA intensity dwell_ms, STOP, STATUS");
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (inputLine.length() > 0) {
        handleCommand(inputLine);
        inputLine = "";
      }
    } else {
      inputLine += c;
    }
  }

  if (limitHit(AEGIS_X_LIMIT_PIN) && xMotor.speed() < 0) hardStopAll();
  if (limitHit(AEGIS_Y_LIMIT_PIN) && yMotor.speed() < 0) hardStopAll();
  if (limitHit(AEGIS_Z_LIMIT_PIN) && zMotor.speed() < 0) hardStopAll();

  if (plasmaOffAtMs > 0 && millis() >= plasmaOffAtMs) disablePlasma();

  xMotor.run();
  yMotor.run();
  zMotor.run();
}
