"""Popup damage/heal number parser for combat units."""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

from ocr_engine import OCREngine


@dataclass
class PopupNumber:
    value: int
    unit_name: str
    raw_text: str
    confidence: float
    position: Tuple[int, int]


class PopupNumberParser:
    """Recognizes popup numbers near characters during combat."""

    def __init__(self, ocr_engine: OCREngine):
        self._ocr_engine = ocr_engine
        self._units: List[Dict] = []

    def set_unit_positions(self, units: List[Dict]) -> None:
        """Set unit positions: [{"name": str, "position": (x, y)}, ...]."""
        self._units = units

    def parse(self, image) -> List[PopupNumber]:
        """Parse popup numbers for all units."""
        results: List[PopupNumber] = []
        for unit in self._units:
            results.extend(self._parse_unit_region(image, unit))
        return results

    def _parse_unit_region(self, image, unit: Dict) -> List[PopupNumber]:
        """Crop a search box around the unit and run OCR."""
        cx, cy = unit["position"]
        x1 = max(0, cx - 100)
        y1 = max(0, cy - 120)
        x2 = cx + 100
        y2 = cy + 40

        cropped = image.crop((x1, y1, x2, y2))
        ocr_results = self._ocr_engine.recognize(cropped)

        numbers: List[PopupNumber] = []
        for res in ocr_results:
            text = res["text"]
            confidence = float(res["confidence"])
            bbox = res["bbox"]

            if confidence < 0.6:
                continue

            value = self._extract_number(text)
            if value is None:
                continue
            if value == 0:
                continue
            if abs(value) > 99999:
                continue

            abs_x = x1 + self._bbox_center_x(bbox)
            abs_y = y1 + self._bbox_center_y(bbox)
            numbers.append(
                PopupNumber(
                    value=value,
                    unit_name=unit["name"],
                    raw_text=text,
                    confidence=confidence,
                    position=(abs_x, abs_y),
                )
            )

        return numbers

    @staticmethod
    def _extract_number(text: str) -> Optional[int]:
        """Extract a signed integer from text. Only pure numbers are accepted.

        Rejects zero and values whose absolute magnitude exceeds 99999.
        """
        stripped = text.strip()
        if not re.fullmatch(r"[+-]?\d+", stripped):
            return None
        try:
            value = int(stripped)
        except ValueError:
            return None
        if value == 0 or abs(value) > 99999:
            return None
        return value

    @staticmethod
    def _bbox_center_x(bbox: List[List[int]]) -> int:
        """Calculate center x from bbox [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]."""
        xs = [point[0] for point in bbox]
        return sum(xs) // len(xs)

    @staticmethod
    def _bbox_center_y(bbox: List[List[int]]) -> int:
        """Calculate center y from bbox."""
        ys = [point[1] for point in bbox]
        return sum(ys) // len(ys)
