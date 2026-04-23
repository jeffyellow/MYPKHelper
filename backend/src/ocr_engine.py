"""基于 PaddleOCR 的 OCR 引擎封装。"""

from typing import Optional, List, Dict, Tuple


class OCREngine:
    """首次使用时延迟加载 PaddleOCR，避免启动过慢。"""

    def __init__(self):
        self._ocr: Optional[object] = None

    def _ensure_loaded(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
            )

    def recognize(self, image) -> List[Dict]:
        """
        识别图片中的文字。
        返回字典列表：{text: str, confidence: float, bbox: list}
        """
        import numpy as np
        self._ensure_loaded()
        img_array = np.array(image)
        result = self._ocr.ocr(img_array, cls=True)

        texts = []
        if result and result[0]:
            for line in result[0]:
                if line is None:
                    continue
                bbox, (text, confidence) = line
                texts.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": bbox,
                })
        return texts

    def recognize_region(
        self, image, region: Tuple[int, int, int, int]
    ) -> List[Dict]:
        """在裁剪区域中识别文字：(x, y, width, height)。"""
        x, y, w, h = region
        cropped = image.crop((x, y, x + w, y + h))
        return self.recognize(cropped)
