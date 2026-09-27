# Autonomous X/Y Movement Calibration

This folder is for the next AEGIS stage: convert Pixy/CV detections into X/Y machine movement.

Scope right now:

- X/Y motion only.
- No plasma commands.
- No Z-axis control beyond a fixed placeholder value.
- Detection source can be Pixy blocks, OpenCV, or a hand-written CSV.

## Data flow

```text
CV/Pixy detection pixel centroid -> XY calibration -> machine X/Y mm -> Arduino MOVE command
```

## 1. Capture calibration points

Create or edit `calibration_points.csv` with rows like:

```csv
pixel_x,pixel_y,machine_x_mm,machine_y_mm
120,90,0,0
520,90,100,0
120,390,0,75
520,390,100,75
```

Each row means: when the camera sees the target at `(pixel_x, pixel_y)`, the gantry/tool is known to be at `(machine_x_mm, machine_y_mm)`.

Use at least 3 points. Four or more spread across the workspace is better.

## 2. Fit calibration

```bash
python -m autonomous_movement.calibrate autonomous_movement/calibration_points.csv \
  --output autonomous_movement/calibration.json
```

## 3. Plan moves from detections

Create or edit `detections.csv`:

```csv
centroid_x_px,centroid_y_px,area_px2,confidence
300,220,2500,0.9
```

Print motion-only commands:

```bash
python -m autonomous_movement.move_from_detection autonomous_movement/detections.csv \
  --calibration autonomous_movement/calibration.json
```

Send directly to Arduino:

```bash
python -m autonomous_movement.move_from_detection autonomous_movement/detections.csv \
  --calibration autonomous_movement/calibration.json \
  --serial-port /dev/cu.usbmodem11301
```

## Later

- Replace CSV detections with live Pixy/OpenCV detections.
- Add depth/Z only after X/Y calibration works.
- Add plasma intensity/dwell only after motion-only validation and safety interlocks.
