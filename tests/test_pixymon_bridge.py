from host.aegis_control.pixymon_bridge import PixyMonCaptureError, pixymon_window_bounds


def test_pixymon_window_bounds_parses_osascript_output(monkeypatch):
    class Result:
        stdout = "10,20,640,480\n"

    monkeypatch.setattr("host.aegis_control.pixymon_bridge._run", lambda command: Result())

    assert pixymon_window_bounds("PixyMon") == (10, 20, 640, 480)


def test_pixymon_window_bounds_rejects_invalid_size(monkeypatch):
    class Result:
        stdout = "10,20,0,480\n"

    monkeypatch.setattr("host.aegis_control.pixymon_bridge._run", lambda command: Result())

    try:
        pixymon_window_bounds("PixyMon")
    except PixyMonCaptureError as exc:
        assert "invalid PixyMon window bounds" in str(exc)
    else:
        raise AssertionError("expected PixyMonCaptureError")
