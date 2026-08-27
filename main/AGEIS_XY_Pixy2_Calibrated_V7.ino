/*
  Wound gantry V7 - PIXY2/ARDUINO XY CALIBRATED MOTION-ONLY DRY RUN

  Hardware values updated from the supplied wiring document:
    Arduino Mega 2560
    X STEP/DIR: 7/6, Y STEP/DIR: 5/4
    X/Y limit switches: 27/23
    Joystick: A11/A12, joystick push switch: 13
    TB6600 common-positive inputs: PUL+/DIR+ to 5V; Arduino pins to PUL-/DIR-
    Measured lead screw travel: 8 mm/rev
    Recommended driver setting: 1600 pulses/rev, giving 200 steps/mm
    Pixy2 CCC wound signature: 2
    Camera scale: X 0.5957 mm/pixel, Y 0.625 mm/pixel

  User-specified changes:
    Normally-open home switches (pressed = LOW)
    X travel: 12 inches = 304.8 mm
    Y travel: 8 inches = 203.2 mm
    Joystick movement; click while the tip is over the detected wound center to
    register the camera coordinates to machine coordinates.

  ONE-TIME CALIBRATION WORKFLOW:
    Attach a signature-1 colored marker at the tool center (or enter its
    measured X/Y offset below). Send H, then CAL. Jog to four widely separated
    positions and press the joystick once at each position. The Arduino fits a
    pixel-to-mm affine transform and stores it in EEPROM.

  NORMAL WORKFLOW:
    Send H after power-up to home against the X/Y limit switches.
    Send C to home and perform a motion-only test of the four workspace corners.
    Pixy2 detects signature 2. Press the joystick once
    to perform a dry-run raster inside the stable detected rectangle. Saved
    calibration is reused; it is not repeated for each image.

  Pixy2 CCC does not provide an irregular outline. This easy version covers
  the detected rectangle, reduced by EDGE_MARGIN_MM on every side.

  No plasma output exists in this sketch.
*/

#include <AccelStepper.h>
#include <Pixy2.h>
#include <EEPROM.h>

constexpr uint8_t X_STEP_PIN = 7, X_DIR_PIN = 6;
constexpr uint8_t Y_STEP_PIN = 5, Y_DIR_PIN = 4;
constexpr uint8_t X_HOME_PIN = 27, Y_HOME_PIN = 23;
// Joystick axes must use analog inputs. The document's "11" and "12" are
// interpreted as A11 and A12, not digital pins D11 and D12.
constexpr uint8_t JOY_X_PIN = A11, JOY_Y_PIN = A12, JOY_SW_PIN = 13;

// These named constants are editable from Wound Gantry Studio's Machine Setup tab.
// steps/mm = driver pulses/revolution / lead-screw travel per revolution
constexpr float DRIVER_PULSES_PER_REV_X = 1600.0f;
constexpr float DRIVER_PULSES_PER_REV_Y = 1600.0f;
constexpr float LEAD_MM_PER_REV_X = 8.0f;
constexpr float LEAD_MM_PER_REV_Y = 8.0f;
constexpr float STEPS_PER_MM_X = DRIVER_PULSES_PER_REV_X / LEAD_MM_PER_REV_X;
constexpr float STEPS_PER_MM_Y = DRIVER_PULSES_PER_REV_Y / LEAD_MM_PER_REV_Y;
// Replace these nominal values with measured safe travel before full-range use.
constexpr float X_MIN_MM = 0.0f;
constexpr float X_MAX_MM = 304.8f;
constexpr float Y_MIN_MM = 0.0f;
constexpr float Y_MAX_MM = 203.2f;
constexpr int8_t HOME_DIR_X = -1, HOME_DIR_Y = -1;

constexpr float HOME_SPEED_MM_S = 5.0f;
constexpr float HOME_BACKOFF_MM = 3.0f;
constexpr float JOG_MAX_MM_S = 15.0f;
constexpr float TRACE_MM_S = 8.0f;
constexpr float CORNER_TEST_MM_S = 15.0f;
constexpr float ACCEL_MM_S2 = 25.0f;
// Stay away from the un-switched far ends during the corner test.
constexpr float CORNER_MARGIN_MM = 5.0f;
constexpr int JOY_CENTER = 512;
constexpr int JOY_DEADZONE = 100;

