# Wound CV model

This package is the AEGIS wound detection and calibration path.

## Live laptop-camera dashboard

```bash
python -m wound_cv_model.camera_server --host 127.0.0.1 --port 8766 --camera-index 0
```

Open `http://127.0.0.1:8766/dashboard`, select **Laptop CV**, then start the feed. Browser camera mode uses `getUserMedia` directly. The current in-browser overlay is still heuristic and should be replaced by trained weights once available.

You can also attach a still image from the dashboard. The server returns `is_wound`, `wound_count`, every detected wound box/centroid/confidence, and relative `depth_hint` / `z_offset_hint_mm` values for each wound. These Z values are monocular appearance hints only, not safe physical depth measurements.

## Dataset conversion for segmentation training

The robot needs localization/segmentation, not only classification. If you have wound images and binary masks with matching filenames, convert them to YOLO segmentation format:

```bash
python -m wound_cv_model.prepare_yolo_dataset \
  --images wound_cv_model/data/raw/images \
  --masks wound_cv_model/data/raw/masks \
  --output wound_cv_model/data/yolo
```

This writes `wound_cv_model/data/yolo/data.yaml` plus YOLO polygon labels.

## Train locally or on RunPod

Install dependencies:

```bash
python -m pip install -r wound_cv_model/requirements.txt
```

Local training:

```bash
python -m wound_cv_model.train wound_cv_model/data/yolo/data.yaml --model yolo11n-seg.pt --epochs 100
```

RunPod training after cloning/uploading the repo and dataset:

```bash
bash wound_cv_model/runpod_train.sh wound_cv_model/data/yolo/data.yaml
```

Expected artifact:

```text
runs/wound_cv/aegis_wound_yolo_seg/weights/best.pt
```

## Evaluate images before dashboard integration

```bash
python -m wound_cv_model.evaluate path/to/wound_images --weights runs/wound_cv/aegis_wound_yolo_seg/weights/best.pt
```

Without `--weights`, evaluation uses the OpenCV red/pink contour fallback and writes annotated images plus `report.json` under `runs/wound_eval/`.

## Single-image inference CSV

```bash
python -m wound_cv_model.infer wound.jpg --weights runs/wound_cv/aegis_wound_yolo_seg/weights/best.pt
```

The CSV output is compatible with the autonomous movement calibration path.

## Depth / Z warning

`depth_hint` and `z_offset_hint_mm` are appearance-based hints only. A laptop monocular camera cannot measure true wound depth. Use real Z calibration before any autonomous Z motion.

## More details

See `docs/architecture/wound_model_training.md` for repo references, RunPod workflow, and acceptance criteria.
