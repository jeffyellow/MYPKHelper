import pytest
import tempfile
import os
from database import Database


@pytest.fixture
async def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.db")
        database = Database(path)
        await database.init()
        yield database
        await database.close()


pytestmark = pytest.mark.asyncio(loop_scope="function")


class TestDatabase:
    async def test_create_and_get_unit(self, db):
        unit = {
            "id": "u1",
            "name": "Player1",
            "faction": "大唐",
            "max_hp": 12000,
            "current_hp": 12000,
            "shield": 0,
            "current_anger": 0,
            "ye_zhang_shield": 0,
        }
        await db.save_unit(unit)
        result = await db.get_unit("u1")
        assert result is not None
        assert result["name"] == "Player1"
        assert result["faction"] == "大唐"

    async def test_save_battle_record(self, db):
        record = {
            "id": "b1",
            "start_time": 1234567890,
            "end_time": 1234567990,
            "opponent_name": "TeamA",
            "result": "win",
            "unit_ids": '["u1", "u2"]',
        }
        await db.save_battle_record(record)
        records = await db.list_battle_records()
        assert len(records) == 1
        assert records[0]["opponent_name"] == "TeamA"

    async def test_save_combat_log(self, db):
        log = {
            "id": "l1",
            "round": 1,
            "unit_id": "u1",
            "action_type": "hit",
            "description": "受到物理攻击",
            "hp_change": -500,
            "anger_change": 3,
            "timestamp": 1234567890,
        }
        await db.save_combat_log(log)
        logs = await db.get_logs_for_unit("u1")
        assert len(logs) == 1
        assert logs[0]["hp_change"] == -500
