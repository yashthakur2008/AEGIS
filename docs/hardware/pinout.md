# AEGIS — Arduino Mega 2560 Pin Map

Current machine wiring. This is the **authoritative** pin map and supersedes the
assignments printed in Appendix E of the ME 195B final report (an earlier
hardware revision). See the discrepancy note at the bottom.

## Stepper drivers (verified breadboard bring-up wiring)

Driver `PUL+` and `DIR+` are tied to the Arduino 5V rail. The Arduino pins below
drive `PUL-` and `DIR-`.

| Axis | Stepper object | PUL- / STEP | DIR- / DIR | Notes |
|------|----------------|-------------|------------|-------|
| X    | `step1`        | 7           | 6          | Verified moving during XY jog test |
| Y    | `step2`        | 5           | 4          | Verified moving during XY jog test |
| Z    | `step3`        | 23          | 26         | Not connected during current XY-only bring-up |

## Limit switches (normally open)

| Axis | Pin | Wire colour |
|------|-----|-------------|
| X    | 49  | yellow |
| Y    | 51  | red    |
| Z    | 53  | blue   |

## Joystick (analog inputs)

| Signal           | Pin | Wire/notes |
|------------------|-----|------------|
| VRx (joystick X) | A11 | Verified during XY joystick test |
| VRy (joystick Y) | A12 | Verified during XY joystick test |
| SW/MS            | 13  | Optional stop/disarm input |
| VCC              | 5V rail | Breadboard `+` rail |
| GND              | GND rail | Breadboard `-` rail |

## Plasma control

| Signal | Pin | Wire/notes |
|--------|-----|------------|
| Plasma PWM enable/intensity | 44 | PWM-capable placeholder output. Keep disconnected or disabled until CAP driver interface and safety interlock are validated. |

## Discrepancy with final report (Appendix E)

The report's `MechanismCameraControl.ino` listing uses an **older** pin map that
no longer matches the hardware:

| Signal            | Report (Appendix E) | Current hardware |
|-------------------|---------------------|------------------|
| X Pulse / Dir     | 22 / 23             | 7 / 6            |
| Y Pulse / Dir     | 26 / 27             | 5 / 4            |
| Z Pulse / Dir     | 30 / 31             | 23 / 26          |
| Limit switch X/Y/Z| 42 / 44 / 46        | 49 / 51 / 53     |
| Joystick X / Y    | A0 / A1             | A11 / A12        |

If/when the full vision + homing + toolpath firmware is brought into this repo,
its pin definitions must be updated to the **current hardware** values above.
