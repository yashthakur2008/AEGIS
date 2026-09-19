from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    for command in ("HOME", "MOVE", "STOP", "STATUS"):
        assert f'"{command}"' in firmware
    assert "stepsPerMm" in firmware
    assert "machineToSteps" in firmware
