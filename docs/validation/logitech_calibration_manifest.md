# Logitech calibration metadata workflow

Use this when the Logitech camera is plugged in and selected in the dashboard. The goal is to preserve camera/source evidence for later relative-depth calibration without implying safe autonomous Z control.

## Create a manifest

```bash
python -m wound_cv_model.logitech_calibration \
  --camera-label "Logitech C920" \
  --device-id-hint "browser device label or OpenCV index" \
  --width 1280 --height 720 --fps 30 \
  --sample close:logitech_close.jpg:120 \
  --sample working:logitech_working.jpg:180 \
  --sample far:logitech_far.jpg:260 \
  --output docs/validation/logitech_calibration_manifest.json
```

Required buckets:

- `close`
- `working`
- `far`

Each sample is `bucket:image[:distance_mm]`. Distance is optional but recommended when a ruler or fixed gantry Z/stand-off measurement is available.

## Safety rule

The manifest records relative calibration evidence only. It must not be used to drive autonomous Z motion until the camera mount, gantry geometry, and physical depth calibration are validated.
