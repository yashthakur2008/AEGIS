# Wound CV model

This package is the AEGIS wound detection and calibration path.

## Live laptop-camera dashboard

```bash
python -m wound_cv_model.camera_server --host 127.0.0.1 --port 8766 --camera-index 0
```

Open `http://127.0.0.1:8766/dashboard`, select **Laptop CV**, then start the feed.

## Train later on Kaggle data

Download the dataset from Kaggle, convert it to YOLO format, then run:

```bash
python -m pip install -r wound_cv_model/requirements.txt
python -m wound_cv_model.train wound_cv_model/configs/wound_yolo.yaml --model yolo11n-seg.pt --epochs 80
```

## Single-image inference

```bash
python -m wound_cv_model.infer wound.jpg --weights runs/wound_cv/wound_yolo/weights/best.pt
```

Without `--weights`, inference uses the OpenCV red/pink contour fallback for testing.

## Depth / Z warning

`depth_hint` and `z_offset_hint_mm` are appearance-based hints only. A laptop monocular camera cannot measure true wound depth. Use real Z calibration before any autonomous Z motion.
