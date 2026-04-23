"""WebSocket 连接管理器：处理战斗相关消息并向客户端广播状态。"""

import asyncio
import json
import uuid
import time
import re
from typing import Optional

from fastapi import WebSocket

from battle_engine import BattleEngine
from database import Database
from screenshot import ScreenshotEngine, Region
from ocr_engine import OCREngine
from ocr_parser import BattleOCRParser
from screen_monitor import ScreenMonitor
from dedup_tracker import DedupTracker


class ConnectionManager:
    """管理 WebSocket 连接、战斗引擎实例和状态广播。"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.battle_engine: Optional[BattleEngine] = None
        self.database: Optional[Database] = None
        self.monitor_region: Optional[dict] = None

        self.screenshot_engine = ScreenshotEngine()
        self.ocr_engine = OCREngine()
        self.ocr_parser = BattleOCRParser(self.ocr_engine)
        self.screen_monitor = ScreenMonitor(
            self.screenshot_engine,
            self.ocr_engine,
            interval=5.0,
        )
        self.screen_monitor.add_callback(self._on_ocr_results)
        self.popup_dedup = DedupTracker(window_ms=3000)

    def set_database(self, db: Database) -> None:
        self.database = db

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        text = json.dumps(message, ensure_ascii=False)
        for conn in self.active_connections:
            try:
                await conn.send_text(text)
            except Exception:
                pass

    async def push_state(self) -> None:
        """将当前战斗状态广播给所有客户端。"""
        if self.battle_engine is None:
            return
        payload = {
            "type": "state_update",
            "data": {
                "units": self.battle_engine.get_all_units(),
                "current_round": self.battle_engine.current_round,
                "logs": self.battle_engine.get_all_logs(),
                "is_active": self.battle_engine.is_active,
            },
        }
        await self.broadcast(payload)

    async def handle_message(self, websocket: WebSocket, raw: str) -> None:
        """解析并分发 WebSocket 消息。"""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        action = msg.get("action")
        data = msg.get("data", {})

        handlers = {
            "set_region": self._do_set_region,
            "start_battle": self._do_start_battle,
            "end_battle": self._do_end_battle,
            "init_unit": self._do_init_unit,
            "get_logs": self._do_get_logs,
            "manual_update": self._do_manual_update,
        }

        handler = handlers.get(action)
        if handler is None:
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Unknown action: {action}"})
            )
            return

        await handler(websocket, data)

    async def _do_set_region(self, websocket: WebSocket, data: dict) -> None:
        region = data.get("region", data)
        self.monitor_region = {
            "x": region.get("x", 0),
            "y": region.get("y", 0),
            "width": region.get("width", 0),
            "height": region.get("height", 0),
        }
        region = Region(
            x=self.monitor_region["x"],
            y=self.monitor_region["y"],
            width=self.monitor_region["width"],
            height=self.monitor_region["height"],
        )
        self.screenshot_engine.set_region(region)
        await websocket.send_text(
            json.dumps({"type": "region_set", "data": self.monitor_region})
        )

    async def _do_start_battle(self, websocket: WebSocket, data: dict) -> None:
        if self.battle_engine is None:
            self.battle_engine = BattleEngine()
        self.battle_engine.start_battle()

        # 战斗开始时截图并 OCR 识别对手角色
        try:
            image = self.screenshot_engine.capture()
            units = self.ocr_parser.parse_first_frame(image)
            for unit in units:
                self.battle_engine.init_unit(
                    unit_id=str(uuid.uuid4()),
                    name=unit.name,
                    faction=unit.faction or "",
                    ye_zhang_shield=0,
                )
        except Exception as exc:
            logger = __import__("logging").getLogger(__name__)
            logger.exception("OCR first frame failed")

        # 战斗期间加快截图频率到 1.0s
        self.screen_monitor.set_interval(1.0)
        await self.screen_monitor.start()
        await self.push_state()

    async def _do_end_battle(self, websocket: WebSocket, data: dict) -> None:
        await self.screen_monitor.stop()
        # 恢复默认截图间隔
        self.screen_monitor.set_interval(5.0)
        self.popup_dedup.clear()
        if self.battle_engine:
            self.battle_engine.end_battle()
            if self.database:
                record = {
                    "id": str(uuid.uuid4()),
                    "start_time": int(time.time() * 1000),
                    "end_time": int(time.time() * 1000),
                    "opponent_name": data.get("opponent_name"),
                    "result": data.get("result"),
                    "unit_ids": list(self.battle_engine.units.keys()),
                }
                await self.database.save_battle_record(record)
        await self.push_state()

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
                unit = self._find_unit_by_name(act["unit_name"])
                if unit:
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

    def _find_unit_by_name(self, name: str) -> Optional[dict]:
        if self.battle_engine is None:
            return None
        for unit in self.battle_engine.get_all_units():
            if unit.get("name") == name:
                return unit
        return None

    async def _do_init_unit(self, websocket: WebSocket, data: dict) -> None:
        if self.battle_engine is None:
            self.battle_engine = BattleEngine()
        unit = self.battle_engine.init_unit(
            unit_id=data.get("id"),
            name=data.get("name"),
            faction=data.get("faction"),
            ye_zhang_shield=data.get("ye_zhang_shield", 0),
        )
        if self.database:
            await self.database.save_unit(unit)
        await self.push_state()

    async def _do_get_logs(self, websocket: WebSocket, data: dict) -> None:
        unit_id = data.get("unit_id")
        if self.battle_engine is None:
            logs = []
        elif unit_id:
            logs = self.battle_engine.get_logs_for_unit(unit_id)
        else:
            logs = self.battle_engine.get_all_logs()
        await websocket.send_text(json.dumps({"type": "logs", "logs": logs}))

    async def _do_manual_update(self, websocket: WebSocket, data: dict) -> None:
        if self.battle_engine is None:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Battle not started"})
            )
            return

        unit_id = data.get("unit_id")
        update_type = data.get("update_type")
        value = data.get("value", 0)
        description = data.get("description", "")

        unit = self.battle_engine.get_unit(unit_id)
        if unit is None:
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Unit {unit_id} not found"})
            )
            return

        if update_type == "damage":
            self.battle_engine.apply_damage(unit_id, value, description or "受到攻击")
        elif update_type == "heal":
            self.battle_engine.apply_heal(unit_id, value, description or "气血回复")
        elif update_type == "set_anger":
            self.battle_engine.set_anger(unit_id, value)
        elif update_type == "set_ye_zhang":
            unit["ye_zhang_shield"] = value
            unit["max_hp"] = int(value / 0.24)
            unit["current_hp"] = unit["max_hp"]
            unit["shield"] = value
        elif update_type == "use_skill":
            self.battle_engine.use_skill(unit_id, description or "")
        elif update_type == "record_cast":
            self.battle_engine.record_cast(unit_id, description or "")
        elif update_type == "next_round":
            self.battle_engine.next_round()
        else:
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Unknown update_type: {update_type}"})
            )
            return

        if self.database:
            await self.database.save_unit(unit)
            for log in self.battle_engine.get_all_logs():
                await self.database.save_combat_log(log)

        await self.push_state()


manager = ConnectionManager()
