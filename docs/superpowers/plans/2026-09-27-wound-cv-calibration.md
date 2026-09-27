# Wound CV Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a laptop-camera wound CV pipeline with future Kaggle YOLO training and dashboard OpenCV overlays.

**Architecture:** Create a focused `wound_cv_model` package for detection models, heuristic/YOLO inference, training entrypoint, and a local camera server. Extend the current dashboard to switch between Pixy and laptop CV feeds without using browser webcam APIs.

**Tech Stack:** Python 3, OpenCV, NumPy, optional Ultralytics YOLO, stdlib HTTP server, existing HTML dashboard.

**Spec:** `docs/superpowers/specs/2026-09-27-wound-cv-calibration-design.md`

## Global Constraints

- Do not train or download the Kaggle dataset in this implementation.
- Do not claim true geometric depth from a monocular laptop camera.
- Laptop camera mode is temporary development mode and must be labeled as such.
- Outputs must include `centroid_x_px`, `centroid_y_px`, `area_px2`, and `confidence` so existing coordinate planners can consume them.

---

### Task 1: Core wound detection package

**Files:**
- Create: `wound_cv_model/__init__.py`
- Create: `wound_cv_model/detection.py`
- Create: `wound_cv_model/depth.py`
- Test: `tests/test_wound_cv_model.py`

**Interfaces:**
- Produces: `WoundDetection.to_dict() -> dict`, `detections_to_csv_rows(list[WoundDetection]) -> list[dict]`, `estimate_depth_hint(area_ratio: float, redness_score: float) -> DepthEstimate`

- [x] Write failing serialization/depth tests.
- [x] Implement dataclasses and depth hint logic.
- [x] Run focused tests.

### Task 2: OpenCV inference and annotation

**Files:**
- Create: `wound_cv_model/inference.py`
- Modify: `tests/test_wound_cv_model.py`

**Interfaces:**
- Consumes: `WoundDetection`, `estimate_depth_hint`
- Produces: `HeuristicWoundDetector.detect(frame_bgr) -> list[WoundDetection]`, `draw_detections(frame_bgr, detections) -> frame_bgr`

- [x] Write synthetic-frame test with a red wound-like ellipse.
- [x] Implement red/pink contour heuristic fallback.
- [x] Implement overlay drawing.
- [x] Run focused tests.

### Task 3: Training and inference CLIs

**Files:**
- Create: `wound_cv_model/train.py`
- Create: `wound_cv_model/infer.py`
- Create: `wound_cv_model/requirements.txt`
- Create: `wound_cv_model/configs/wound_yolo.yaml`
- Create: `wound_cv_model/dataset.md`
- Create: `wound_cv_model/README.md`

**Interfaces:**
- Consumes: YOLO-format dataset YAML, optional trained weights.
- Produces: CSV detections compatible with `autonomous_movement/detections.csv`.

- [x] Implement CLIs with helpful dependency errors.
- [x] Document Kaggle dataset placement and training command.

### Task 4: Local laptop-camera CV server and dashboard integration

**Files:**
- Create: `wound_cv_model/camera_server.py`
- Modify: `docs/dashboard/motion_camera_dashboard_mockup.html`
- Test: `tests/test_wound_cv_server.py`

**Interfaces:**
- Produces endpoints: `/cv-frame.jpg`, `/cv-detections.json`, `/cv-status.json`, `/dashboard`.

- [x] Implement camera server with optional camera index and optional YOLO weights.
- [x] Update dashboard with Pixy/CV feed selector and detection polling.
- [x] Test status serialization without requiring a camera.

### Task 5: Verification and commit

**Files:**
- All changed files.

- [x] Run `python -m pytest -q`.
- [x] Commit the implementation.
