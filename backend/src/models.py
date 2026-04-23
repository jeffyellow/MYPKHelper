"""API 和内部数据的 Pydantic 模型。"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ActionType(str, Enum):
    CAST = "cast"
    HIT = "hit"
    HEAL = "heal"
    SKILL = "skill"
    OTHER = "other"


class CombatUnit(BaseModel):
    id: str
    name: str
    faction: str
    max_hp: int
    current_hp: int
    shield: int = 0
    current_anger: int = 0
    ye_zhang_shield: int = 0


class CombatLog(BaseModel):
    id: str
    round: int
    unit_id: str
    action_type: ActionType
    description: str
    hp_change: int = 0
    anger_change: int = 0
    timestamp: int


class BattleRecord(BaseModel):
    id: str
    start_time: int
    end_time: Optional[int] = None
    opponent_name: Optional[str] = None
    result: Optional[str] = None
    unit_ids: list = Field(default_factory=list)


class MonitorRegion(BaseModel):
    x: int
    y: int
    width: int
    height: int


class BattleStateUpdate(BaseModel):
    units: list
    current_round: int
    logs: list
    is_active: bool
