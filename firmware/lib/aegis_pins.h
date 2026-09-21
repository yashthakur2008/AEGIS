#pragma once

#include <Arduino.h>

// Authoritative Arduino Mega 2560 wiring for the current AEGIS gantry.
// Keep this file synchronized with docs/hardware/pinout.md.
constexpr uint8_t AEGIS_X_STEP_PIN = 27;
constexpr uint8_t AEGIS_X_DIR_PIN = 25;
constexpr uint8_t AEGIS_Y_STEP_PIN = 24;
constexpr uint8_t AEGIS_Y_DIR_PIN = 22;
constexpr uint8_t AEGIS_Z_STEP_PIN = 23;
constexpr uint8_t AEGIS_Z_DIR_PIN = 26;

constexpr uint8_t AEGIS_X_LIMIT_PIN = 49;
constexpr uint8_t AEGIS_Y_LIMIT_PIN = 51;
constexpr uint8_t AEGIS_Z_LIMIT_PIN = 53;

// PWM-capable plasma control output. Keep plasma disabled until safety validation.
constexpr uint8_t AEGIS_PLASMA_PWM_PIN = 6;

constexpr uint8_t AEGIS_JOYSTICK_Y_PIN = A1;
constexpr uint8_t AEGIS_JOYSTICK_X_PIN = A2;
