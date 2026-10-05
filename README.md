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
  aegis_controller/  Coordinate-based controller firmware (HOME/MOVE/PLASMA/STOP/STATUS)
  jog_test/          Bench-test sketch — jogs all 3 axes via serial (f/b/s)
  xy_jog_test/       X/Y twitch and jog bring-up sketches
  xy_joystick_test/  Current safe X/Y joystick control sketch
  lib/               Shared Arduino headers, including authoritative pin map
host/
  aegis_control/     Host-side CV/Pixy detection → calibrated MOVE/PLASMA planner
autonomous_movement/ Camera-pixel → machine-coordinate calibration tools
wound_cv_model/      Wound model training, inference, and laptop camera CV server
docs/
  architecture/      Wound-to-coordinate pipeline notes
  dashboard/         Browser motion/camera dashboard
  PROJECT_MAP.md     Current map of the active subsystems
  ME-195B-Final-Report.pdf   Full project report (background + Appendix E firmware)
  hardware/
    pinout.md        Authoritative Arduino Mega pin map + wiring
tests/
  test_*.py          Python, dashboard, CV, Pixy, calibration, and firmware guardrails
```

For the current subsystem map, see [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).

## Firmware

- **`firmware/aegis_controller/`** — primary motion controller. Build with
  PlatformIO:

  ```bash
  pio run
  ```

  Serial protocol at **115200 baud**:
  - `HOME`
  - `MOVE <x_mm> <y_mm> <z_mm>`
  - `PLASMA <intensity_0_to_1> <dwell_ms>`
  - `STATUS`
  - `STOP`

## Host CV planner

The host-side planner turns Pixy2/CV detections into calibrated gantry commands:

```bash
python -m host.aegis_control.cli detections.csv \
  --x-mm-per-px 0.5 --y-mm-per-px 0.5 \
  --x-offset-mm 10 --y-offset-mm 12
```

To send the planned motion-only `MOVE` commands directly to the Arduino controller after calibration values are known:

```bash
python -m host.aegis_control.cli detections.csv \
  --x-mm-per-px 0.5 --y-mm-per-px 0.5 \
  --x-offset-mm 10 --y-offset-mm 12 \
  --serial-port /dev/cu.usbmodem11301
```

The CSV contract is one detection per row with `centroid_x_px`, `centroid_y_px`, `area_px2`, and optional `confidence`. This stage intentionally sends motion first. Add `--emit-plasma` only after motion-only validation, CAP driver wiring, and safety interlocks are confirmed.

For hardware-free validation of the same HOME/MOVE/STATUS flow, use the in-memory controller simulator:

```bash
python -m host.aegis_control.cli detections.csv \
  --x-mm-per-px 0.5 --y-mm-per-px 0.5 \
  --simulate-controller
```

The simulator refuses PLASMA by default and is intended for dry-run motion workflow checks before connecting hardware.

- **`firmware/jog_test/`** — bring-up sketch to verify motor wiring, driver
  direction, and limit switches before running the full control firmware.
  Requires the [`AccelStepper`](https://www.airspayce.com/mikem/arduino/AccelStepper/) library.
  Upload via the Arduino IDE (board: Arduino Mega 2560), open Serial Monitor at
  **115200 baud**, then send `f` / `b` / `s`.

The pin map in the sketches reflects the **current hardware wiring**, documented
in [`docs/hardware/pinout.md`](docs/hardware/pinout.md). Note that this
supersedes the (outdated) pin assignments in Appendix E of the final report.

## Browser dashboard and wound CV

The dashboard is at [`docs/dashboard/motion_camera_dashboard_mockup.html`](docs/dashboard/motion_camera_dashboard_mockup.html). The easiest development path is the laptop camera mode:

```bash
python -m wound_cv_model.camera_server --host 127.0.0.1 --port 8766 --camera-index 0
```

Open `http://127.0.0.1:8766/dashboard`, select **Laptop CV**, click **Start Feed**, and approve the browser camera permission. Laptop CV uses browser `getUserMedia` directly and overlays a lightweight red wound segmentation box. The wound CV package also includes OpenCV heuristic inference, optional YOLO inference, and training scaffolding for the Kaggle wound dataset.

## Pixy camera dashboard

Pixy2 is not a UVC webcam, so it cannot be opened like a normal Mac camera. The Pixy bridge exposes Pixy endpoints for the dashboard. Direct USB requires a Pixy2/libpixyusb2 Python binding; PixyMon screen capture is only a fallback.

```bash
python -m host.aegis_control.pixymon_bridge --source direct
```

Open `http://127.0.0.1:8765/dashboard` and click **Start Feed**. The bridge uses `/pixy-stream.mjpg`, `/pixy-frame.jpg`, `/pixy-blocks.json`, and `/pixy-status.json`.

## Architecture

See [`docs/architecture/wound_to_coordinate_pipeline.md`](docs/architecture/wound_to_coordinate_pipeline.md)
for the intended wound image → calibrated machine coordinates → gantry toolpath
pipeline.
