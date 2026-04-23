"""Parse action text from bottom-of-screen OCR results."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from constants import SKILL_ANGER_COST


@dataclass
class ParsedAction:
    action_type: str
    text: str
    unit_name: Optional[str] = None
    skill_name: Optional[str] = None
    round_num: Optional[int] = None
    hp_value: Optional[int] = None


class ActionTextParser:
    """Recognize skill usage, round changes, damage/heal descriptions."""

    def __init__(self, unit_names: Optional[List[str]] = None):
        self._unit_names = unit_names or []

    def set_unit_names(self, names: List[str]) -> None:
        self._unit_names = names

    def parse(self, ocr_results: List[Dict]) -> List[ParsedAction]:
        actions = []
        for result in ocr_results:
            text = result.get("text", "")
            action = self._parse_single(text)
            if action is not None:
                actions.append(action)
        return actions

    def _parse_single(self, text: str) -> Optional[ParsedAction]:
        # 1. Round pattern
        round_match = re.search(r"第\s*(\d+)\s*回合", text)
        if round_match:
            return ParsedAction(
                action_type="round",
                text=text,
                round_num=int(round_match.group(1)),
            )

        # 2. Skill pattern
        for skill_name in SKILL_ANGER_COST:
            if skill_name in text:
                unit_name = self._extract_unit_name(text)
                return ParsedAction(
                    action_type="skill",
                    text=text,
                    unit_name=unit_name,
                    skill_name=skill_name,
                )

        # 3. Damage patterns
        damage_match = re.search(r"(?:受到|造成|失去)\s*(\d+)\s*点(?:伤害|气血)", text)
        if damage_match:
            unit_name = self._extract_unit_name(text)
            return ParsedAction(
                action_type="damage_desc",
                text=text,
                unit_name=unit_name,
                hp_value=int(damage_match.group(1)),
            )

        # 4. Heal patterns
        heal_match = re.search(r"(?:回复|恢复)\s*(\d+)\s*点气血", text)
        if heal_match:
            unit_name = self._extract_unit_name(text)
            return ParsedAction(
                action_type="heal_desc",
                text=text,
                unit_name=unit_name,
                hp_value=int(heal_match.group(1)),
            )
        heal_match2 = re.search(r"治疗\s*(\d+)\s*点", text)
        if heal_match2:
            unit_name = self._extract_unit_name(text)
            return ParsedAction(
                action_type="heal_desc",
                text=text,
                unit_name=unit_name,
                hp_value=int(heal_match2.group(1)),
            )

        return None

    def _extract_unit_name(self, text: str) -> Optional[str]:
        for name in self._unit_names:
            if name in text:
                return name
        return None
