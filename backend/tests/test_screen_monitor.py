import pytest
from unittest.mock import Mock, patch

from screen_monitor import ScreenMonitor
from screenshot import ScreenshotEngine, Region
from ocr_engine import OCREngine


class TestScreenMonitor:
    def test_start_stop(self):
        screenshot = ScreenshotEngine()
        ocr = OCREngine()
        monitor = ScreenMonitor(screenshot, ocr, interval=1.0)

        assert monitor._running is False
        assert monitor._task is None

    def test_add_remove_callback(self):
        screenshot = ScreenshotEngine()
        ocr = OCREngine()
        monitor = ScreenMonitor(screenshot, ocr)

        def cb(results):
            pass

        monitor.add_callback(cb)
        assert cb in monitor._callbacks

        monitor.remove_callback(cb)
        assert cb not in monitor._callbacks

    @pytest.mark.asyncio
    async def test_capture_and_recognize_no_region(self):
        """未设置区域时应跳过截图。"""
        screenshot = ScreenshotEngine()
        ocr = OCREngine()
        monitor = ScreenMonitor(screenshot, ocr)

        # 不应抛出异常
        await monitor._capture_and_recognize()

    @pytest.mark.asyncio
    async def test_capture_and_recognize_with_region(self):
        """设置区域后应执行截图和 OCR。"""
        screenshot = ScreenshotEngine()
        region = Region(x=0, y=0, width=10, height=10)
        screenshot.set_region(region)

        ocr = OCREngine()
        monitor = ScreenMonitor(screenshot, ocr)

        called = False

        def cb(results):
            nonlocal called
            called = True

        monitor.add_callback(cb)

        with patch.object(screenshot, "capture") as mock_capture:
            mock_img = Mock()
            mock_capture.return_value = mock_img
            with patch.object(ocr, "recognize") as mock_recognize:
                mock_recognize.return_value = [
                    {"text": "1234", "confidence": 0.95, "bbox": []}
                ]
                await monitor._capture_and_recognize()

        assert called is True
        mock_capture.assert_called_once()
        mock_recognize.assert_called_once_with(mock_img)
