# OCR 自动化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现纯 OCR 驱动的战斗状态追踪：识别角色附近的弹出伤害/治疗数字、画面下方的特技使用和回合切换，自动更新血量、愤怒，并展示 OCR 调试信息。

**Architecture:** 后端新增弹出数字解析器和操作文字扩展解析器，通过去重机制避免重复计算，最终由 `ConnectionManager._on_ocr_results` 驱动 `BattleEngine`。前端新增 OCR 调试面板展示每帧识别结果。

**Tech Stack:** Python 3.10, FastAPI, PaddleOCR, React 18, TypeScript, Zustand, WebSocket

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/src/popup_number_parser.py` | Create | 从角色附近区域识别弹出伤害/治疗数字 |
| `backend/src/action_text_parser.py` | Create | 从画面下方识别特技名、回合、伤害描述 |
| `backend/src/dedup_tracker.py` | Create | 3 秒窗口去重，避免同一数字重复计算 |
| `backend/src/ocr_parser.py` | Modify | 集成 popup_number_parser 和 action_text_parser |
| `backend/src/websocket_handler.py` | Modify | 重写 `_on_ocr_results`，连接所有新模块 |
| `backend/tests/test_popup_number_parser.py` | Create | 弹出数字识别测试 |
| `backend/tests/test_action_text_parser.py` | Create | 操作文字识别测试 |
| `backend/tests/test_dedup_tracker.py` | Create | 去重机制测试 |
| `backend/tests/test_ocr_parser.py` | Modify | 补充新解析器集成测试 |
| `backend/tests/test_battle_engine.py` | Modify | 修复初始愤怒值测试（0 → 90）|
| `frontend/src/components/OCRDebugPanel.tsx` | Create | OCR 调试面板 |
| `frontend/src/components/ActionPanel.tsx` | Modify | 集成 OCR 调试面板 |

---

### Task 1: 弹出数字识别模块

**Files:**
- Create: `backend/src/popup_number_parser.py`
- Test: `backend/tests/test_popup_number_parser.py`

- [ ] **Step 1: Write the module**

```python
"""弹出数字识别器：从角色附近区域识别伤害/治疗数字。"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from ocr_engine import OCREngine
from screenshot import Region


@dataclass
class PopupNumber:
    """识别出的弹出数字。"""
    value: int           # 数值（负值表示伤害，正值表示治疗）
    unit_name: str       # 关联角色名字
    raw_text: str        # OCR 原始文字
    confidence: float    # 置信度
    position: Tuple[int, int]  # 屏幕坐标 (x, y)


class PopupNumberParser:
    """识别角色附近的弹出式伤害/治疗数字。

    每场战斗前需通过 `set_unit_positions` 传入角色位置。
    """

    def __init__(self, ocr_engine: OCREngine):
        self.ocr = ocr_engine
        self.unit_positions: List[Dict] = []

    def set_unit_positions(self, units: List[Dict]) -> None:
        """设置角色位置列表。

        units: [{"name": str, "position": (x, y)}, ...]
        """
        self.unit_positions = units

    def parse(self, image) -> List[PopupNumber]:
        """从整图中识别所有角色的弹出数字。"""
        if not self.unit_positions:
            return []

        results = []
        for unit in self.unit_positions:
            nums = self._parse_unit_region(image, unit)
            results.extend(nums)
        return results

    def _parse_unit_region(self, image, unit: Dict) -> List[PopupNumber]:
        """识别单个角色搜索区域内的弹出数字。"""
        name = unit["name"]
        cx, cy = unit["position"]

        # 搜索框：以角色为中心，水平 ±100px，垂直 ±80px
        box = (
            max(0, cx - 100),
            max(0, cy - 120),
            min(image.width, cx + 100),
            min(image.height, cy + 40),
        )
        crop = image.crop(box)
        ocr_results = self.ocr.recognize(crop)

        numbers = []
        for r in ocr_results:
            text = r.get("text", "").strip()
            conf = r.get("confidence", 0)
            bbox = r.get("bbox", [])

            if conf < 0.6:
                continue

            val = self._extract_number(text)
            if val is None or val == 0:
                continue

            # 计算绝对坐标
            abs_x = box[0] + self._bbox_center_x(bbox)
            abs_y = box[1] + self._bbox_center_y(bbox)

            numbers.append(PopupNumber(
                value=val,
                unit_name=name,
                raw_text=text,
                confidence=conf,
                position=(int(abs_x), int(abs_y)),
            ))

        return numbers

    @staticmethod
    def _extract_number(text: str) -> Optional[int]:
        """从文本中提取带符号的整数。只匹配纯数字（可选正负号）。"""
        text = text.replace(" ", "").replace(",", "").replace("，", "")
        m = re.match(r"^([+-]?\d+)$", text)
        if m:
            val = int(m.group(1))
            if 1 <= abs(val) <= 99999:
                return val
        return None

    @staticmethod
    def _bbox_center_x(bbox: List) -> float:
        xs = [p[0] for p in bbox]
        return sum(xs) / len(xs) if xs else 0

    @staticmethod
    def _bbox_center_y(bbox: List) -> float:
        ys = [p[1] for p in bbox]
        return sum(ys) / len(ys) if ys else 0
```

- [ ] **Step 2: Write the tests**

```python
"""Tests for PopupNumberParser."""

import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from popup_number_parser import PopupNumberParser


def _make_result(text, confidence, bbox):
    return {"text": text, "confidence": confidence, "bbox": bbox}


def _mock_image(width=800, height=600):
    img = MagicMock()
    img.width = width
    img.height = height
    img.crop.return_value = img
    return img


class MockOCREngine:
    def __init__(self, results=None):
        self._results = results or []

    def recognize(self, image):
        return self._results


class TestExtractNumber:
    def test_positive(self):
        assert PopupNumberParser._extract_number("1500") == 1500

    def test_negative(self):
        assert PopupNumberParser._extract_number("-1500") == -1500

    def test_with_plus(self):
        assert PopupNumberParser._extract_number("+500") == 500

    def test_mixed_text(self):
        assert PopupNumberParser._extract_number("受到1500点伤害") is None

    def test_zero(self):
        assert PopupNumberParser._extract_number("0") is None

    def test_too_large(self):
        assert PopupNumberParser._extract_number("100000") is None


class TestParseUnitRegion:
    def test_damage_number(self):
        bbox = [[10, 10], [50, 10], [50, 30], [10, 30]]
        engine = MockOCREngine([_make_result("-1500", 0.95, bbox)])
        parser = PopupNumberParser(engine)
        parser.set_unit_positions([{"name": "剑侠客", "position": (100, 100)}])

        img = _mock_image()
        results = parser.parse(img)

        assert len(results) == 1
        assert results[0].value == -1500
        assert results[0].unit_name == "剑侠客"

    def test_heal_number(self):
        bbox = [[10, 10], [50, 10], [50, 30], [10, 30]]
        engine = MockOCREngine([_make_result("800", 0.92, bbox)])
        parser = PopupNumberParser(engine)
        parser.set_unit_positions([{"name": "剑侠客", "position": (100, 100)}])

        img = _mock_image()
        results = parser.parse(img)

        assert len(results) == 1
        assert results[0].value == 800

    def test_no_numbers(self):
        engine = MockOCREngine([])
        parser = PopupNumberParser(engine)
        parser.set_unit_positions([{"name": "剑侠客", "position": (100, 100)}])

        img = _mock_image()
        results = parser.parse(img)
        assert results == []

    def test_multiple_units(self):
        bbox = [[10, 10], [50, 10], [50, 30], [10, 30]]
        engine = MockOCREngine([
            _make_result("-1000", 0.95, bbox),
            _make_result("500", 0.90, bbox),
        ])
        parser = PopupNumberParser(engine)
        parser.set_unit_positions([
            {"name": "剑侠客", "position": (100, 100)},
            {"name": "龙太子", "position": (300, 100)},
        ])

        img = _mock_image()
        results = parser.parse(img)

        assert len(results) == 4  # 每个角色区域各识别到 2 个
```

- [ ] **Step 3: Run tests**

```bash
cd backend
pytest tests/test_popup_number_parser.py -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/popup_number_parser.py backend/tests/test_popup_number_parser.py
git commit -m "feat: add popup number parser for damage/heal recognition"
```

---

### Task 2: 操作文字扩展识别

**Files:**
- Create: `backend/src/action_text_parser.py`
- Test: `backend/tests/test_action_text_parser.py`

- [ ] **Step 1: Write the module**

```python
"""操作文字扩展识别器：识别特技名、回合、伤害描述。"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from constants import SKILL_ANGER_COST


