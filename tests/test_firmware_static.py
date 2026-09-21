from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_platformio_builds_coordinate_controller_by_default():
    config = (ROOT / "platformio.ini").read_text()
    assert "default_envs = megaatmega2560" in config
    assert "src_dir = firmware/aegis_controller" in config
    assert "include_dir = firmware/lib" in config
    assert "waspinator/AccelStepper@^1.64" in config


def test_architecture_doc_matches_firmware_protocol_and_safety_contract():
    doc = (ROOT / "docs/architecture/wound_to_coordinate_pipeline.md").read_text()
    for command in ("HOME", "MOVE <x_mm> <y_mm> <z_mm>", "STOP", "STATUS"):
        assert command in doc
    for frame in ("Image", "Machine", "Motor"):
        assert frame in doc
    assert "Keep CAP disabled by default" in doc
    assert "Verify limit switch polarity" in doc


def test_readme_exposes_build_and_pipeline_entry_points():
    readme = (ROOT / "README.md").read_text()
    assert "pio run" in readme
    assert "firmware/aegis_controller/" in readme
    assert "docs/architecture/wound_to_coordinate_pipeline.md" in readme


def test_gitignore_excludes_generated_build_outputs():
    gitignore = (ROOT / ".gitignore").read_text()
    for pattern in (".pio/", "__pycache__/", ".pytest_cache/"):
        assert pattern in gitignore


def test_shared_pin_header_matches_documented_current_wiring():
    header = (ROOT / "firmware/lib/aegis_pins.h").read_text()
    expected = {
        "AEGIS_X_STEP_PIN": "27",
        "AEGIS_X_DIR_PIN": "25",
        "AEGIS_Y_STEP_PIN": "24",
        "AEGIS_Y_DIR_PIN": "22",
        "AEGIS_Z_STEP_PIN": "23",
        "AEGIS_Z_DIR_PIN": "26",
        "AEGIS_X_LIMIT_PIN": "49",
        "AEGIS_Y_LIMIT_PIN": "51",
        "AEGIS_Z_LIMIT_PIN": "53",
    }
    for name, value in expected.items():
        assert f"constexpr uint8_t {name} = {value};" in header


def test_jog_test_uses_shared_pin_map_and_limit_safety():
    firmware = (ROOT / "firmware/jog_test/jog_test.ino").read_text()
    assert '#include "aegis_pins.h"' in firmware
    for pin in ("AEGIS_X_LIMIT_PIN", "AEGIS_Y_LIMIT_PIN", "AEGIS_Z_LIMIT_PIN"):
        assert pin in firmware
    assert "limitsClearForDirection" in firmware


def test_controller_declares_coordinate_serial_commands():
    firmware = (ROOT / "firmware/aegis_controller/main.cpp").read_text()
    for command in ("HOME", "MOVE", "PLASMA", "STOP", "STATUS"):
        assert f'"{command}"' in firmware
    assert "stepsPerMm" in firmware
    assert "machineToSteps" in firmware


def test_controller_declares_plasma_pwm_safety_defaults():
    header = (ROOT / "firmware/lib/aegis_pins.h").read_text()
    firmware = (ROOT / "firmware/aegis_controller/main.cpp").read_text()
    assert "AEGIS_PLASMA_PWM_PIN" in header
    assert "disablePlasma();" in firmware
    assert "analogWrite(AEGIS_PLASMA_PWM_PIN, 0)" in firmware
    assert "PLASMA <intensity_0_to_1> <dwell_ms>" in (ROOT / "docs/architecture/wound_to_coordinate_pipeline.md").read_text()
