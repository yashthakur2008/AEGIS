import pytest

from host.aegis_control.pixymon_bridge import (
    DirectPixyFrameSource,
    PixyFeedError,
    PixyMonCaptureError,
    PixyMonFrameSource,
    make_source,
    pixymon_window_bounds,
)


def test_pixymon_window_bounds_parses_osascript_output(monkeypatch):
    class Result:
        stdout = "10,20,640,480\n"

    monkeypatch.setattr("host.aegis_control.pixymon_bridge._run", lambda command: Result())

    assert pixymon_window_bounds("PixyMon") == (10, 20, 640, 480)


def test_pixymon_window_bounds_rejects_invalid_size(monkeypatch):
    class Result:
        stdout = "10,20,0,480\n"

    monkeypatch.setattr("host.aegis_control.pixymon_bridge._run", lambda command: Result())

    with pytest.raises(PixyMonCaptureError, match="invalid PixyMon window bounds"):
        pixymon_window_bounds("PixyMon")


def test_make_source_selects_pixymon_source():
    source = make_source("pixymon", "PixyMon")

    assert isinstance(source, PixyMonFrameSource)
    assert source.mode == "pixymon-window"


def test_direct_pixy_source_is_explicitly_pending():
    source = DirectPixyFrameSource()

    with pytest.raises(PixyFeedError, match="direct Pixy2 feed is not implemented yet"):
        source.capture_frame()
