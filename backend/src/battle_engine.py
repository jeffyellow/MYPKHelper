"""战斗状态引擎：管理角色、气血/愤怒、回合和日志。"""

import uuid
import time
from typing import Optional
from constants import FACTION_HP, SKILL_ANGER_COST
from anger_calculator import calculate_anger_from_damage


class BattleEngine:
    def __init__(self):
        self.units = {}
        self.logs = []
        self.current_round = 0
        self.is_active = False

    def init_unit(
        self,
        unit_id,
        name,
        faction,
        ye_zhang_shield=0,
    ):
        base_hp = FACTION_HP.get(faction, 12000)

        if ye_zhang_shield > 0:
            max_hp = int(ye_zhang_shield / 0.24)
            current_hp = max_hp
            shield = ye_zhang_shield
        else:
            max_hp = base_hp
            current_hp = base_hp
            shield = 0

        unit = {
            "id": unit_id,
            "name": name,
            "faction": faction,
            "max_hp": max_hp,
            "current_hp": current_hp,
            "shield": shield,
            "current_anger": 90,
            "ye_zhang_shield": ye_zhang_shield,
        }
        self.units[unit_id] = unit
        return unit

    def get_unit(self, unit_id):
        return self.units.get(unit_id)

    def set_anger(self, unit_id, anger):
        if unit_id in self.units:
            self.units[unit_id]["current_anger"] = max(0, anger)

    def apply_damage(self, unit_id, damage, description="受到攻击"):
        unit = self.units.get(unit_id)
        if unit is None:
            raise ValueError("Unit {} not found".format(unit_id))

        actual_damage = min(damage, unit["current_hp"] + unit["shield"])
        anger_gain = calculate_anger_from_damage(unit["max_hp"], actual_damage)

        if unit["shield"] > 0:
            shield_absorb = min(unit["shield"], actual_damage)
            unit["shield"] -= shield_absorb
            actual_damage -= shield_absorb

        unit["current_hp"] = max(0, unit["current_hp"] - actual_damage)
        unit["current_anger"] = min(150, unit["current_anger"] + anger_gain)

        self._add_log(unit_id, "hit", description, hp_change=-damage, anger_change=anger_gain)

    def apply_heal(self, unit_id, amount, description="气血回复"):
        unit = self.units.get(unit_id)
        if unit is None:
            raise ValueError("Unit {} not found".format(unit_id))

        old_hp = unit["current_hp"]
        unit["current_hp"] = min(unit["max_hp"], unit["current_hp"] + amount)
        actual_heal = unit["current_hp"] - old_hp

        self._add_log(unit_id, "heal", description, hp_change=actual_heal, anger_change=0)

    def use_skill(self, unit_id, skill_name):
        unit = self.units.get(unit_id)
        if unit is None:
            raise ValueError("Unit {} not found".format(unit_id))

        cost = SKILL_ANGER_COST.get(skill_name, 0)
        if unit["current_anger"] < cost:
            raise ValueError("Not enough anger")

        unit["current_anger"] -= cost
        self._add_log(unit_id, "skill", "使用{}".format(skill_name), anger_change=-cost)

    def record_cast(self, unit_id, spell_name):
        self._add_log(unit_id, "cast", "使用{}".format(spell_name))

    def next_round(self):
        self.current_round += 1

    def start_battle(self):
        self.is_active = True
        self.current_round = 1

    def end_battle(self):
        self.is_active = False

    def get_logs_for_unit(self, unit_id):
        return [log for log in self.logs if log["unit_id"] == unit_id]

    def get_all_units(self):
        return list(self.units.values())

    def get_all_logs(self):
        return self.logs

    def _add_log(
        self,
        unit_id,
        action_type,
        description,
        hp_change=0,
        anger_change=0,
    ):
        log = {
            "id": str(uuid.uuid4()),
            "round": self.current_round,
            "unit_id": unit_id,
            "action_type": action_type,
            "description": description,
            "hp_change": hp_change,
            "anger_change": anger_change,
            "timestamp": int(time.time() * 1000),
        }
        self.logs.append(log)