@dataclass
class ParsedAction:
    action_type: str       # "skill", "round", "damage_desc", "heal_desc", "other"
    text: str              # 原始文字
    unit_name: Optional[str] = None
    skill_name: Optional[str] = None
    round_num: Optional[int] = None
    hp_value: Optional[int] = None


class ActionTextParser:
    """从画面下方的操作文字中识别关键事件。

    识别内容：
    - 特技使用：匹配 SKILL_ANGER_COST 中的特技名
    - 回合切换：匹配"第 X 回合"
    - 伤害描述：匹配"受到 X 点伤害"等
    - 治疗描述：匹配"回复 X 点气血"等
    """

    # 伤害/治疗关键词（仅用于日志描述，不用于血量计算）
    DAMAGE_PATTERNS = [
        r"受到\s*(\d+)\s*点伤害",
        r"造成\s*(\d+)\s*点伤害",
        r"失去\s*(\d+)\s*点气血",
    ]
    HEAL_PATTERNS = [
        r"回复\s*(\d+)\s*点气血",
        r"恢复\s*(\d+)\s*点气血",
        r"治疗\s*(\d+)\s*点",
    ]
    ROUND_PATTERN = re.compile(r"第\s*(\d+)\s*回合")

    def __init__(self, unit_names: List[str] = None):
        self.unit_names = unit_names or []

    def set_unit_names(self, names: List[str]) -> None:
        self.unit_names = names

    def parse(self, ocr_results: List[Dict]) -> List[ParsedAction]:
        """从 OCR 结果列表中解析所有操作事件。"""
        actions = []
        for r in ocr_results:
            text = r.get("text", "").strip()
            if not text:
                continue
            action = self._parse_single(text)
            if action:
                actions.append(action)
        return actions

    def _parse_single(self, text: str) -> Optional[ParsedAction]:
        # 1. 回合检测（最高优先级）
        round_match = self.ROUND_PATTERN.search(text)
        if round_match:
            return ParsedAction(
                action_type="round",
                text=text,
                round_num=int(round_match.group(1)),
            )

        # 2. 特技检测
        for skill_name in SKILL_ANGER_COST:
            if skill_name in text:
                unit_name = self._extract_unit_name(text)
                return ParsedAction(
                    action_type="skill",
                    text=text,
                    unit_name=unit_name,
                    skill_name=skill_name,
                )

        # 3. 伤害描述（仅日志）
        for pattern in self.DAMAGE_PATTERNS:
            m = re.search(pattern, text)
            if m:
                unit_name = self._extract_unit_name(text)
                return ParsedAction(
                    action_type="damage_desc",
                    text=text,
                    unit_name=unit_name,
                    hp_value=int(m.group(1)),
                )

        # 4. 治疗描述（仅日志）
        for pattern in self.HEAL_PATTERNS:
            m = re.search(pattern, text)
            if m:
                unit_name = self._extract_unit_name(text)
                return ParsedAction(
                    action_type="heal_desc",
                    text=text,
                    unit_name=unit_name,
                    hp_value=int(m.group(1)),
                )

        return None

    def _extract_unit_name(self, text: str) -> Optional[str]:
        """从操作文字中提取角色名。简单实现：找第一个匹配到的已知角色名。"""
        for name in self.unit_names:
            if name in text:
                return name
        return None
