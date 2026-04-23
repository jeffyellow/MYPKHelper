"""使用 mss 的屏幕截图引擎。"""

from dataclasses import dataclass
from typing import Optional
import mss


@dataclass
class Region:
    x: int
    y: int
    width: int
    height: int

    def to_mss_dict(self) -> dict:
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height,
        }


class ScreenshotEngine:
    def __init__(self):
        self._region: Optional[Region] = None
        self._last_capture: Optional[object] = None

    def set_region(self, region: Region) -> None:
        self._region = region

    def get_region(self) -> Optional[Region]:
        return self._region

    def capture(self):
        if self._region is None:
            raise ValueError("Monitor region not set")

        try:
            from PIL import Image
            with mss.mss() as sct:
                screenshot = sct.grab(self._region.to_mss_dict())
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                self._last_capture = img
                return img
        except Exception as exc:
            msg = str(exc)
            if "DISPLAY" in msg or "display" in msg.lower():
                raise RuntimeError("No DISPLAY environment available") from exc
            raise
