# Wound dataset setup

Dataset reference: https://www.kaggle.com/datasets/yasinpratomo/wound-dataset?select=Wound_dataset

Do not commit dataset images to this repo. Put downloaded data under:

```text
wound_cv_model/data/raw/Wound_dataset/
```

The training script expects YOLO format:

```text
wound_cv_model/data/yolo/
  images/train/*.jpg
  images/val/*.jpg
  labels/train/*.txt
  labels/val/*.txt
```

If the Kaggle archive only has class folders or masks, convert them to YOLO boxes/segments before training. Keep the final YAML at `wound_cv_model/configs/wound_yolo.yaml`.
