"""Tests for BattleOCRParser."""

import pytest
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ocr_parser import BattleOCRParser, ParsedUnit, ParsedAction
from typing import List, Dict


class MockOCREngine:
    """模拟 OCR 引擎，可预设返回结果。"""

    def __init__(self, results=None):
        self._results = results or []

    def recognize(self, image) -> List[Dict]:
        return self._results


def _mock_image(width=800, height=600):
    """创建模拟 PIL Image 对象。"""
    img = MagicMock()
    img.size = (width, height)
    img.crop.return_value = img
    return img


def _make_result(text, confidence, bbox):
    """辅助构造 OCR 结果字典。"""
    return {
        "text": text,
        "confidence": confidence,
        "bbox": bbox,
    }


# ------------------------------------------------------------------ #
#  _looks_like_name
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_looks_like_name_valid():
    assert BattleOCRParser._looks_like_name("剑侠客") is True
    assert BattleOCRParser._looks_like_name("龙太子") is True


@pytest.mark.unit
def test_looks_like_name_too_short():
    assert BattleOCRParser._looks_like_name("a") is False


@pytest.mark.unit
def test_looks_like_name_too_long():
    assert BattleOCRParser._looks_like_name("这是一个超长名字超过了限制") is False


@pytest.mark.unit
def test_looks_like_name_low_chinese_ratio():
    assert BattleOCRParser._looks_like_name("abc123") is False


# ------------------------------------------------------------------ #
#  parse_first_frame
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_parse_first_frame_extracts_units():
    """首场识别应正确过滤左侧对手区域的名字。"""
    bbox_left = [[10, 100], [80, 100], [80, 130], [10, 130]]
    bbox_right = [[600, 100], [670, 100], [670, 130], [600, 130]]
    results = [
        _make_result("剑侠客", 0.95, bbox_left),
        _make_result("龙太子", 0.92, bbox_right),  # 右侧，应被过滤
    ]
    engine = MockOCREngine(results)
    parser = BattleOCRParser(engine, opponent_region_ratio=0.5)

    img = _mock_image(800, 600)
    units = parser.parse_first_frame(img)

    assert len(units) == 1
    assert units[0].name == "剑侠客"
    assert units[0].confidence == pytest.approx(0.95)


@pytest.mark.unit
def test_parse_first_frame_faction_extraction():
    """应在名字附近识别出门派。"""
    bbox_name = [[10, 100], [80, 100], [80, 130], [10, 130]]
    bbox_faction = [[10, 50], [50, 50], [50, 68], [10, 68]]  # 上方，中心 y=59 刚好在 name_y_range 外，但仍在 search_radius 内
    results = [
        _make_result("剑侠客", 0.95, bbox_name),
        _make_result("大唐", 0.90, bbox_faction),
    ]
    engine = MockOCREngine(results)
    parser = BattleOCRParser(engine, opponent_region_ratio=0.5)

    img = _mock_image(800, 600)
    units = parser.parse_first_frame(img)

    assert len(units) == 1
    assert units[0].faction == "大唐"


@pytest.mark.unit
def test_parse_first_frame_limits_to_five():
    """候选超过 5 个时应按置信度取前 5 并按 y 排序。"""
    results = []
    for i in range(7):
        y = 50 + i * 50
        bbox = [[10, y], [80, y], [80, y + 30], [10, y + 30]]
        results.append(_make_result(f"角色{i}", 0.5 + i * 0.05, bbox))
    engine = MockOCREngine(results)
    parser = BattleOCRParser(engine, opponent_region_ratio=0.5)

    img = _mock_image(800, 600)
    units = parser.parse_first_frame(img)

    assert len(units) == 5
    # 按 y 坐标排序
    ys = [u.position[1] for u in units]
    assert ys == sorted(ys)