constexpr uint8_t WOUND_SIGNATURE = 2;
constexpr uint8_t CAL_MARKER_SIGNATURE = 1;
// Physical marker-center position relative to the tool center. Use zero only
// when the colored calibration marker is centered exactly on the tool axis.
constexpr float MARKER_OFFSET_X_MM = 0.0f;
constexpr float MARKER_OFFSET_Y_MM = 0.0f;
constexpr uint8_t STABLE_FRAMES_REQUIRED = 8;
constexpr float EDGE_MARGIN_MM = 2.0f;
constexpr float LINE_SPACING_MM = 3.0f;

AccelStepper xMotor(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper yMotor(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
Pixy2 pixy;

struct BlockData {
  int16_t x, y, w, h;
  bool valid;
};
BlockData lastBlock = {0, 0, 0, 0, false};
BlockData stableBlock = {0, 0, 0, 0, false};
BlockData markerBlock = {0, 0, 0, 0, false};
uint8_t stableFrames = 0;

bool homed = false;
bool faulted = false;
bool calibrationValid = false;
bool calibrationMode = false;
bool oldJoyClick = false;
String commandLine;

struct CalibrationData {
  uint32_t magic;
  float a, b, c; // machine X = a*pixelX + b*pixelY + c
  float d, e, f; // machine Y = d*pixelX + e*pixelY + f
};
constexpr uint32_t CAL_MAGIC = 0xCA1B2026UL;
CalibrationData cal = {0, 0, 0, 0, 0, 0, 0};

struct CalibrationSample { float u, v, x, y; };
CalibrationSample samples[4];
uint8_t sampleCount = 0;

long xSteps(float mm) { return lroundf(mm * STEPS_PER_MM_X); }
long ySteps(float mm) { return lroundf(mm * STEPS_PER_MM_Y); }
float xMM() { return xMotor.currentPosition() / STEPS_PER_MM_X; }
float yMM() { return yMotor.currentPosition() / STEPS_PER_MM_Y; }
float cameraToMachineX(float px, float py) { return cal.a*px + cal.b*py + cal.c; }
float cameraToMachineY(float px, float py) { return cal.d*px + cal.e*py + cal.f; }

bool homePressed(uint8_t pin) { return digitalRead(pin) == LOW; } // NO switch

void fault(const __FlashStringHelper *why) {
  xMotor.stop(); yMotor.stop();
  xMotor.disableOutputs(); yMotor.disableOutputs();
  faulted = true; homed = false;
  Serial.println(why);
}

bool safetyOK() {
  return !faulted;
}

bool homeAxis(AccelStepper &motor, uint8_t pin, int8_t direction,
              float stepsPerMM, const __FlashStringHelper *name) {
  Serial.print(F("Homing ")); Serial.println(name);
  motor.enableOutputs();
  motor.setMaxSpeed(HOME_SPEED_MM_S * stepsPerMM);
  motor.setSpeed(direction * HOME_SPEED_MM_S * stepsPerMM);
  unsigned long started = millis();

  // NO switch reads HIGH normally and LOW when pressed.
  while (!homePressed(pin)) {
    if (millis() - started > 30000UL) return false;
    motor.runSpeed();
  }

  motor.setCurrentPosition(0);
  motor.moveTo(lroundf(-direction * HOME_BACKOFF_MM * stepsPerMM));
  while (motor.distanceToGo()) {
    motor.run();
  }
  if (homePressed(pin)) return false; // Must release after backing off.
  motor.setCurrentPosition(0);
  return true;
}

void homeMachine() {
  faulted = false;
  xMotor.enableOutputs(); yMotor.enableOutputs();

  if (!homeAxis(xMotor, X_HOME_PIN, HOME_DIR_X, STEPS_PER_MM_X, F("X")) ||
      !homeAxis(yMotor, Y_HOME_PIN, HOME_DIR_Y, STEPS_PER_MM_Y, F("Y"))) {
    fault(F("FAULT: homing failed"));
    return;
  }

  xMotor.setAcceleration(ACCEL_MM_S2 * STEPS_PER_MM_X);
  yMotor.setAcceleration(ACCEL_MM_S2 * STEPS_PER_MM_Y);
  // Common-positive TB6600 wiring makes the PUL- inputs active LOW.
  xMotor.setPinsInverted(false, true, false);
  yMotor.setPinsInverted(false, true, false);
  homed = true;
  Serial.println(F("Homed. Send CAL to calibrate, or press joystick to run a stable detection."));
}

void updatePixyBlock() {
  pixy.ccc.getBlocks();
  BlockData newest = {0, 0, 0, 0, false};
  markerBlock.valid = false;
  uint32_t largest = 0;
  uint32_t largestMarker = 0;
  for (uint8_t i = 0; i < pixy.ccc.numBlocks; ++i) {
    const auto &b = pixy.ccc.blocks[i];
    uint32_t area = (uint32_t)b.m_width * b.m_height;
    if (b.m_signature == WOUND_SIGNATURE && area > largest) {
      largest = area;
      newest = {(int16_t)b.m_x, (int16_t)b.m_y,
                (int16_t)b.m_width, (int16_t)b.m_height, true};
    }
    if (b.m_signature == CAL_MARKER_SIGNATURE && area > largestMarker) {
      largestMarker = area;
      markerBlock = {(int16_t)b.m_x, (int16_t)b.m_y,
                     (int16_t)b.m_width, (int16_t)b.m_height, true};
    }
  }

  if (!newest.valid) {
    stableFrames = 0; lastBlock.valid = false; stableBlock.valid = false;
    return;
  }

  bool close = lastBlock.valid && abs(newest.x-lastBlock.x) <= 4 &&
               abs(newest.y-lastBlock.y) <= 4 && abs(newest.w-lastBlock.w) <= 4 &&
               abs(newest.h-lastBlock.h) <= 4;
  stableFrames = close ? min(255, stableFrames + 1) : 1;
  lastBlock = newest;
  if (stableFrames >= STABLE_FRAMES_REQUIRED) stableBlock = newest;
}

bool solve3x3(float matrix[3][3], float rhs[3], float answer[3]) {
  float augmented[3][4];
  for (uint8_t r=0; r<3; ++r) {
    for (uint8_t c=0; c<3; ++c) augmented[r][c] = matrix[r][c];
    augmented[r][3] = rhs[r];
  }

  for (uint8_t pivot=0; pivot<3; ++pivot) {
    uint8_t best = pivot;
    for (uint8_t r=pivot+1; r<3; ++r)
      if (fabs(augmented[r][pivot]) > fabs(augmented[best][pivot])) best = r;
    if (fabs(augmented[best][pivot]) < 0.000001f) return false;
    if (best != pivot) {
      for (uint8_t c=pivot; c<4; ++c) {
        float t=augmented[pivot][c]; augmented[pivot][c]=augmented[best][c];
        augmented[best][c]=t;
      }
    }
    float divisor = augmented[pivot][pivot];
    for (uint8_t c=pivot; c<4; ++c) augmented[pivot][c] /= divisor;
    for (uint8_t r=0; r<3; ++r) {
      if (r == pivot) continue;
      float factor = augmented[r][pivot];
      for (uint8_t c=pivot; c<4; ++c)
        augmented[r][c] -= factor * augmented[pivot][c];
    }
  }
  for (uint8_t i=0; i<3; ++i) answer[i] = augmented[i][3];
  return true;
}

bool calculateCalibration() {
  float normal[3][3] = {{0,0,0},{0,0,0},{0,0,0}};
  float rhsX[3] = {0,0,0}, rhsY[3] = {0,0,0};
  for (uint8_t i=0; i<4; ++i) {
    float row[3] = {samples[i].u, samples[i].v, 1.0f};
    for (uint8_t r=0; r<3; ++r) {
      rhsX[r] += row[r] * samples[i].x;
      rhsY[r] += row[r] * samples[i].y;
      for (uint8_t c=0; c<3; ++c) normal[r][c] += row[r]*row[c];
    }
  }
  float xAnswer[3], yAnswer[3];
  float normalCopy[3][3];
  memcpy(normalCopy, normal, sizeof(normal));
  if (!solve3x3(normalCopy, rhsX, xAnswer)) return false;
  memcpy(normalCopy, normal, sizeof(normal));
  if (!solve3x3(normalCopy, rhsY, yAnswer)) return false;
  cal = {CAL_MAGIC, xAnswer[0], xAnswer[1], xAnswer[2],
                    yAnswer[0], yAnswer[1], yAnswer[2]};

  float worstError = 0;
  for (uint8_t i=0; i<4; ++i) {
    float ex = cameraToMachineX(samples[i].u, samples[i].v)-samples[i].x;
    float ey = cameraToMachineY(samples[i].u, samples[i].v)-samples[i].y;
    worstError = max(worstError, sqrt(ex*ex + ey*ey));
  }
  Serial.print(F("Worst calibration-point error (mm): ")); Serial.println(worstError, 3);
  if (!isfinite(worstError) || worstError > 3.0f) return false;
  EEPROM.put(0, cal);
  calibrationValid = true;
  return true;
}

void captureCalibrationPoint() {
  if (!calibrationMode || !homed || !markerBlock.valid) {
    Serial.println(F("Capture rejected: CAL mode, homing, and stable signature-1 marker required"));
    return;
  }
  if (sampleCount >= 4) return;
  samples[sampleCount] = {(float)markerBlock.x, (float)markerBlock.y,
                          xMM()+MARKER_OFFSET_X_MM, yMM()+MARKER_OFFSET_Y_MM};
  ++sampleCount;
  Serial.print(F("Captured calibration point ")); Serial.print(sampleCount);
  Serial.print(F("/4 at pixel ")); Serial.print(markerBlock.x); Serial.print(',');
  Serial.print(markerBlock.y); Serial.print(F(" and machine mm "));
  Serial.print(xMM(),2); Serial.print(','); Serial.println(yMM(),2);
  if (sampleCount == 4) {
    calibrationMode = false;
    if (calculateCalibration()) Serial.println(F("Calibration saved in EEPROM"));
    else Serial.println(F("Calibration failed: use four widely separated, non-collinear positions"));
  }
}

float joystickSpeed(int raw) {
  int displacement = raw - JOY_CENTER;
  if (abs(displacement) <= JOY_DEADZONE) return 0.0f;
  float magnitude = (abs(displacement) - JOY_DEADZONE) /
                    (float)(511 - JOY_DEADZONE);
  magnitude = constrain(magnitude, 0.0f, 1.0f);
  return (displacement > 0 ? 1.0f : -1.0f) * magnitude * JOG_MAX_MM_S;
}

void jogMachine() {
  if (!homed || faulted) return;
  float vx = joystickSpeed(analogRead(JOY_X_PIN));
  float vy = joystickSpeed(analogRead(JOY_Y_PIN));

  // Prevent movement past soft limits or into a pressed home switch.
  if ((xMM() <= X_MIN_MM && vx < 0) || (xMM() >= X_MAX_MM && vx > 0) ||
      (homePressed(X_HOME_PIN) && vx < 0)) vx = 0;
  if ((yMM() <= Y_MIN_MM && vy < 0) || (yMM() >= Y_MAX_MM && vy > 0) ||
      (homePressed(Y_HOME_PIN) && vy < 0)) vy = 0;

  xMotor.setSpeed(vx * STEPS_PER_MM_X);
  yMotor.setSpeed(vy * STEPS_PER_MM_Y);
  xMotor.runSpeed(); yMotor.runSpeed();
}

bool moveToMMAtSpeed(float x, float y, float speedMMPerSecond) {
  if (!homed || faulted || x < X_MIN_MM || x > X_MAX_MM ||
      y < Y_MIN_MM || y > Y_MAX_MM) {
    Serial.println(F("Move rejected: not homed, faulted, or outside configured workspace"));
    return false;
  }
  xMotor.setMaxSpeed(speedMMPerSecond * STEPS_PER_MM_X);
  yMotor.setMaxSpeed(speedMMPerSecond * STEPS_PER_MM_Y);
  xMotor.moveTo(xSteps(x)); yMotor.moveTo(ySteps(y));
  while (xMotor.distanceToGo() || yMotor.distanceToGo()) {
    if (!safetyOK()) return false;
    if ((homePressed(X_HOME_PIN) && xMotor.speed() < 0) ||
        (homePressed(Y_HOME_PIN) && yMotor.speed() < 0)) {
      fault(F("FAULT: home switch hit during outline"));
      return false;
    }
    xMotor.run(); yMotor.run();
  }
  return true;
}

bool moveToMM(float x, float y) {
  return moveToMMAtSpeed(x, y, TRACE_MM_S);
}

void testFourCorners() {
  Serial.println(F("Four-corner test: homing first. Plasma must remain disabled."));
  homeMachine();
  if (!homed || faulted) return;

  const float left   = X_MIN_MM + CORNER_MARGIN_MM;
  const float right  = X_MAX_MM - CORNER_MARGIN_MM;
  const float bottom = Y_MIN_MM + CORNER_MARGIN_MM;
  const float top    = Y_MAX_MM - CORNER_MARGIN_MM;

  if (right <= left || top <= bottom) {
    Serial.println(F("Corner test rejected: workspace is smaller than its safety margins"));
    return;
  }

  Serial.println(F("Corner 1/4: near home"));
  if (!moveToMMAtSpeed(left, bottom, CORNER_TEST_MM_S)) return;
  Serial.println(F("Corner 2/4: far X, near Y"));
  if (!moveToMMAtSpeed(right, bottom, CORNER_TEST_MM_S)) return;
  Serial.println(F("Corner 3/4: far X, far Y"));
  if (!moveToMMAtSpeed(right, top, CORNER_TEST_MM_S)) return;
  Serial.println(F("Corner 4/4: near X, far Y"));
  if (!moveToMMAtSpeed(left, top, CORNER_TEST_MM_S)) return;
  if (!moveToMMAtSpeed(left, bottom, CORNER_TEST_MM_S)) return;
  if (!moveToMMAtSpeed(X_MIN_MM, Y_MIN_MM, CORNER_TEST_MM_S)) return;
  Serial.println(F("Four-corner dry run complete; returned to machine home"));
}

void runDetectedRectangle() {
  if (!calibrationValid || !stableBlock.valid) {
    Serial.println(F("RUN rejected: no saved calibration or wound detection not stable"));
    return;
  }

  float leftPx = stableBlock.x - stableBlock.w * 0.5f;
  float rightPx = stableBlock.x + stableBlock.w * 0.5f;
  float topPx = stableBlock.y - stableBlock.h * 0.5f;
  float bottomPx = stableBlock.y + stableBlock.h * 0.5f;

  // Transform all four corners because camera rotation couples pixel X and Y.
  float cornerX[4] = {
    cameraToMachineX(leftPx,topPx), cameraToMachineX(rightPx,topPx),
    cameraToMachineX(rightPx,bottomPx), cameraToMachineX(leftPx,bottomPx)};
  float cornerY[4] = {
    cameraToMachineY(leftPx,topPx), cameraToMachineY(rightPx,topPx),
    cameraToMachineY(rightPx,bottomPx), cameraToMachineY(leftPx,bottomPx)};
  float x0=cornerX[0], x1=cornerX[0], y0=cornerY[0], y1=cornerY[0];
  for (uint8_t i=1; i<4; ++i) {
    x0=min(x0,cornerX[i]); x1=max(x1,cornerX[i]);
    y0=min(y0,cornerY[i]); y1=max(y1,cornerY[i]);
  }
  x0 += EDGE_MARGIN_MM; x1 -= EDGE_MARGIN_MM;
  y0 += EDGE_MARGIN_MM; y1 -= EDGE_MARGIN_MM;

  if (x0 < X_MIN_MM || x1 > X_MAX_MM || y0 < Y_MIN_MM || y1 > Y_MAX_MM ||
      x1 - x0 < 1.0f || y1 - y0 < 1.0f) {
    Serial.println(F("RUN rejected: rectangle is invalid or outside configured workspace"));
    return;
  }

  if (!moveToMM(x0, y0)) return;
  bool moveRight = true;
  float y = y0;
  while (true) {
    if (!moveToMM(moveRight ? x1 : x0, y)) return;
    if (y >= y1) break;
    y = min(y + LINE_SPACING_MM, y1);
    if (!moveToMM(moveRight ? x1 : x0, y)) return;
    moveRight = !moveRight;
  }
  Serial.println(F("Rectangle raster dry run complete; plasma remained disabled"));
}

void processCommand(String line) {
  line.trim(); line.toUpperCase();
  if (line == "H") { homeMachine(); return; }
  if (line == "C" || line == "CORNERS") { testFourCorners(); return; }
  if (line == "CAL") {
    if (!homed) { Serial.println(F("CAL rejected: home first")); return; }
    calibrationMode=true; sampleCount=0;
    Serial.println(F("CAL mode: jog marker to 4 spread-out positions; click joystick at each"));
    return;
  }
  if (line == "STATUS") {
    Serial.print(F("Homed=")); Serial.print(homed);
    Serial.print(F(" Calibration=")); Serial.print(calibrationValid);
    Serial.print(F(" CalMode=")); Serial.print(calibrationMode);
    Serial.print(F(" Samples=")); Serial.println(sampleCount);
    return;
  }
  if (line == "RUN") { runDetectedRectangle(); return; }
  if (line == "HELP" || line == "?") {
    Serial.println(F("Commands: H=limit-switch home, C=four-corner dry run, CAL=calibrate, RUN=trace, STATUS=status"));
    return;
  }
  Serial.println(F("Unknown command. Send HELP for the command list."));
}

void setup() {
  Serial.begin(115200);
  pinMode(X_HOME_PIN, INPUT_PULLUP); pinMode(Y_HOME_PIN, INPUT_PULLUP);
  pinMode(JOY_X_PIN, INPUT); pinMode(JOY_Y_PIN, INPUT);
  pinMode(JOY_SW_PIN, INPUT_PULLUP);
  // Configure common-positive TB6600 pulse polarity before any homing motion.
  xMotor.setPinsInverted(false, true, false);
  yMotor.setPinsInverted(false, true, false);
  xMotor.setAcceleration(ACCEL_MM_S2 * STEPS_PER_MM_X);
  yMotor.setAcceleration(ACCEL_MM_S2 * STEPS_PER_MM_Y);
  pixy.init(); pixy.setLamp(0, 0);
  EEPROM.get(0, cal);
  calibrationValid = cal.magic == CAL_MAGIC && isfinite(cal.a) && isfinite(cal.b) &&
                     isfinite(cal.c) && isfinite(cal.d) && isfinite(cal.e) && isfinite(cal.f);
  Serial.println(F("Calibrated Pixy2 XY rectangle DRY RUN."));
  Serial.println(F("Send H + Enter to limit-switch home, or C + Enter for the four-corner dry run."));
  Serial.print(F("Saved calibration loaded: ")); Serial.println(calibrationValid ? F("YES") : F("NO"));
}

void loop() {
  if (!safetyOK()) return;
  updatePixyBlock();
  jogMachine();

  bool joyClick = digitalRead(JOY_SW_PIN) == LOW;
  if (joyClick && !oldJoyClick) {
    if (calibrationMode) captureCalibrationPoint();
    else runDetectedRectangle();
  }
  oldJoyClick = joyClick;

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (commandLine.length()) processCommand(commandLine);
      commandLine = "";
    } else if (commandLine.length() < 60) {
      commandLine += c;
    }
  }
}
