#!/usr/bin/env bash
set -euo pipefail

DATA_YAML=${1:-wound_cv_model/data/yolo/data.yaml}
MODEL=${MODEL:-yolo11n-seg.pt}
EPOCHS=${EPOCHS:-100}
IMGSZ=${IMGSZ:-640}
PROJECT=${PROJECT:-runs/wound_cv}
NAME=${NAME:-aegis_wound_yolo_seg}

python -m pip install --upgrade pip
python -m pip install -r wound_cv_model/requirements.txt
python -m wound_cv_model.train "$DATA_YAML" --model "$MODEL" --epochs "$EPOCHS" --imgsz "$IMGSZ" --project "$PROJECT" --name "$NAME"

echo "Best weights should be under: $PROJECT/$NAME/weights/best.pt"
