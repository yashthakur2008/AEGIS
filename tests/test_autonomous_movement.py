import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autonomous_movement.calibrate import load_samples_or_exit, main as calibrate_main
from autonomous_movement.calibration import CalibrationSample, XYCalibration, load_samples, solve_affine
from autonomous_movement.move_from_detection import load_calibration_or_exit, load_detections_or_exit
from autonomous_movement.movement import Detection, detection_to_move_command, load_detections, plan_move_commands


def test_solve_affine_maps_pixel_points_to_machine_xy():
    calibration = solve_affine(
        [
            CalibrationSample(120, 90, 0, 0),
            CalibrationSample(520, 90, 100, 0),
            CalibrationSample(120, 390, 0, 75),
            CalibrationSample(520, 390, 100, 75),
        ]
    )

    x_mm, y_mm = calibration.image_to_machine(300, 220)

    assert round(x_mm, 3) == 45.000
    assert round(y_mm, 3) == 32.500


def test_detection_to_move_command_keeps_z_fixed_for_xy_only_stage():
    calibration = XYCalibration(a=0.25, b=0, c=-30, d=0, e=0.25, f=-22.5)

    command = detection_to_move_command(Detection(300, 220, 2500, 0.9), calibration)

    assert command == "MOVE 45.000 32.500 0.000"


def test_plan_move_commands_handles_multiple_detections():
    calibration = XYCalibration(a=1, b=0, c=0, d=0, e=1, f=0)

    commands = plan_move_commands([Detection(1, 2), Detection(3, 4)], calibration)

    assert commands == ["MOVE 1.000 2.000 0.000", "MOVE 3.000 4.000 0.000"]


def test_autonomous_detection_loader_reports_missing_columns(tmp_path: Path):
    detections_csv = tmp_path / "detections.csv"
    detections_csv.write_text("centroid_x_px,area_px2\n10,100\n", encoding="utf-8")

    try:
        load_detections(detections_csv)
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected missing detection column error")

    assert str(detections_csv) in message
    assert "missing required detection CSV column" in message
    assert "centroid_y_px" in message


def test_autonomous_detection_cli_reports_bad_numeric_line(tmp_path: Path):
    detections_csv = tmp_path / "detections.csv"
    detections_csv.write_text("centroid_x_px,centroid_y_px,area_px2\n10,bad,100\n", encoding="utf-8")

    try:
        load_detections_or_exit(detections_csv)
    except SystemExit as exc:
        message = str(exc)
    else:
        raise AssertionError("expected detection numeric SystemExit")

    assert str(detections_csv) in message
    assert "line 2" in message
    assert "must be numbers" in message


def test_autonomous_calibration_loader_reports_missing_columns(tmp_path: Path):
    samples_csv = tmp_path / "calibration.csv"
    samples_csv.write_text("pixel_x,pixel_y,machine_x_mm\n10,20,30\n", encoding="utf-8")

    try:
        load_samples(samples_csv)
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected missing calibration column error")

    assert str(samples_csv) in message
    assert "missing required calibration CSV column" in message
    assert "machine_y_mm" in message


def test_autonomous_calibration_cli_reports_bad_numeric_line(tmp_path: Path):
    samples_csv = tmp_path / "calibration.csv"
    samples_csv.write_text("pixel_x,pixel_y,machine_x_mm,machine_y_mm\n10,20,bad,40\n", encoding="utf-8")

    try:
        load_samples_or_exit(samples_csv)
    except SystemExit as exc:
        message = str(exc)
    else:
        raise AssertionError("expected calibration numeric SystemExit")

    assert str(samples_csv) in message
    assert "line 2" in message
    assert "must be numbers" in message


def test_autonomous_calibration_cli_creates_nested_output(tmp_path: Path, monkeypatch):
    samples_csv = tmp_path / "samples.csv"
    samples_csv.write_text(
        "pixel_x,pixel_y,machine_x_mm,machine_y_mm\n"
        "0,0,0,0\n"
        "10,0,10,0\n"
        "0,10,0,10\n",
        encoding="utf-8",
    )
    output = tmp_path / "nested" / "calibration" / "calibration.json"
    monkeypatch.setattr("sys.argv", ["calibrate", str(samples_csv), "--output", str(output)])

    calibrate_main()

    assert output.exists()
    calibration = XYCalibration.from_json(output.read_text(encoding="utf-8"))
    assert calibration.image_to_machine(5, 7) == (5, 7)


def test_move_from_detection_reports_invalid_calibration_json(tmp_path: Path):
    calibration_json = tmp_path / "calibration.json"
    calibration_json.write_text("not json", encoding="utf-8")

    try:
        load_calibration_or_exit(calibration_json)
    except SystemExit as exc:
        message = str(exc)
    else:
        raise AssertionError("expected invalid calibration JSON SystemExit")

    assert str(calibration_json) in message
    assert "Invalid calibration JSON" in message
