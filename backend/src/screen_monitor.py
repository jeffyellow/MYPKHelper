"""屏幕监控器：在战斗期间定时截图并通过 OCR 识别游戏状态。"""

import asyncio
import logging
from typing import Optional, Callable, List, Dict

from screenshot import ScreenshotEngine, Region
from ocr_engine import OCREngine


logger = logging.getLogger(__name__)


class ScreenMonitor:
    """管理截图轮询和 OCR 识别流程。"""

    def __init__(
        self,
        screenshot_engine: ScreenshotEngine,
        ocr_engine: OCREngine,
        interval: float = 5.0,
    ):
        self.screenshot = screenshot_engine
        self.ocr = ocr_engine
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._callbacks: List[Callable[[List[Dict]], None]] = []

    def add_callback(self, callback: Callable[[List[Dict]], None]) -> None:
        """添加 OCR 结果回调。"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[List[Dict]], None]) -> None:
        """移除 OCR 结果回调。"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def set_interval(self, interval: float) -> None:
        """动态调整截图间隔（秒）。"""
        self.interval = interval

    async def start(self) -> None:
        """启动截图轮询。"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Screen monitor started")

    async def stop(self) -> None:
        """停止截图轮询。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Screen monitor stopped")

    async def _loop(self) -> None:
        """主循环：定时截图并 OCR。"""
        while self._running:
            try:
                await self._capture_and_recognize()
            except Exception as exc:
                msg = str(exc)
                if "DISPLAY" in msg or "display" in msg:
                    logger.warning("No display available, skipping capture")
                else:
                    logger.exception("Capture/OCR error")
            await asyncio.sleep(self.interval)

    async def _capture_and_recognize(self) -> None:
        """截图一次并识别。"""
        if self.screenshot.get_region() is None:
            logger.warning("Monitor region not set, skipping capture")
            return

        image = self.screenshot.capture()
        results = self.ocr.recognize(image)

        for callback in self._callbacks:
            try:
                callback(results)
            except Exception:
                logger.exception("Callback error")
