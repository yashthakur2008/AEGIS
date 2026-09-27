import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from host.aegis_control.pixy2_direct import DirectPixySource, OptionalPixy2Backend, Pixy2DirectError
from host.aegis_control.pixymon_bridge import PixyDashboardHandler, PixyFeedError, PixyMonFrameSource, make_source


class FakeBlock:
    m_signature = 2
    m_x = 123
    m_y = 45
    m_width = 20
    m_height = 10
    m_age = 7


class FakeCCC:
    def getBlocks(self):
        return 1

    blocks = [FakeBlock()]


class FakePixy:
    def __init__(self):
        self.ccc = FakeCCC()
        self.initialized = False

    def init(self):
        self.initialized = True


class FakeModule:
    @staticmethod
    def Pixy2():
        return FakePixy()


def test_optional_pixy2_backend_normalizes_ccc_blocks():
    backend = OptionalPixy2Backend(module=FakeModule)

    blocks = backend.get_blocks()

    assert len(blocks) == 1
    assert blocks[0].signature == 2
    assert blocks[0].centroid_x_px == 123
    assert blocks[0].centroid_y_px == 45
    assert blocks[0].area == 200
    assert blocks[0].age == 7


def test_optional_pixy2_backend_reports_missing_frame_api():
    backend = OptionalPixy2Backend(module=FakeModule)

    try:
        backend.get_frame_jpeg()
    except Pixy2DirectError as exc:
        assert "Use /pixy-blocks.json" in str(exc)
    else:
        raise AssertionError("expected Pixy2DirectError")


def test_direct_pixy_source_blocks_json_uses_backend_blocks():
    class Backend:
        backend_name = "fake"

        def get_blocks(self):
            return OptionalPixy2Backend(module=FakeModule).get_blocks()

        def get_frame_jpeg(self):
            return b"\xff\xd8fakejpeg"

    source = DirectPixySource(backend=Backend())

    payload = source.blocks_json()

    assert '"mode": "direct-pixy2-usb"' in payload
    assert '"signature": 2' in payload
    assert '"centroid_x_px": 123' in payload


def test_pixymon_source_blocks_endpoint_rejects_screen_capture_mode():
    source = PixyMonFrameSource()

    try:
        source.capture_blocks()
    except PixyFeedError as exc:
        assert "does not expose numeric Pixy blocks" in str(exc)
    else:
        raise AssertionError("expected PixyFeedError")
