import pytest
from anger_calculator import calculate_anger_from_damage, get_skill_cost


class TestCalculateAngerFromDamage:
    def test_1_percent_damage(self):
        assert calculate_anger_from_damage(15000, 150) == 1  # 1%

    def test_3_percent_boundary_low(self):
        assert calculate_anger_from_damage(15000, 449) == 1  # 2.99%

    def test_3_percent_boundary_high(self):
        assert calculate_anger_from_damage(15000, 450) == 3  # 3%

    def test_10_percent_damage(self):
        assert calculate_anger_from_damage(15000, 1500) == 3  # 10%

    def test_20_percent_damage(self):
        assert calculate_anger_from_damage(15000, 3000) == 10  # 20%

    def test_50_percent_damage(self):
        assert calculate_anger_from_damage(15000, 7500) == 25  # 50%

    def test_80_percent_damage(self):
        assert calculate_anger_from_damage(15000, 12000) == 40  # 80%

    def test_99_percent_damage(self):
        assert calculate_anger_from_damage(15000, 14850) == 55  # 99%

    def test_zero_damage(self):
        assert calculate_anger_from_damage(15000, 0) == 1

    def test_damage_exceeds_hp(self):
        with pytest.raises(ValueError):
            calculate_anger_from_damage(15000, 16000)

    def test_different_max_hp(self):
        assert calculate_anger_from_damage(10000, 300) == 3  # 3%
        assert calculate_anger_from_damage(12000, 360) == 3  # 3%


class TestGetSkillCost:
    def test_known_skill(self):
        assert get_skill_cost("晶清诀") == 120
        assert get_skill_cost("放下屠刀") == 24

    def test_unknown_skill(self):
        assert get_skill_cost("未知特技") == 0
