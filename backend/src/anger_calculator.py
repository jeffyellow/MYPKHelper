"""计算伤害获得的愤怒和特技消耗的愤怒。"""

from constants import DAMAGE_ANGER_TABLE, SKILL_ANGER_COST


def calculate_anger_from_damage(max_hp: int, damage: int) -> int:
    """返回当最大气血为 `max_hp` 时，受到 `damage` 伤害获得的愤怒。"""
    if damage < 0:
        raise ValueError("伤害不能为负数")
    if damage > max_hp:
        raise ValueError("伤害不能超过最大气血")

    if max_hp <= 0:
        raise ValueError("max_hp 必须为正数")

    ratio = damage / max_hp

    for i, ((low, high), anger) in enumerate(DAMAGE_ANGER_TABLE):
        if i == 0:
            if low <= ratio < high:
                return anger
        else:
            if low <= ratio <= high:
                return anger

    return 55


def get_skill_cost(skill_name: str) -> int:
    """返回特技的愤怒消耗。未知特技返回 0。"""
    return SKILL_ANGER_COST.get(skill_name, 0)
