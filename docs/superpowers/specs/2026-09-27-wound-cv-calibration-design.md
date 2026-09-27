# Wound CV Calibration Design

## Goal
Build a local wound computer-vision path that can be trained later on the Kaggle wound dataset, can run now from the laptop camera in OpenCV, and exports detections compatible with the existing AEGIS coordinate planner.

## Scope
- Add a `wound_cv_model` package for dataset documentation, training scaffold, inference, heuristic fallback detection, and depth/Z estimation scaffolding.
- Add dashboard bridge endpoints for laptop-camera CV mode: annotated JPEG frame, detection JSON, and CV status.
- Keep Pixy2 direct work separate. The laptop camera mode is temporary for development and calibration at home.
- Do not claim true geometric wound depth from a single laptop camera. The system reports a `depth_hint` and `z_offset_hint_mm` derived from area/appearance until real depth calibration data exists.

## Architecture
`wound_cv_model.detection` defines the stable `WoundDetection` model and CSV/JSON output. `wound_cv_model.inference` runs either an Ultralytics YOLO model when weights are available or an OpenCV color/contour heuristic fallback for live testing. `wound_cv_model.camera_server` captures from the laptop camera, overlays detections, and serves dashboard-compatible endpoints.

## Data flow
Laptop camera frame → inference backend → wound detections → annotated OpenCV frame → dashboard `/cv-frame.jpg` and `/cv-detections.json` → existing coordinate calibration can consume detection centroids.

## Training
The Kaggle dataset is documented but not downloaded automatically. `train.py` expects a YOLO-format `data.yaml` and supports YOLO segmentation or detection weights. Users can download the dataset locally and convert labels if required.

## Depth/Z plan
Current implementation estimates `depth_hint` as `surface`, `shallow`, `moderate`, or `deep_risk` from normalized area and redness. This is only a planning hint. Later, Z calibration should replace this with measured camera-to-surface calibration using fiducials, stereo/depth hardware, or physical probe calibration.

## Testing
Unit tests cover detection serialization, heuristic detection on synthetic frames, depth hint behavior, and dashboard endpoint status without requiring a real camera or YOLO installation.
