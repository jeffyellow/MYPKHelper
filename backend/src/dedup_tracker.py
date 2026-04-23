"""去重追踪器：避免同一伤害/治疗数字在 3 秒窗口内被重复计算。"""

import time
from typing import Optional


class DedupTracker:
    """记录最近处理过的 (unit_name, value) 对，支持时间窗口去重。"""

    def __init__(self, window_ms: int = 3000):
        self.window_ms = window_ms
        self._entries: list[tuple[str, int, float]] = []

    def is_duplicate(self, unit_name: str, value: int) -> bool:
        """检查该组合是否在窗口内已处理过。"""
        now = time.time() * 1000
        cutoff = now - self.window_ms

        # 清理过期条目
        self._entries = [
            (u, v, ts) for (u, v, ts) in self._entries if ts > cutoff
        ]

        for u, v, _ in self._entries:
            if u == unit_name and v == value:
                return True
        return False

    def record(self, unit_name: str, value: int) -> None:
        """记录一次处理。"""
        now = time.time() * 1000
        self._entries.append((unit_name, value, now))

    def clear(self) -> None:
        """清空所有记录。"""
        self._entries = []