# ------------------------------------------------------------------ #
#  parse_round_frame
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_parse_round_frame_action_text():
    """应识别下排操作文字。"""
    bbox_action = [[10, 500], [200, 500], [200, 530], [10, 530]]
    results = [
        _make_result("受到 1234 点伤害", 0.90, bbox_action),
    ]
    engine = MockOCREngine(results)
    parser = BattleOCRParser(engine, action_y_range=(0.75, 0.95))

    img = _mock_image(800, 600)
    actions = parser.parse_round_frame(img)

    assert len(actions) == 1
    assert actions[0].action_text == "受到 1234 点伤害"
    assert actions[0].hp_change == -1234


@pytest.mark.unit
def test_parse_round_frame_with_cached_units():
    """有角色位置缓存时应尝试在头顶识别血量。"""
    engine = MockOCREngine([])
    parser = BattleOCRParser(engine)

    # 预设角色位置（头顶区域会被裁剪做 OCR）
    parser.unit_positions = [
        ParsedUnit(
            name="剑侠客",
            faction="大唐",
            position=(100, 200),
            name_region=MagicMock(),
            confidence=0.95,
        )
    ]

    img = _mock_image(800, 600)
    actions = parser.parse_round_frame(img)

    # 没有模拟血量数字 OCR 结果，所以不会有血量动作
    assert all(a.action_text != "气血 1234" for a in actions)


# ------------------------------------------------------------------ #
#  _extract_hp_change
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_extract_hp_change_damage():
    parser = BattleOCRParser(MockOCREngine())
    assert parser._extract_hp_change("受到 1500 点伤害") == -1500
    assert parser._extract_hp_change("攻击造成 800 点伤害") == -800


@pytest.mark.unit
def test_extract_hp_change_heal():
    parser = BattleOCRParser(MockOCREngine())
    assert parser._extract_hp_change("回复 500 点气血") == 500
    assert parser._extract_hp_change("治疗 1200 点") == 1200


@pytest.mark.unit
def test_extract_hp_change_no_number():
    parser = BattleOCRParser(MockOCREngine())
    assert parser._extract_hp_change("使用了技能") is None


# ------------------------------------------------------------------ #
#  track_hp_changes
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_track_hp_changes_detects_difference():
    parser = BattleOCRParser(MockOCREngine())
    prev = {"A": 1000, "B": 2000}
    curr = {"A": 800, "B": 2000}
    changes = parser.track_hp_changes(prev, curr)

    assert len(changes) == 1
    assert changes[0]["unit_name"] == "A"
    assert changes[0]["prev_hp"] == 1000
    assert changes[0]["curr_hp"] == 800
    assert changes[0]["change"] == -200


@pytest.mark.unit
def test_track_hp_changes_ignores_same():
    parser = BattleOCRParser(MockOCREngine())
    prev = {"A": 1000}
    curr = {"A": 1000}
    changes = parser.track_hp_changes(prev, curr)
    assert changes == []


@pytest.mark.unit
def test_track_hp_changes_new_unit():
    parser = BattleOCRParser(MockOCREngine())
    prev = {"A": 1000}
    curr = {"A": 1000, "B": 500}
    changes = parser.track_hp_changes(prev, curr)
    assert changes == []


def test_parse_popup_numbers():
    bbox = [[10, 10], [50, 10], [50, 30], [10, 30]]
    engine = MockOCREngine([_make_result("-1500", 0.95, bbox)])
    parser = BattleOCRParser(engine)
    parser.unit_positions = [
        ParsedUnit(name="剑侠客", faction="大唐", position=(100, 200), name_region=MagicMock(), confidence=0.95)
    ]
    img = _mock_image(800, 600)
    results = parser.parse_popup_numbers(img)
    assert len(results) == 1
    assert results[0]["value"] == -1500


def test_parse_actions():
    engine = MockOCREngine([])
    parser = BattleOCRParser(engine)
    parser.unit_positions = [
        ParsedUnit(name="剑侠客", faction="大唐", position=(100, 200), name_region=MagicMock(), confidence=0.95)
    ]
    ocr_results = [
        {"text": "第 3 回合", "confidence": 0.9},
        {"text": "剑侠客 使用了晶清诀", "confidence": 0.9},
    ]
    actions = parser.parse_actions(ocr_results)
    assert len(actions) == 2
    assert actions[0]["action_type"] == "round"
    assert actions[1]["action_type"] == "skill"
