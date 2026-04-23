import pytest
from battle_engine import BattleEngine


class TestBattleEngine:
    def test_init_with_faction(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        unit = engine.get_unit("u1")
        assert unit["name"] == "Player1"
        assert unit["faction"] == "大唐"
        assert unit["max_hp"] == 12000
        assert unit["current_hp"] == 12000
        assert unit["current_anger"] == 90

    def test_init_with_ye_zhang(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐", ye_zhang_shield=2400)
        unit = engine.get_unit("u1")
        assert unit["ye_zhang_shield"] == 2400
        assert unit["max_hp"] == 10000  # 2400 / 0.24
        assert unit["current_hp"] == 10000
        assert unit["shield"] == 2400

    def test_apply_damage(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        engine.apply_damage("u1", 450)  # 12000 的 3.75%
        unit = engine.get_unit("u1")
        assert unit["current_hp"] == 11550
        assert unit["current_anger"] == 93  # 初始 90 + 受伤 3

    def test_apply_damage_through_shield(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐", ye_zhang_shield=2400)
        engine.apply_damage("u1", 1000)
        unit = engine.get_unit("u1")
        assert unit["shield"] == 1400
        assert unit["current_hp"] == 10000

    def test_apply_heal(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        engine.apply_damage("u1", 1000)
        engine.apply_heal("u1", 500)
        unit = engine.get_unit("u1")
        assert unit["current_hp"] == 11500

    def test_heal_cannot_exceed_max(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        engine.apply_heal("u1", 99999)
        unit = engine.get_unit("u1")
        assert unit["current_hp"] == 12000

    def test_use_skill(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        engine.set_anger("u1", 120)
        engine.use_skill("u1", "晶清诀")
        unit = engine.get_unit("u1")
        assert unit["current_anger"] == 0

    def test_use_skill_not_enough_anger(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        engine.set_anger("u1", 50)
        with pytest.raises(ValueError, match="Not enough anger"):
            engine.use_skill("u1", "晶清诀")

    def test_next_round(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        assert engine.current_round == 0
        engine.next_round()
        assert engine.current_round == 1
        engine.next_round()
        assert engine.current_round == 2

    def test_log_created_on_damage(self):
        engine = BattleEngine()
        engine.init_unit("u1", "Player1", "大唐")
        engine.next_round()
        engine.apply_damage("u1", 500)
        logs = engine.get_logs_for_unit("u1")
        assert len(logs) == 1
        assert logs[0]["action_type"] == "hit"
        assert logs[0]["round"] == 1
