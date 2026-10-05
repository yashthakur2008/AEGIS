from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_movement.calibration import load_samples, solve_affine


def load_samples_or_exit(path: Path):
    try:
        return load_samples(path)
    except OSError as exc:
        raise SystemExit(f"Could not read calibration CSV {path}: {exc}") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit autonomous X/Y pixel-to-machine calibration.")
    parser.add_argument("samples_csv", type=Path, help="CSV with pixel_x,pixel_y,machine_x_mm,machine_y_mm")
    parser.add_argument("--output", type=Path, default=Path("autonomous_movement/calibration.json"))
    args = parser.parse_args()

    calibration = solve_affine(load_samples_or_exit(args.samples_csv))
    args.output.write_text(calibration.to_json())
    print(f"Wrote {args.output}")
    print(calibration.to_json(), end="")


if __name__ == "__main__":
    main()
