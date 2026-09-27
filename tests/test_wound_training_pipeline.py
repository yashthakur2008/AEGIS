from __future__ import annotations

import cv2  # type: ignore[import-not-found]
import numpy as np

from wound_cv_model.prepare_yolo_dataset import mask_to_yolo_segments, prepare_from_masks


def test_mask_to_yolo_segments_outputs_normalized_polygon(tmp_path):
    mask = np.zeros((80, 100), dtype=np.uint8)
    cv2.rectangle(mask, (20, 15), (70, 55), 255, -1)
    mask_path = tmp_path / "wound.png"
    cv2.imwrite(str(mask_path), mask)

    labels = mask_to_yolo_segments(mask_path)

    assert len(labels) == 1
    parts = labels[0].split()
    assert parts[0] == "0"
    coords = [float(value) for value in parts[1:]]
    assert len(coords) >= 6
    assert all(0.0 <= value <= 1.0 for value in coords)


def test_prepare_from_masks_creates_yolo_dataset(tmp_path):
    image_dir = tmp_path / "images"
    mask_dir = tmp_path / "masks"
    output_dir = tmp_path / "yolo"
    image_dir.mkdir()
    mask_dir.mkdir()
    for index in range(3):
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        image[:] = (80, 80, 120)
        mask = np.zeros((64, 64), dtype=np.uint8)
        cv2.circle(mask, (32, 32), 12, 255, -1)
        cv2.imwrite(str(image_dir / f"sample_{index}.jpg"), image)
        cv2.imwrite(str(mask_dir / f"sample_{index}.png"), mask)

    summary = prepare_from_masks(image_dir, mask_dir, output_dir, seed=1)

    assert summary.images_seen == 3
    assert summary.labels_written == 3
    assert (output_dir / "data.yaml").exists()
    label_files = list((output_dir / "labels").rglob("*.txt"))
    assert len(label_files) == 3
