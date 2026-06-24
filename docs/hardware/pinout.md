# AEGIS — Arduino Mega 2560 Pin Map

Current machine wiring. This is the **authoritative** pin map and supersedes the
assignments printed in Appendix E of the ME 195B final report (an earlier
hardware revision). See the discrepancy note at the bottom.

## Stepper drivers (DM556, Pul+ / Dir+)

| Axis | Stepper object | Pul+ (pulse) | Dir+ (direction) | Wire colour |
|------|----------------|--------------|------------------|-------------|
| X    | `step1`        | 27           | 25               | purple / yellow |
| Y    | `step2`        | 24           | 22               | green / blue |
| Z    | `step3`        | 23           | 26               | orange / white |

## Limit switches (normally open)

| Axis | Pin | Wire colour |
|------|-----|-------------|
| X    | 49  | yellow |
| Y    | 51  | red    |
| Z    | 53  | blue   |

## Joystick (analog inputs)

| Signal           | Pin | Wire/notes |
|------------------|-----|------------|
| (unused)         | A0  | —          |
| VRy (joystick Y) | A1  | —          |
| VRx (joystick X) | A2  | —          |

## Discrepancy with final report (Appendix E)

The report's `MechanismCameraControl.ino` listing uses an **older** pin map that
no longer matches the hardware:

| Signal            | Report (Appendix E) | Current hardware |
|-------------------|---------------------|------------------|
| X Pulse / Dir     | 22 / 23             | 27 / 25          |
| Y Pulse / Dir     | 26 / 27             | 24 / 22          |
| Z Pulse / Dir     | 30 / 31             | 23 / 26          |
| Limit switch X/Y/Z| 42 / 44 / 46        | 49 / 51 / 53     |
| Joystick X / Y    | A0 / A1             | A2 / A1          |

If/when the full vision + homing + toolpath firmware is brought into this repo,
its pin definitions must be updated to the **current hardware** values above.
