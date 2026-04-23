"""Tests for ActionTextParser."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from action_text_parser import ActionTextParser, ParsedAction


class TestRoundParsing:
    def test_round(self):
        parser = ActionTextParser()
        actions = parser.parse([{"text": "第 3 回合"}])
        assert len(actions) == 1
        assert actions[0].action_type == "round"
        assert actions[0].round_num == 3

    def test_round_no_space(self):
        parser = ActionTextParser()
        actions = parser.parse([{"text": "第3回合"}])
        assert len(actions) == 1
        assert actions[0].action_type == "round"
        assert actions[0].round_num == 3


class TestSkillParsing:
    def test_skill(self):
        parser = ActionTextParser()
        actions = parser.parse([{"text": "剑侠客 使用了晶清诀"}])
        assert len(actions) == 1
        assert actions[0].action_type == "skill"
        assert actions[0].skill_name == "晶清诀"

    def test_skill_with_unit_names(self):
        parser = ActionTextParser(unit_names=["剑侠客"])
        actions = parser.parse([{"text": "剑侠客 使用了晶清诀"}])
        assert len(actions) == 1
        assert actions[0].action_type == "skill"
        assert actions[0].skill_name == "晶清诀"
        assert actions[0].unit_name == "剑侠客"


class TestDamageDescParsing:
    def test_damage_desc(self):
        parser = ActionTextParser()
        actions = parser.parse([{"text": "受到 1500 点伤害"}])
        assert len(actions) == 1
        assert actions[0].action_type == "damage_desc"
        assert actions[0].hp_value == 1500


class TestHealDescParsing:
    def test_heal_desc(self):
        parser = ActionTextParser()
        actions = parser.parse([{"text": "回复 800 点气血"}])
        assert len(actions) == 1
        assert actions[0].action_type == "heal_desc"
        assert actions[0].hp_value == 800


class TestNoMatch:
    def test_no_match(self):
        parser = ActionTextParser()
        actions = parser.parse([{"text": "普通攻击"}])
        assert actions == []
