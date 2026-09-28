# AEGIS prototype roadmap

This roadmap turns the durable initiatives into an implementation sequence from the current wound-CV dashboard to the final prototype demo.

## Ground rules

- The old Pixy dashboard feed was a **PixyMon screen capture**, not raw Pixy2 camera data. Do not treat it as calibrated camera input.
- Attached-image wound analysis must support **multiple wounds in one image**. Each wound gets its own box, centroid, confidence, wound status, and relative depth/distance hint.
- Monocular depth is only a **relative calibration hint** until a real camera geometry calibration exists. Do not drive autonomous Z from it.
- CAP/plasma power stays disconnected for walking, jog, camera, and dry-run alignment tests.

## Chronological initiatives

### 1. Stabilize the wound CV dashboard

Initiative: `aegis-dashboard-stabilization`

Goal: make the current dashboard reliable enough to use during experiments.

Deliverables:

- Smooth browser camera feed.
- YOLO-only wound overlay, with skin-prone local color tracker disabled.
- Detection boxes with centroid, confidence, `is_wound`, `wound_count`, and relative depth hints.
- Clear detector status, last error, latency, and restart instructions.
- Regression checks for normal skin, background, close/mid/far wound print positions, and moving target behavior.

Acceptance gate:

- Dashboard starts at `http://127.0.0.1:8766/dashboard`.
- Live feed is smooth while inference runs.
- Normal skin is not detected as a wound.
- Wound print is detected in controlled close/mid/far cases.
- JS syntax and Python tests pass.

Immediate next actions:

1. Add detector latency and last-error fields to the visible dashboard UI.
2. Write a short operator checklist for restart, hard refresh, and test flow.
3. Re-test the printed wound target and normal skin after hard refresh.

---

### 2. Build copy/paste sample wound detector

Initiative: `aegis-sample-wound-detector`

Goal: create a repeatable still-image detector for pasted/uploaded wound examples before relying on live camera conditions.

Deliverables:

- Dedicated sample detector panel separate from live camera.
- Clipboard paste, drag/drop, and file upload.
- Multiple-wound detection in a single attached image.
- Per-wound output: wound status, box, centroid, confidence, area, relative depth hint, z-offset hint.
- Small smoke-test sample set: wound print, normal skin, background, far target, close target, and multi-wound image.

Acceptance gate:

- User can copy/paste a screenshot or image directly into the dashboard.
- Detector can report `wound_count > 1` and render each wound independently.
- Negative examples report `is_wound: false` and `wound_count: 0`.
- Results do not interfere with the live camera feed.

Immediate next actions:

1. Move current attached-image input into a dedicated sample detector panel.
2. Add paste and drag/drop handlers.
3. Create a five-to-six-image local smoke-test set and a replay script.

---

### 3. Move vision from laptop camera to Logitech camera

Initiative: `aegis-logitech-camera-integration`

Goal: make the Logitech camera the representative live prototype vision source.

Deliverables:

- Camera device enumeration through browser `getUserMedia`.
- Source selector for laptop camera vs Logitech camera.
- Logitech default resolution/FPS selected for smooth feed and acceptable inference latency.
- Close/mid/far calibration images captured from the Logitech camera.
- Updated relative depth buckets for Logitech field of view and mounting distance.

Acceptance gate:

- Dashboard reliably lists and selects the Logitech camera.
- Logitech feed stays smooth at chosen resolution/FPS.
- YOLO boxes align with the Logitech video frame.
- Laptop camera remains available as a fallback.
- Depth labels are recalibrated for Logitech geometry and still marked relative-only.

Immediate next actions:

1. Add camera selector using `navigator.mediaDevices.enumerateDevices()`.
2. Plug in Logitech and record label/deviceId behavior on macOS.
3. Measure 720p vs 1080p smoothness and inference latency.

---

### 4. Integrate motion controls with vision safety gates

Initiative: `aegis-motion-integration-safety`

Goal: connect wound localization to motion planning only through safe, supervised dry-run controls.

Deliverables:

- Verified manual X/Y/Z jog controls.
- HOME / limit-switch zeroing check.
- STOP button visible and tested.
- Camera-space target-center overlay.
- Wound centroid to X/Y offset suggestion, not automatic motion.
- Dry-run alignment workflow with CAP/plasma power disconnected.

Acceptance gate:

- Manual jog commands work on firmware or simulator.
- HOME and STOP are verified before vision-driven work.
- Dashboard can show a suggested X/Y correction from wound centroid to target center.
- Autonomous Z remains blocked until real calibration exists.

Immediate next actions:

1. Confirm current firmware command protocol.
2. Add simulator mode if hardware is not attached.
3. Add target-center overlay and suggested jog vector.

---

### 5. Final integrated AEGIS prototype demo

Initiative: `aegis-final-prototype-demo`

Goal: package everything into one repeatable demonstration.

Deliverables:

- Clean startup checklist or one-command launcher.
- Sample detector demo with positive, negative, and multi-wound images.
- Logitech live detection demo.
- Manual-supervised motion dry-run alignment demo.
- Screenshot/video/log evidence.
- Known limitations and fallback plan.

Acceptance gate:

- Demo can be run from a fresh session without code edits.
- Logitech feed is smooth and selected in the dashboard.
- Sample detector demonstrates pasted image workflow.
- Live detector finds the wound target without detecting normal skin as wound.
- Motion dry-run is safe and clearly separated from treatment/plasma power.
- Logs/screenshots prove what happened if live demo conditions fail.

Immediate next actions:

1. Write final demo script after initiatives 1-4 pass.
2. Decide which parts are live and which have prerecorded fallback evidence.
3. Freeze a final branch/tag after the acceptance checklist passes.

## Suggested execution order

1. Finish dashboard stabilization items that reduce live-demo risk.
2. Build the sample detector so model quality can be tested repeatably.
3. Integrate Logitech and recalibrate relative depth buckets.
4. Add safe motion dry-run alignment.
5. Rehearse and freeze the final demo.
