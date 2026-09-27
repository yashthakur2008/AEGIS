from __future__ import annotations

import argparse
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

import cv2  # type: ignore[import-not-found]
import numpy as np

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class DatasetSummary:
    images_seen: int
    labels_written: int
    skipped_without_mask: int


def list_images(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file())


def find_matching_mask(image: Path, mask_dir: Path) -> Path | None:
    candidates = [mask_dir / f"{image.stem}{suffix}" for suffix in IMAGE_EXTENSIONS]
    candidates += list(mask_dir.rglob(f"{image.stem}.*"))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTENSIONS:
            return candidate
    return None


def contour_to_yolo_polygon(contour: np.ndarray, width: int, height: int) -> str | None:
    if cv2.contourArea(contour) < 20:
        return None
    epsilon = 0.003 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    points = approx.reshape(-1, 2)
    if len(points) < 3:
        return None
    coords: list[str] = ["0"]
    for x, y in points:
        coords.append(f"{max(0.0, min(1.0, float(x) / width)):.6f}")
        coords.append(f"{max(0.0, min(1.0, float(y) / height)):.6f}")
    return " ".join(coords)


def mask_to_yolo_segments(mask_path: Path) -> list[str]:
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return []
    _, binary = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = binary.shape[:2]
    return [label for contour in contours if (label := contour_to_yolo_polygon(contour, width, height))]


def split_name(index: int, total: int, train_ratio: float, val_ratio: float) -> str:
    frac = index / max(total, 1)
    if frac < train_ratio:
        return "train"
    if frac < train_ratio + val_ratio:
        return "val"
    return "test"


def write_data_yaml(output_dir: Path) -> None:
    (output_dir / "data.yaml").write_text(
        f"path: {output_dir.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: wound\n"
    )


def prepare_from_masks(
    image_dir: Path,
    mask_dir: Path,
    output_dir: Path,
    *,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    seed: int = 7,
) -> DatasetSummary:
    images = list_images(image_dir)
    rng = random.Random(seed)
    rng.shuffle(images)
    for split in ["train", "val", "test"]:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    labels_written = 0
    skipped = 0
    for index, image in enumerate(images):
        mask = find_matching_mask(image, mask_dir)
        if mask is None:
            skipped += 1
            continue
        labels = mask_to_yolo_segments(mask)
        if not labels:
            skipped += 1
            continue
        split = split_name(index, len(images), train_ratio, val_ratio)
        shutil.copy2(image, output_dir / "images" / split / image.name)
        (output_dir / "labels" / split / f"{image.stem}.txt").write_text("\n".join(labels) + "\n")
        labels_written += 1
    write_data_yaml(output_dir)
    return DatasetSummary(len(images), labels_written, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert wound images + binary masks into YOLO segmentation format.")
    parser.add_argument("--images", type=Path, required=True, help="Directory containing source wound images.")
    parser.add_argument("--masks", type=Path, required=True, help="Directory containing binary wound masks with matching stems.")
    parser.add_argument("--output", type=Path, default=Path("wound_cv_model/data/yolo"))
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    summary = prepare_from_masks(args.images, args.masks, args.output, train_ratio=args.train_ratio, val_ratio=args.val_ratio, seed=args.seed)
    print(f"images_seen={summary.images_seen} labels_written={summary.labels_written} skipped_without_mask={summary.skipped_without_mask}")
    print(f"data_yaml={args.output / 'data.yaml'}")


if __name__ == "__main__":
    main()