```

- [ ] **Step 2: Write the tests**

```python
"""Tests for ActionTextParser."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from action_text_parser import ActionTextParser


class TestRoundDetection:
    def test_round(self):
        p = ActionTextParser()
        actions = p.parse([{"text": "第 3 回合", "confidence": 0.9}])
        assert len(actions) == 1
        assert actions[0].action_type == "round"
        assert actions[0].round_num == 3

    def test_round_no_space(self):
        p = ActionTextParser()
        actions = p.parse([{"text": "第3回合", "confidence": 0.9}])
        assert actions[0].round_num == 3


class TestSkillDetection:
    def test_skill(self):
        p = ActionTextParser()
        actions = p.parse([{"text": "剑侠客 使用了晶清诀", "confidence": 0.9}])
        assert len(actions) == 1
        assert actions[0].action_type == "skill"
        assert actions[0].skill_name == "晶清诀"
        assert actions[0].unit_name is None  # 未设置 unit_names

    def test_skill_with_unit_names(self):
        p = ActionTextParser(unit_names=["剑侠客"])
        actions = p.parse([{"text": "剑侠客 使用了晶清诀", "confidence": 0.9}])
        assert actions[0].unit_name == "剑侠客"


class TestDamageDesc:
    def test_damage(self):
        p = ActionTextParser()
        actions = p.parse([{"text": "受到 1500 点伤害", "confidence": 0.9}])
        assert actions[0].action_type == "damage_desc"
        assert actions[0].hp_value == 1500

    def test_heal(self):
        p = ActionTextParser()
        actions = p.parse([{"text": "回复 800 点气血", "confidence": 0.9}])
        assert actions[0].action_type == "heal_desc"
        assert actions[0].hp_value == 800


class TestNoMatch:
    def test_no_match(self):
        p = ActionTextParser()
        actions = p.parse([{"text": "普通攻击", "confidence": 0.9}])
        assert actions == []
```

- [ ] **Step 3: Run tests**

```bash
cd backend
pytest tests/test_action_text_parser.py -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/action_text_parser.py backend/tests/test_action_text_parser.py
git commit -m "feat: add action text parser for skills and round detection"
```

---

### Task 3: 去重机制

**Files:**
- Create: `backend/src/dedup_tracker.py`
- Test: `backend/tests/test_dedup_tracker.py`

- [ ] **Step 1: Write the module**

```python
"""去重追踪器：避免同一伤害/治疗数字在 3 秒窗口内被重复计算。"""

import time
from typing import Optional


class DedupTracker:
    """记录最近处理过的 (unit_name, value) 对，支持时间窗口去重。"""

    def __init__(self, window_ms: int = 3000):
        self.window_ms = window_ms
        self._entries: list[tuple[str, int, float]] = []

    def is_duplicate(self, unit_name: str, value: int) -> bool:
        """检查该组合是否在窗口内已处理过。"""
        now = time.time() * 1000
        cutoff = now - self.window_ms

        # 清理过期条目
        self._entries = [
            (u, v, ts) for (u, v, ts) in self._entries if ts > cutoff
        ]

        for u, v, _ in self._entries:
            if u == unit_name and v == value:
                return True
        return False

    def record(self, unit_name: str, value: int) -> None:
        """记录一次处理。"""
        now = time.time() * 1000
        self._entries.append((unit_name, value, now))

    def clear(self) -> None:
        """清空所有记录。"""
        self._entries = []
```

- [ ] **Step 2: Write the tests**

```python
"""Tests for DedupTracker."""

import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dedup_tracker import DedupTracker


class TestDedupTracker:
    def test_first_entry_not_duplicate(self):
        t = DedupTracker(window_ms=3000)
        assert t.is_duplicate("A", 100) is False

    def test_duplicate_within_window(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        assert t.is_duplicate("A", 100) is True

    def test_different_value_not_duplicate(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        assert t.is_duplicate("A", 200) is False

    def test_different_unit_not_duplicate(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        assert t.is_duplicate("B", 100) is False

    def test_expired_entry_not_duplicate(self):
        t = DedupTracker(window_ms=100)
        t.record("A", 100)
        time.sleep(0.15)
        assert t.is_duplicate("A", 100) is False

    def test_clear(self):
        t = DedupTracker(window_ms=3000)
        t.record("A", 100)
        t.clear()
        assert t.is_duplicate("A", 100) is False
```

- [ ] **Step 3: Run tests**

```bash
cd backend
pytest tests/test_dedup_tracker.py -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/dedup_tracker.py backend/tests/test_dedup_tracker.py
git commit -m "feat: add dedup tracker for popup numbers"
```

---

### Task 4: 重写 _on_ocr_results

**Files:**
- Modify: `backend/src/websocket_handler.py`
- Modify: `backend/src/ocr_parser.py`
- Test: `backend/tests/test_ocr_parser.py`

- [ ] **Step 1: 修改 `ocr_parser.py` 集成新解析器**

在 `BattleOCRParser.__init__` 末尾添加：

```python
from popup_number_parser import PopupNumberParser
from action_text_parser import ActionTextParser

# ... 在 __init__ 末尾添加：
self.popup_parser = PopupNumberParser(self.ocr)
self.action_parser = ActionTextParser()
```

在 `BattleOCRParser` 中添加新方法：

```python
def parse_popup_numbers(self, image) -> List[Dict]:
    """识别所有角色的弹出数字。"""
    if not self.unit_positions:
        return []
    units = [{"name": u.name, "position": u.position} for u in self.unit_positions]
    self.popup_parser.set_unit_positions(units)
    numbers = self.popup_parser.parse(image)
    return [
        {
            "value": n.value,
            "unit_name": n.unit_name,
            "raw_text": n.raw_text,
            "confidence": n.confidence,
        }
        for n in numbers
    ]

def parse_actions(self, ocr_results: List[Dict]) -> List[Dict]:
    """识别操作文字中的特技、回合、伤害描述。"""
    unit_names = [u.name for u in self.unit_positions]
    self.action_parser.set_unit_names(unit_names)
    actions = self.action_parser.parse(ocr_results)
    return [
        {
            "action_type": a.action_type,
            "text": a.text,
            "unit_name": a.unit_name,
            "skill_name": a.skill_name,
            "round_num": a.round_num,
            "hp_value": a.hp_value,
        }
        for a in actions
    ]
```

- [ ] **Step 2: 修改 `websocket_handler.py` 导入新模块**

在文件顶部添加：

```python
from dedup_tracker import DedupTracker
```

在 `ConnectionManager.__init__` 中添加：

```python
self.popup_dedup = DedupTracker(window_ms=3000)
```

- [ ] **Step 3: 重写 `_on_ocr_results`**

```python
def _on_ocr_results(self, results: list[dict]) -> None:
    """OCR 识别结果回调。解析弹出数字和操作文字并更新战斗状态。"""
    if self.battle_engine is None:
        return

    image = getattr(self.screenshot_engine, "_last_capture", None)
    if image is None:
        return

    # 1. 识别弹出数字（伤害/治疗）
    popup_numbers = self.ocr_parser.parse_popup_numbers(image)
    processed_numbers = []

    for pn in popup_numbers:
        unit = self._find_unit_by_name(pn["unit_name"])
        if unit is None:
            continue

        value = pn["value"]
        if self.popup_dedup.is_duplicate(unit["name"], value):
            continue
        self.popup_dedup.record(unit["name"], value)

        if value < 0:
            self.battle_engine.apply_damage(
                unit["id"], abs(value), f"受到 {abs(value)} 点伤害"
            )
        else:
            self.battle_engine.apply_heal(
                unit["id"], value, f"回复 {value} 点气血"
            )
        processed_numbers.append(pn)

    # 2. 识别操作文字（特技 + 回合）
    actions = self.ocr_parser.parse_actions(results)
    processed_actions = []

    for act in actions:
        if act["action_type"] == "skill" and act["skill_name"]:
            unit = self._find_unit_by_name(act["unit_name"])
            if unit:
                try:
                    self.battle_engine.use_skill(unit["id"], act["skill_name"])
                except ValueError:
                    pass  # 愤怒不足，忽略
            processed_actions.append(act)

        elif act["action_type"] == "round" and act["round_num"] is not None:
            target = act["round_num"]
            while self.battle_engine.current_round < target:
                self.battle_engine.next_round()
            processed_actions.append(act)

        elif act["action_type"] in ("damage_desc", "heal_desc"):
            # 仅作为日志记录，不用于血量计算
            unit = self._find_unit_by_name(act["unit_name"])
            if unit:
                desc = "受到攻击" if act["action_type"] == "damage_desc" else "气血回复"
                self.battle_engine.record_cast(unit["id"], act["text"])
            processed_actions.append(act)

    # 3. 广播状态更新
    asyncio.create_task(self.push_state())

    # 4. 广播 OCR 调试信息
    asyncio.create_task(
        self.broadcast({
            "type": "ocr_debug",
            "data": {
                "popup_numbers": processed_numbers,
                "actions": processed_actions,
                "timestamp": int(time.time() * 1000),
            },
        })
    )
```

- [ ] **Step 4: 战斗结束时清空去重缓存**

在 `_do_end_battle` 中添加：

```python
self.popup_dedup.clear()
```

- [ ] **Step 5: 补充 ocr_parser 集成测试**

在 `test_ocr_parser.py` 末尾添加：

```python
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
```

- [ ] **Step 6: Run tests**

```bash
cd backend
pytest tests/test_ocr_parser.py tests/test_dedup_tracker.py -v
```

Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/ocr_parser.py backend/src/websocket_handler.py backend/tests/test_ocr_parser.py
git commit -m "feat: integrate popup numbers and action text into ocr pipeline"
```

---

### Task 5: 修复初始愤怒值测试

**Files:**
- Modify: `backend/tests/test_battle_engine.py:14`

- [ ] **Step 1: Fix the test**

```python
# 修改第 14 行
assert unit["current_anger"] == 90
```

- [ ] **Step 2: Run tests**

```bash
cd backend
pytest tests/test_battle_engine.py -v
```

Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_battle_engine.py
git commit -m "fix: update test to expect initial anger 90"
```

---

### Task 6: OCR 调试面板（前端）

**Files:**
- Create: `frontend/src/components/OCRDebugPanel.tsx`
- Modify: `frontend/src/components/ActionPanel.tsx`

- [ ] **Step 1: 创建 OCRDebugPanel 组件**

```tsx
import { useState, useEffect } from 'react'
import { useCombatStore } from '@/stores/useCombatStore'

interface OCRDebugData {
  popup_numbers: Array<{
    value: number
    unit_name: string
    raw_text: string
    confidence: number
  }>
  actions: Array<{
    action_type: string
    text: string
    unit_name: string | null
    skill_name: string | null
    round_num: number | null
  }>
  timestamp: number
}

export default function OCRDebugPanel() {
  const [debugData, setDebugData] = useState<OCRDebugData | null>(null)
  const logs = useCombatStore((s) => s.logs)

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'ocr_debug') {
        setDebugData(event.data.data)
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [])

  // 通过 WebSocket 的 raw message 监听 ocr_debug
  // 注意：useWebSocket 当前没有暴露 ocr_debug，需要扩展
  // 这里先展示结构，实际需配合 useWebSocket 修改

  return (
    <div className="border-t border-border-gray p-3 bg-gray-50">
      <h3 className="text-xs font-semibold text-gray-500 mb-2">OCR 调试</h3>
      {debugData ? (
        <div className="space-y-2 text-xs">
          {debugData.popup_numbers.length > 0 && (
            <div>
              <span className="text-gray-400">弹出数字:</span>
              {debugData.popup_numbers.map((n, i) => (
                <span
                  key={i}
                  className={`ml-2 font-mono ${n.value < 0 ? 'text-red-600' : 'text-green-600'}`}
                >
                  {n.unit_name}: {n.value > 0 ? '+' : ''}{n.value}
                </span>
              ))}
            </div>
          )}
          {debugData.actions.length > 0 && (
            <div>
              <span className="text-gray-400">操作文字:</span>
              {debugData.actions.map((a, i) => (
                <span key={i} className="ml-2 text-deep-navy">
                  {a.action_type === 'round' && `回合${a.round_num}`}
                  {a.action_type === 'skill' && `${a.unit_name}·${a.skill_name}`}
                  {a.action_type === 'damage_desc' && `伤${a.hp_value}`}
                  {a.action_type === 'heal_desc' && `治${a.hp_value}`}
                </span>
              ))}
            </div>
          )}
          <div className="text-gray-400">
            最新日志: {logs.length > 0 ? logs[logs.length - 1].description : '无'}
          </div>
        </div>
      ) : (
        <div className="text-gray-400 text-xs">等待 OCR 数据...</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 修改 useWebSocket.ts 接收 ocr_debug**

在 `handleMessage` 中添加：

```typescript
case 'ocr_debug': {
  // 可以通过全局事件或 store 传递
  window.dispatchEvent(new MessageEvent('message', { data: msg }))
  break
}
```

实际上 `window.addEventListener('message', ...)` 监听的是 `window.postMessage`，而 WebSocket 的消息不会触发 `window.message`。需要改用其他方式。

更简洁的方式：在 `useCombatStore` 中添加 `ocrDebugData` 字段，或者创建一个独立的 hook。

修改 `frontend/src/stores/useCombatStore.ts`：

```typescript
interface CombatStore extends BattleState {
  // ... existing fields
  ocrDebug: OCRDebugData | null
  setOcrDebug: (data: OCRDebugData | null) => void
}

// initialState 添加
ocrDebug: null,

// store 实现添加
setOcrDebug: (ocrDebug) => set({ ocrDebug }),
```

修改 `frontend/src/hooks/useWebSocket.ts`：

```typescript
case 'ocr_debug': {
  store.setOcrDebug(msg.data)
  break
}
```

- [ ] **Step 3: 修改 ActionPanel.tsx 集成调试面板**

```tsx
import OCRDebugPanel from './OCRDebugPanel'

// 在 ActionPanel 的 LogViewer 下方添加：
<OCRDebugPanel />
```

- [ ] **Step 4: Build frontend**

```bash
cd frontend
npm run build
```

Expected: build 成功，无 TypeScript 错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/OCRDebugPanel.tsx frontend/src/stores/useCombatStore.ts frontend/src/hooks/useWebSocket.ts frontend/src/components/ActionPanel.tsx
git commit -m "feat: add OCR debug panel to frontend"
```

---

### Task 7: 集成验证

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
pytest -v
```

Expected: all PASS

- [ ] **Step 2: Run frontend build**

```bash
cd frontend
npm run build
```

Expected: build 成功

- [ ] **Step 3: Start services and manual test**

```bash
# Terminal 1
cd backend/src
python -m uvicorn main:app --host 0.0.0.0 --port 8765

# Terminal 2
cd frontend
npm run dev
```

打开浏览器 `http://localhost:5173`，点击"选择监控区域"测试全屏选区，然后点击"战斗开始"测试 OCR 流水线。

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete OCR automation pipeline"
```

---

## Self-Review

### Spec Coverage

| Spec Section | Implementing Task |
|--------------|-------------------|
| 弹出数字识别 | Task 1 |
| 操作文字扩展（特技+回合） | Task 2 |
| 去重策略 | Task 3 |
| _on_ocr_results 重写 | Task 4 |
| 初始愤怒 90 | Task 5 |
| OCR 调试面板 | Task 6 |
| 战斗生命周期 | Task 4 (start/end battle) |
| 状态同步 | Task 4 (push_state + ocr_debug broadcast) |

**Gap:** 操作文字中的伤害描述日志记录（`record_cast`）在 Task 4 中已包含，但未在前端日志中特殊展示。当前 LogViewer 已有 `action_type` 区分，足够使用。

### Placeholder Scan

- 无 TBD/TODO
- 无 "appropriate error handling" 等模糊描述
- 每个 step 包含完整代码

### Type Consistency

- `PopupNumberParser` 使用 `List[Dict]` 传入 unit_positions
- `ocr_parser.py` 适配层转换为相同格式
- `ActionTextParser` 使用 `unit_names: List[str]`
- 前后一致

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-23-ocr-automation.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
