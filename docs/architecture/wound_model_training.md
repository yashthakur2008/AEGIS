# Wound model training plan

Pixy work is deferred. The active CV goal is a wound localization/segmentation model that can produce centroids and masks for the AEGIS coordinate pipeline.

## Reference repos reviewed

- `uwm-bigdata/wound-segmentation`: best fit. It targets 2D wound area segmentation, includes annotated wound segmentation data, and evaluates U-Net, MobileNetV2, Mask-RCNN, SegNet, and VGG16.
- `uwm-bigdata/DFUTissueSegNet`: useful later for tissue type segmentation. It is smaller and focused on DFU tissue classes.
- `uwm-bigdata/wound_localization`: relevant conceptually, but the public README has little implementation detail.
- `uwm-bigdata/wound_classification` and `wound-classification-using-images-and-locations`: useful later for wound type classification, but classification alone does not give robot target coordinates.
- Kaggle `yasinpratomo/wound-dataset`: useful image source, but it must be checked for labels/masks before segmentation training.

## Chosen model path

Use wound segmentation first. Robot motion needs wound location and shape. Wound type classification can be layered on after localization works.

Preferred training target is YOLO segmentation because it gives:

- bounding boxes for quick dashboard overlay,
- masks for wound area and centroid,
- a simple `best.pt` artifact that can run locally or on RunPod,
- an easier bridge into the existing `wound_cv_model.inference` code.

## Local dataset conversion

If images and binary masks have matching stems:

```bash
python -m wound_cv_model.prepare_yolo_dataset \
  --images wound_cv_model/data/raw/images \
  --masks wound_cv_model/data/raw/masks \
  --output wound_cv_model/data/yolo
```

This creates:

```text
wound_cv_model/data/yolo/
  data.yaml
  images/train|val|test/
  labels/train|val|test/*.txt
```

The label files are YOLO segmentation polygons with class `0: wound`.

## RunPod training

On a RunPod GPU pod, clone this repo, upload or mount `wound_cv_model/data/yolo`, then run:

```bash
cd /workspace/AEGIS
bash wound_cv_model/runpod_train.sh wound_cv_model/data/yolo/data.yaml
```

Optional overrides:

```bash
MODEL=yolo11s-seg.pt EPOCHS=150 IMGSZ=768 bash wound_cv_model/runpod_train.sh wound_cv_model/data/yolo/data.yaml
```

Expected artifact:

```text
runs/wound_cv/aegis_wound_yolo_seg/weights/best.pt
```

## Offline evaluation

Before trusting dashboard behavior, run the detector on saved wound images:

```bash
python -m wound_cv_model.evaluate path/to/images --weights runs/wound_cv/aegis_wound_yolo_seg/weights/best.pt
```

Without `--weights`, it uses the heuristic detector and writes annotated images plus `report.json`.

## Acceptance criteria before robot use

- Model detects the printed wound target in lab lighting.
- `evaluate.py` report shows detections on representative wound images.
- Dashboard overlay shows a stable box/mask on the target, not face/hair/background.
- The output centroid maps through `autonomous_movement` to plausible X/Y motion.
- Z/CAP remain disabled until physical calibration and safety interlocks are validated.
