"""Tests for PopupNumberParser."""

import pytest
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from popup_number_parser import PopupNumberParser, PopupNumber
from typing import List, Dict


class MockOCREngine:
    """Mock OCR engine with preset results."""

    def __init__(self, results=None):
        self._results = results or []

    def recognize(self, image) -> List[Dict]:
        return self._results


def _mock_image(width=800, height=600):
    """Create a mock PIL Image object."""
    img = MagicMock()
    img.size = (width, height)
    img.crop.return_value = img
    return img


def _make_result(text, confidence, bbox):
    """Helper to construct OCR result dict."""
    return {
        "text": text,
        "confidence": confidence,
        "bbox": bbox,
    }


# ------------------------------------------------------------------ #
#  _extract_number
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_extract_number_positive():
    assert PopupNumberParser._extract_number("1500") == 1500


@pytest.mark.unit
def test_extract_number_negative():
    assert PopupNumberParser._extract_number("-1500") == -1500


@pytest.mark.unit
def test_extract_number_with_plus():
    assert PopupNumberParser._extract_number("+500") == 500


@pytest.mark.unit
def test_extract_number_mixed_text():
    assert PopupNumberParser._extract_number("受到1500点伤害") is None


@pytest.mark.unit
def test_extract_number_zero():
    assert PopupNumberParser._extract_number("0") is None


@pytest.mark.unit
def test_extract_number_too_large():
    assert PopupNumberParser._extract_number("100000") is None


# ------------------------------------------------------------------ #
#  _parse_unit_region
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_parse_unit_region_damage():
    """Mock OCR returns '-1500', parser finds it for unit '剑侠客'."""
    bbox = [[10, 10], [60, 10], [60, 30], [10, 30]]
    results = [_make_result("-1500", 0.85, bbox)]
    engine = MockOCREngine(results)
    parser = PopupNumberParser(engine)

    img = _mock_image()
    unit = {"name": "剑侠客", "position": (200, 200)}
    numbers = parser._parse_unit_region(img, unit)

    assert len(numbers) == 1
    assert numbers[0].value == -1500
    assert numbers[0].unit_name == "剑侠客"
    assert numbers[0].raw_text == "-1500"
    assert numbers[0].confidence == pytest.approx(0.85)


@pytest.mark.unit
def test_parse_unit_region_heal():
    """Mock OCR returns '800', parser finds it."""
    bbox = [[5, 5], [50, 5], [50, 25], [5, 25]]
    results = [_make_result("800", 0.92, bbox)]
    engine = MockOCREngine(results)
    parser = PopupNumberParser(engine)

    img = _mock_image()
    unit = {"name": "龙太子", "position": (300, 300)}
    numbers = parser._parse_unit_region(img, unit)

    assert len(numbers) == 1
    assert numbers[0].value == 800
    assert numbers[0].unit_name == "龙太子"


@pytest.mark.unit
def test_parse_no_numbers():
    """Empty OCR results returns empty list."""
    engine = MockOCREngine([])
    parser = PopupNumberParser(engine)

    img = _mock_image()
    unit = {"name": "飞燕女", "position": (400, 400)}
    numbers = parser._parse_unit_region(img, unit)

    assert numbers == []


# ------------------------------------------------------------------ #
#  parse (multiple units)
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_parse_multiple_units():
    """Two units, OCR returns numbers for each."""
    bbox1 = [[10, 10], [60, 10], [60, 30], [10, 30]]
    bbox2 = [[5, 5], [50, 5], [50, 25], [5, 25]]

    def recognize_side_effect(image):
        # Return different results based on which unit region is cropped.
        # We distinguish by checking the crop call arguments via the mock image.
        # Since img.crop.return_value = img, we can't easily distinguish here.
        # Instead, return both results; each unit region will see all results.
        return [
            _make_result("-1500", 0.85, bbox1),
            _make_result("800", 0.90, bbox2),
        ]

    engine = MockOCREngine()
    engine.recognize = recognize_side_effect
    parser = PopupNumberParser(engine)
    parser.set_unit_positions([
        {"name": "剑侠客", "position": (200, 200)},
        {"name": "龙太子", "position": (400, 400)},
    ])

    img = _mock_image()
    numbers = parser.parse(img)

    assert len(numbers) == 4  # Each unit sees both OCR results
    unit_names = [n.unit_name for n in numbers]
    assert unit_names.count("剑侠客") == 2
    assert unit_names.count("龙太子") == 2
