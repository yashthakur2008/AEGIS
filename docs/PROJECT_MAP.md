# AEGIS Project Map

This repo is organized around the current build path: motion bring-up, camera/CV, calibration, and future CAP treatment.

## Live dashboard

- `docs/dashboard/motion_camera_dashboard_mockup.html` is the browser dashboard UI.
- Laptop CV mode now uses browser camera permissions directly with `getUserMedia` and browser-side red wound segmentation.
- Pixy mode is still available through the bridge when Pixy direct/PixyMon is needed.

Run the dashboard through either local server:

```bash
python -m wound_cv_model.camera_server --host 127.0.0.1 --port 8766 --camera-index 0
# then open http://127.0.0.1:8766/dashboard
```

or:

```bash
python -m host.aegis_control.pixymon_bridge --source direct
# then open http://127.0.0.1:8765/dashboard
```

## Wound CV model and detection

- `wound_cv_model/` contains the wound detection scaffold.
- `wound_cv_model/inference.py` has OpenCV heuristic detection and optional YOLO inference.
- `wound_cv_model/train.py` trains later against a YOLO-format dataset.
- `wound_cv_model/dataset.md` documents the Kaggle dataset placement and conversion expectations.
- Browser dashboard detection is currently a lightweight red segmentation overlay for rapid lab feedback.

## Autonomous movement calibration

- `autonomous_movement/` maps camera pixels to machine X/Y coordinates.
- `autonomous_movement/calibrate.py` builds calibration from fiducial point pairs.
- `autonomous_movement/move_from_detection.py` turns detection CSV rows into calibrated movement commands.
- Z is intentionally fixed until real depth/Z calibration exists.

## Host control

- `host/aegis_control/cli.py` plans MOVE commands from detections and optional calibration constants.
- `host/aegis_control/pixymon_bridge.py` serves Pixy dashboard endpoints.
- `host/aegis_control/pixy2_direct.py` is the direct Pixy2 USB adapter scaffold. It requires an installed Pixy2/libpixyusb2 Python binding.

## Firmware

- `firmware/xy_joystick_test/` is the current working X/Y joystick jog firmware.
- `firmware/xy_jog_test/` contains direct twitch/jog tests.
- `firmware/aegis_controller/` is the coordinate-command controller.
- `firmware/lib/aegis_pins.h` is the shared pin map.
- `docs/hardware/pinout.md` documents the current breadboard/driver wiring.

## Tests

Run all Python/static tests:

```bash
python -m pytest -q
```

Current coverage includes autonomous calibration, host planner behavior, Pixy bridge/direct adapter behavior, wound CV detection, and firmware static guardrails.

## Safety notes

- CAP/plasma must stay disconnected during walking, jogging, camera, and calibration tests.
- Browser/laptop monocular CV can detect appearance but cannot measure true wound depth.
- Do not automate Z or CAP from `depth_hint` until physical Z calibration and safety interlocks are validated.
