import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from screenshot import ScreenshotEngine, Region


class TestScreenshotEngine:
    def test_region_creation(self):
        region = Region(x=0, y=0, width=1920, height=1080)
        assert region.width == 1920
        assert region.height == 1080

    def test_capture_without_region_raises(self):
        engine = ScreenshotEngine()
        with pytest.raises(ValueError, match="Monitor region not set"):
            engine.capture()

    @patch("screenshot.mss")
    def test_capture_with_region(self, mock_mss_module):
        mock_mss_instance = Mock()

        class FakeScreenshot:
            def __init__(self):
                self.rgb = bytes([255, 0, 0] * 100)
                self.size = (10, 10)

        mock_mss_instance.grab.return_value = FakeScreenshot()
        mock_mss_module.mss.return_value.__enter__ = lambda self: mock_mss_instance
        mock_mss_module.mss.return_value.__exit__ = lambda self, *args: False

        mock_img = Mock()
        mock_img.width = 10
        mock_img.height = 10
        mock_image_mod = MagicMock()
        mock_image_mod.frombytes.return_value = mock_img

        fake_pil = MagicMock()
        fake_pil.Image = mock_image_mod
        with patch.dict(sys.modules, {"PIL": fake_pil}):
            engine = ScreenshotEngine()
            engine.set_region(Region(x=0, y=0, width=10, height=10))

            img = engine.capture()
            assert img is not None
            assert img.width == 10
            assert img.height == 10
