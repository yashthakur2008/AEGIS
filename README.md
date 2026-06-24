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
  jog_test/          Bench-test sketch — jogs all 3 axes via serial (f/b/s)
docs/
  ME-195B-Final-Report.pdf   Full project report (background + Appendix E firmware)
  hardware/
    pinout.md        Authoritative Arduino Mega pin map + wiring
tests/
```

## Firmware

- **`firmware/jog_test/`** — bring-up sketch to verify motor wiring and driver
  direction before running the full control firmware. Requires the
  [`AccelStepper`](https://www.airspayce.com/mikem/arduino/AccelStepper/) library.
  Upload via the Arduino IDE (board: Arduino Mega 2560), open Serial Monitor at
  **115200 baud**, then send `f` / `b` / `s`.

The pin map in the sketches reflects the **current hardware wiring**, documented
in [`docs/hardware/pinout.md`](docs/hardware/pinout.md). Note that this
supersedes the (outdated) pin assignments in Appendix E of the final report.
