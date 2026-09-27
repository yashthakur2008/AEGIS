from __future__ import annotations

import importlib
import io
import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol


class Pixy2DirectError(RuntimeError):
    """Raised when direct Pixy2 USB access is unavailable or fails."""


@dataclass(frozen=True)
class PixyBlock:
    signature: int
    x: int
    y: int
    width: int
    height: int
    angle: int | None = None
    index: int | None = None
    age: int | None = None

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def centroid_x_px(self) -> int:
        return self.x

    @property
    def centroid_y_px(self) -> int:
        return self.y

    def to_dict(self) -> dict[str, int | None]:
        payload = asdict(self)
        payload["area"] = self.area
        payload["centroid_x_px"] = self.centroid_x_px
        payload["centroid_y_px"] = self.centroid_y_px
        return payload


class DirectPixyBackend(Protocol):
    backend_name: str

    def get_blocks(self) -> list[PixyBlock]: ...
    def get_frame_jpeg(self) -> bytes: ...


class OptionalPixy2Backend:
    """Best-effort adapter around optional Pixy2 Python/libpixyusb2 bindings.

    Pixy2 is not a UVC webcam. This class intentionally avoids pretending it can
    be opened with OpenCV VideoCapture. It tries common Python binding names and
    normalizes color-connected-component blocks into PixyBlock objects. Raw frame
    capture is supported only if the installed binding exposes a usable frame API.
    """

    backend_name = "optional-pixy2-python-binding"
    candidate_modules = ("pixy2", "pixy", "libpixyusb2")

    def __init__(self, module: Any | None = None) -> None:
        self.module = module or self._import_first_available()
        self.pixy = self._open_pixy(self.module)

    @classmethod
    def _import_first_available(cls) -> Any:
        errors: list[str] = []
        for name in cls.candidate_modules:
            try:
                return importlib.import_module(name)
            except ImportError as exc:
                errors.append(f"{name}: {exc}")
        raise Pixy2DirectError(
            "No Pixy2 direct USB Python binding is installed. Install/build Charmed Labs libpixyusb2 "
            "or a Pixy2 Python API, then retry --source direct. Tried: " + "; ".join(errors)
        )

    @staticmethod
    def _open_pixy(module: Any) -> Any:
        if hasattr(module, "Pixy2"):
            pixy = module.Pixy2()
            if hasattr(pixy, "init"):
                pixy.init()
            return pixy
        if hasattr(module, "init"):
            module.init()
            return module
        raise Pixy2DirectError(
            f"Pixy2 binding {getattr(module, '__name__', module)!r} does not expose Pixy2() or init()"
        )

    def get_blocks(self) -> list[PixyBlock]:
        source = self._get_block_source()
        raw_blocks = self._read_raw_blocks(source)
        return [self._normalize_block(block) for block in raw_blocks]

    def _get_block_source(self) -> Any:
        if hasattr(self.pixy, "ccc"):
            return self.pixy.ccc
        if hasattr(self.pixy, "get_blocks") or hasattr(self.pixy, "getBlocks"):
            return self.pixy
        raise Pixy2DirectError("Pixy2 binding does not expose CCC block access")

    @staticmethod
    def _read_raw_blocks(source: Any) -> list[Any]:
        if hasattr(source, "get_blocks"):
            result = source.get_blocks()
        elif hasattr(source, "getBlocks"):
            result = source.getBlocks()
        else:
            raise Pixy2DirectError("Pixy2 block source does not expose get_blocks/getBlocks")

        if isinstance(result, tuple) and len(result) == 2:
            _, blocks = result
            return list(blocks)
        if result is None and hasattr(source, "blocks"):
            count = int(getattr(source, "numBlocks", len(source.blocks)))
            return list(source.blocks[:count])
        if isinstance(result, int) and hasattr(source, "blocks"):
            return list(source.blocks[:result])
        return list(result or [])

    @staticmethod
    def _attr(block: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            if hasattr(block, name):
                return getattr(block, name)
            if isinstance(block, dict) and name in block:
                return block[name]
        return default

    @classmethod
    def _normalize_block(cls, block: Any) -> PixyBlock:
        return PixyBlock(
            signature=int(cls._attr(block, "signature", "m_signature", "sig", default=0)),
            x=int(cls._attr(block, "x", "m_x", default=0)),
            y=int(cls._attr(block, "y", "m_y", default=0)),
            width=int(cls._attr(block, "width", "m_width", "w", default=0)),
            height=int(cls._attr(block, "height", "m_height", "h", default=0)),
            angle=cls._optional_int(cls._attr(block, "angle", "m_angle")),
            index=cls._optional_int(cls._attr(block, "index", "m_index")),
            age=cls._optional_int(cls._attr(block, "age", "m_age")),
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return None if value is None else int(value)

    def get_frame_jpeg(self) -> bytes:
        frame = self._read_frame()
        if isinstance(frame, bytes):
            if frame.startswith(b"\xff\xd8"):
                return frame
            raise Pixy2DirectError("Pixy2 frame API returned bytes, but not JPEG bytes")
        return encode_frame_to_jpeg(frame)

    def _read_frame(self) -> Any:
        for name in ("get_frame", "getFrame", "get_rgb_frame", "getRawFrame"):
            if hasattr(self.pixy, name):
                return getattr(self.pixy, name)()
        raise Pixy2DirectError(
            "Installed Pixy2 binding exposes blocks but not raw frame capture. "
            "Use /pixy-blocks.json for calibration, or add a libpixyusb2 raw-frame binding."
        )


def encode_frame_to_jpeg(frame: Any) -> bytes:
    """Encode a frame-like object as JPEG using Pillow if available."""
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise Pixy2DirectError("Raw frame encoding requires Pillow: python -m pip install pillow") from exc

    if isinstance(frame, Image.Image):
        image = frame
    else:
        try:
            image = Image.fromarray(frame)
        except Exception as exc:  # pragma: no cover - depends on optional frame type
            raise Pixy2DirectError(f"Cannot encode Pixy2 frame as JPEG: {exc}") from exc
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


class DirectPixySource:
    name = "Direct Pixy2 USB"
    mode = "direct-pixy2-usb"

    def __init__(self, backend: DirectPixyBackend | None = None) -> None:
        self.backend = backend or OptionalPixy2Backend()

    def capture_frame(self) -> bytes:
        return self.backend.get_frame_jpeg()

    def capture_blocks(self) -> list[PixyBlock]:
        return self.backend.get_blocks()

    def blocks_json(self) -> str:
        return json.dumps({"ok": True, "source": self.name, "mode": self.mode, "blocks": [b.to_dict() for b in self.capture_blocks()]})
