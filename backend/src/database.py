"""使用 aiosqlite 的 SQLite 持久化层。"""

import aiosqlite
import json
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: str = "mypkhelper.db"):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def init(self):
        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()

    async def close(self):
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _create_tables(self):
        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS combat_units (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                faction TEXT NOT NULL,
                max_hp INTEGER NOT NULL,
                current_hp INTEGER NOT NULL,
                shield INTEGER DEFAULT 0,
                current_anger INTEGER DEFAULT 0,
                ye_zhang_shield INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS combat_logs (
                id TEXT PRIMARY KEY,
                round INTEGER NOT NULL,
                unit_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                hp_change INTEGER DEFAULT 0,
                anger_change INTEGER DEFAULT 0,
                timestamp INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS battle_records (
                id TEXT PRIMARY KEY,
                start_time INTEGER NOT NULL,
                end_time INTEGER,
                opponent_name TEXT,
                result TEXT,
                unit_ids TEXT
            );
        """)
        await self._connection.commit()

    async def save_unit(self, unit: dict) -> None:
        await self._connection.execute(
            """
            INSERT OR REPLACE INTO combat_units
            (id, name, faction, max_hp, current_hp, shield, current_anger, ye_zhang_shield)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                unit["id"], unit["name"], unit["faction"],
                unit["max_hp"], unit["current_hp"],
                unit.get("shield", 0), unit.get("current_anger", 0),
                unit.get("ye_zhang_shield", 0),
            ),
        )
        await self._connection.commit()

    async def get_unit(self, unit_id: str) -> Optional[dict]:
        async with self._connection.execute(
            "SELECT * FROM combat_units WHERE id = ?", (unit_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))

    async def save_combat_log(self, log: dict) -> None:
        await self._connection.execute(
            """
            INSERT OR REPLACE INTO combat_logs
            (id, round, unit_id, action_type, description, hp_change, anger_change, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log["id"], log["round"], log["unit_id"],
                log["action_type"], log["description"],
                log.get("hp_change", 0), log.get("anger_change", 0),
                log["timestamp"],
            ),
        )
        await self._connection.commit()

    async def get_logs_for_unit(self, unit_id: str) -> List[Dict]:
        async with self._connection.execute(
            "SELECT * FROM combat_logs WHERE unit_id = ? ORDER BY timestamp",
            (unit_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def save_battle_record(self, record: dict) -> None:
        unit_ids = record.get("unit_ids", [])
        if isinstance(unit_ids, list):
            unit_ids = json.dumps(unit_ids)

        await self._connection.execute(
            """
            INSERT OR REPLACE INTO battle_records
            (id, start_time, end_time, opponent_name, result, unit_ids)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"], record["start_time"], record.get("end_time"),
                record.get("opponent_name"), record.get("result"), unit_ids,
            ),
        )
        await self._connection.commit()

    async def list_battle_records(self) -> List[Dict]:
        async with self._connection.execute(
            "SELECT * FROM battle_records ORDER BY start_time DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
