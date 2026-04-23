"""OCR 结果解析器：从游戏画面中提取角色信息、血量、操作文字。"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from ocr_engine import OCREngine
from screenshot import Region
from constants import ALL_FACTIONS
from popup_number_parser import PopupNumberParser
from action_text_parser import ActionTextParser


@dataclass
class ParsedUnit:
    """从 OCR 结果中解析出的角色信息。"""

    name: str
    faction: Optional[str]
    position: Tuple[int, int]  # 角色中心坐标 (x, y)
    name_region: Region  # 名字文字所在区域
    confidence: float


@dataclass
class ParsedAction:
    """从 OCR 结果中解析出的回合操作。"""

    unit_name: Optional[str]  # 关联角色名字（可能识别不到）
    action_text: str  # 原始操作文字
    hp_change: Optional[int]  # 气血变化（负数表示受伤）
    position: Tuple[int, int]  # 文字位置


class BattleOCRParser:
    """解析战斗画面的 OCR 结果。

    使用策略：
    1. 首场全图识别，定位对手 5 个角色的名字和位置。
    2. 后续回合对固定区域做 OCR，识别血量变化和下排操作文字。

    参数说明（可根据实际画面分辨率调整）：
    - opponent_region_ratio: 对手区域占画面宽度的比例（默认左半部分 0.5）
    - name_y_range: 名字可能出现的 y 坐标范围（相对画面高度的比例）
    - action_y_range: 操作文字可能出现的 y 坐标范围
    """

    def __init__(
        self,
        ocr_engine: OCREngine,
        opponent_region_ratio: float = 0.5,
        name_y_range: Tuple[float, float] = (0.1, 0.7),
        action_y_range: Tuple[float, float] = (0.75, 0.95),
    ):
        self.ocr = ocr_engine
        self.opponent_region_ratio = opponent_region_ratio
        self.name_y_range = name_y_range
        self.action_y_range = action_y_range
        self.unit_positions: List[ParsedUnit] = []
        self.popup_parser = PopupNumberParser(self.ocr)
        self.action_parser = ActionTextParser()

    # ------------------------------------------------------------------ #
    #  首场识别
    # ------------------------------------------------------------------ #

    def parse_first_frame(self, image) -> List[ParsedUnit]:
        """首场全图识别：提取对手区域的角色名字和位置。

        返回按 y 坐标排序的 ParsedUnit 列表（通常 5 个）。
        """
        results = self.ocr.recognize(image)
        width, height = image.size
        units = self._extract_opponent_units(results, width, height)
        self.unit_positions = units
        return units

    def _extract_opponent_units(
        self, results: List[Dict], img_width: int, img_height: int
    ) -> List[ParsedUnit]:
        """从 OCR 结果中过滤并提取对手角色信息。"""
        opponent_x_max = img_width * self.opponent_region_ratio
        name_y_min = img_height * self.name_y_range[0]
        name_y_max = img_height * self.name_y_range[1]

        candidates = []
        for r in results:
            text = r.get("text", "").strip()
            conf = r.get("confidence", 0)
            bbox = r.get("bbox", [])
            if not text or not bbox or conf < 0.5:
                continue

            # bbox 格式：[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]（四边形）
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)

            # 只取左侧对手区域
            if cx > opponent_x_max:
                continue

            # 只取名字可能出现的 y 范围
            if not (name_y_min <= cy <= name_y_max):
                continue

            # 名字通常是纯中文，2-6 个字
            if not self._looks_like_name(text):
                continue

            candidates.append({
                "text": text,
                "conf": conf,
                "cx": cx,
                "cy": cy,
                "bbox": bbox,
            })

        # 按 y 坐标排序（从上到下）
        candidates.sort(key=lambda c: c["cy"])

        # 如果候选超过 5 个，按置信度取前 5
        if len(candidates) > 5:
            candidates = sorted(candidates, key=lambda c: c["conf"], reverse=True)[:5]
            candidates.sort(key=lambda c: c["cy"])

        units = []
        for c in candidates:
            # 尝试从附近文字提取门派
            faction = self._extract_faction_from_context(c, results)

            bbox = c["bbox"]
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            region = Region(
                x=int(min(xs)),
                y=int(min(ys)),
                width=int(max(xs) - min(xs)),
                height=int(max(ys) - min(ys)),
            )

            units.append(
                ParsedUnit(
                    name=c["text"],
                    faction=faction,
                    position=(int(c["cx"]), int(c["cy"])),
                    name_region=region,
                    confidence=c["conf"],
                )
            )

        return units

    @staticmethod
    def _looks_like_name(text: str) -> bool:
        """判断文字是否像角色名字。

        角色名字通常是中文，2-6 个字，不含数字和明显标点。
        """
        if len(text) < 2 or len(text) > 8:
            return False
        # 允许少量非中文字符（如「·」）
        chinese_ratio = sum(1 for ch in text if "一" <= ch <= "鿿") / len(text)
        return chinese_ratio >= 0.5

    def _extract_faction_from_context(
        self, candidate: Dict, all_results: List[Dict]
    ) -> Optional[str]:
        """在候选名字附近的 OCR 结果中查找门派名称。"""
        cx, cy = candidate["cx"], candidate["cy"]
        search_radius = 60  # 像素

        for r in all_results:
            text = r.get("text", "").strip()
            bbox = r.get("bbox", [])
            if not text or not bbox:
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            ox = sum(xs) / len(xs)
            oy = sum(ys) / len(ys)

            if abs(ox - cx) < search_radius and abs(oy - cy) < search_radius:
                for faction in ALL_FACTIONS:
                    if faction in text:
                        return faction
        return None

    # ------------------------------------------------------------------ #
    #  回合识别
    # ------------------------------------------------------------------ #

    def parse_round_frame(self, image) -> List[ParsedAction]:
        """识别当前回合的操作文字和血量变化。

        如果首场已定位角色位置，会优先在角色附近区域识别血量数字；
        同时在画面下排识别操作文字。
        """
        results = self.ocr.recognize(image)
        width, height = image.size

        actions = []

        # 1. 识别下排操作文字
        action_y_min = height * self.action_y_range[0]
        action_y_max = height * self.action_y_range[1]

        for r in results:
            text = r.get("text", "").strip()
            conf = r.get("confidence", 0)
            bbox = r.get("bbox", [])
            if not text or not bbox or conf < 0.5:
                continue

            ys = [p[1] for p in bbox]
            cy = sum(ys) / len(ys)

            if action_y_min <= cy <= action_y_max:
                # 尝试关联到最近的角色
                nearest = self._find_nearest_unit(bbox, width)
                hp_change = self._extract_hp_change(text)
                actions.append(
                    ParsedAction(
                        unit_name=nearest.name if nearest else None,
                        action_text=text,
                        hp_change=hp_change,
                        position=(int(sum([p[0] for p in bbox]) / len(bbox)), int(cy)),
                    )
                )

        # 2. 如果有角色位置缓存，在角色头顶区域识别血量数字
        if self.unit_positions:
            for unit in self.unit_positions:
                hp = self._recognize_hp_at_position(image, unit.position)
                if hp is not None:
                    actions.append(
                        ParsedAction(
                            unit_name=unit.name,
                            action_text=f"气血 {hp}",
                            hp_change=None,  # 单场无法判断变化量，需前后对比
                            position=unit.position,
                        )
                    )

        return actions

    def _find_nearest_unit(
        self, bbox: List, img_width: int
    ) -> Optional[ParsedUnit]:
        """根据文字位置找到最近的角色（仅限对手区域）。"""
        if not self.unit_positions:
            return None

        xs = [p[0] for p in bbox]
        cx = sum(xs) / len(xs)
        # 只考虑左侧对手区域
        if cx > img_width * self.opponent_region_ratio:
            return None

        nearest = None
        min_dist = float("inf")
        for unit in self.unit_positions:
            dist = abs(unit.position[0] - cx)
            if dist < min_dist:
                min_dist = dist
                nearest = unit

        return nearest

    def _extract_hp_change(self, text: str) -> Optional[int]:
        """从操作文字中提取气血变化。

        例如：
        - "受到 1234 点伤害" → -1234
        - "回复 500 点气血" → +500
        """
        # 匹配数字
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return None

        val = int(numbers[0])

        # 判断是受伤还是回复
        damage_keywords = ["伤害", "攻击", "扣除", "失去", "减少", "受到"]
        heal_keywords = ["回复", "恢复", "治疗", "增加", "补充"]

        for kw in damage_keywords:
            if kw in text:
                return -val
        for kw in heal_keywords:
            if kw in text:
                return val

        return None

    def _recognize_hp_at_position(
        self, image, position: Tuple[int, int]
    ) -> Optional[int]:
        """在角色头顶附近识别血量数字。

        裁剪一个小区域做 OCR，返回识别到的数字。
        """
        x, y = position
        # 头顶区域大约在角色上方 40-80 像素处，宽 80 像素
        crop_region = (
            max(0, x - 40),
            max(0, y - 90),
            80,
            50,
        )
        cropped = image.crop(crop_region)
        results = self.ocr.recognize(cropped)

        for r in results:
            text = r.get("text", "").strip()
            nums = re.findall(r"\d+", text)
            if nums:
                return int(nums[0])

        return None

    # ------------------------------------------------------------------ #
    #  血量追踪
    # ------------------------------------------------------------------ #

    def parse_popup_numbers(self, image):
        """识别角色头顶弹出的伤害/治疗数字。"""
        units = [
            {"name": u.name, "position": u.position}
            for u in self.unit_positions
        ]
        self.popup_parser.set_unit_positions(units)
        numbers = self.popup_parser.parse(image)
        return [
            {
                "value": n.value,
                "unit_name": n.unit_name,
                "raw_text": n.raw_text,
                "confidence": n.confidence,
            }
            for n in numbers
        ]

    def parse_actions(self, ocr_results: List[Dict]):
        """从 OCR 结果中解析操作文字（特技、回合、伤害/治疗描述）。"""
        names = [u.name for u in self.unit_positions]
        self.action_parser.set_unit_names(names)
        actions = self.action_parser.parse(ocr_results)
        return [
            {
                "action_type": a.action_type,
                "text": a.text,
                "unit_name": a.unit_name,
                "skill_name": a.skill_name,
                "round_num": a.round_num,
                "hp_value": a.hp_value,
            }
            for a in actions
        ]

    def track_hp_changes(
        self, prev_hps: Dict[str, int], curr_hps: Dict[str, int]
    ) -> List[Dict]:
        """对比前后两帧的血量，生成变化记录。

        prev_hps / curr_hps: {unit_name: hp_value}
        返回: [{unit_name, prev_hp, curr_hp, change}, ...]
        """
        changes = []
        for name, curr in curr_hps.items():
            prev = prev_hps.get(name)
            if prev is not None and prev != curr:
                changes.append({
                    "unit_name": name,
                    "prev_hp": prev,
                    "curr_hp": curr,
                    "change": curr - prev,
                })
        return changes
