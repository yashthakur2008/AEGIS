# AEGIS

The **Autonomous Epidermal and Germicidal Imaging System (AEGIS)** is a
theranostics dermatological robot: a 3-axis gantry that uses image processing to
detect open wounds and applies Cold Atmospheric Plasma (CAP) treatment over an
automatically generated toolpath.

The machine runs on an Arduino Mega 2560 driving NEMA-class steppers through
DM556 microstepper drivers, with limit-switch homing, a Pixy2 camera for wound
detection, and safety features (emergency stop, IR temperature monitoring).

## Repository layout

```
firmware/
  aegis_controller/  Coordinate-based controller firmware (HOME/MOVE/STOP/STATUS)
  jog_test/          Bench-test sketch — jogs all 3 axes via serial (f/b/s)
  lib/               Shared Arduino headers, including authoritative pin map
docs/
  architecture/      Wound-to-coordinate pipeline notes
  ME-195B-Final-Report.pdf   Full project report (background + Appendix E firmware)
  hardware/
    pinout.md        Authoritative Arduino Mega pin map + wiring
tests/
  test_firmware_static.py    Static firmware guardrails
```

## Firmware

- **`firmware/aegis_controller/`** — primary motion controller. Build with
  PlatformIO:

  ```bash
  pio run
  ```

  Serial protocol at **115200 baud**:
  - `HOME`
  - `MOVE <x_mm> <y_mm> <z_mm>`
  - `STATUS`
  - `STOP`

- **`firmware/jog_test/`** — bring-up sketch to verify motor wiring, driver
  direction, and limit switches before running the full control firmware.
  Requires the [`AccelStepper`](https://www.airspayce.com/mikem/arduino/AccelStepper/) library.
  Upload via the Arduino IDE (board: Arduino Mega 2560), open Serial Monitor at
  **115200 baud**, then send `f` / `b` / `s`.

The pin map in the sketches reflects the **current hardware wiring**, documented
in [`docs/hardware/pinout.md`](docs/hardware/pinout.md). Note that this
supersedes the (outdated) pin assignments in Appendix E of the final report.

## Architecture

See [`docs/architecture/wound_to_coordinate_pipeline.md`](docs/architecture/wound_to_coordinate_pipeline.md)
for the intended wound image → calibrated machine coordinates → gantry toolpath
pipeline.
