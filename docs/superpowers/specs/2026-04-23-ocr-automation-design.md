# MYPKHelper OCR 自动化设计文档

## 背景与约束

- **双屏幕**：浏览器辅助屏在一屏，游戏画面在另一屏
- **纯 OCR 驱动**：不接受手动操作面板
- **完全自动**：OCR 识别结果直接驱动状态变化，无人工确认/纠错环节
- **隐藏总血量**：战斗画面不显示总血量，初始值由门派预设或叶障护盾反推

## 游戏机制关键事实

1. 总血量不在战斗画面中显示
2. 初始总血量 = 门派预设值（或 叶障护盾 / 0.24）
3. 血量变化只能通过识别战斗过程中弹出的伤害/治疗数字来追踪
4. 愤怒增加来自伤害值，愤怒减少来自特技使用
5. 伤害/治疗数字以弹出形式出现在角色附近，红/绿色区分
6. 特技使用信息出现在画面下方的操作文字中

## 架构设计

### 数据流

```
ScreenMonitor (1s 间隔截图)
  │
  ├──→ 【角色区域】OCR 识别弹出数字
  │       ├── 伤害数字 → BattleEngine.apply_damage()
  │       └── 治疗数字 → BattleEngine.apply_heal()
  │
  └──→ 【画面下方】OCR 识别操作文字
          ├── 特技名 → BattleEngine.use_skill()
          └── "第 X 回合" → BattleEngine.next_round()

BattleEngine 状态变化
  │
  └──→ WebSocket broadcast (state_update)
          └──→ React 前端更新 CombatTable + LogViewer
```

### 模块职责

| 模块 | 职责 |
|------|------|
| `screen_monitor.py` | 定时截图，触发 OCR 和解析 |
| `ocr_parser.py` | 从截图中提取弹出数字和操作文字 |
| `battle_engine.py` | 维护战斗状态，计算愤怒，生成日志 |
| `websocket_handler.py` | 管理 WebSocket，广播状态，处理前端消息 |
| `region_selector.py` | 全屏选区（已 implemented） |

## 核心设计

### 1. 首场角色识别

沿用现有 `parse_first_frame` 逻辑：

1. 全图 OCR，过滤左侧对手区域（`opponent_region_ratio=0.5`）
2. 识别名字（2-8 字中文，置信度 > 0.5）
3. 名字附近 60px 搜索门派关键字
4. 取前 5 个候选，按 y 坐标排序
5. 初始化 BattleEngine：
   - 总血量 = `FACTION_HP[门派]`（默认 12000）
   - 当前血量 = 总血量
   - 当前愤怒 = **90**（PK 开场愤怒值）
   - 叶障护盾 = 0
6. 用户可手动输入叶障护盾值（前端 `CombatTable` 输入框），输入后联动更新：
   - 总血量 = `叶障护盾 / 0.24`（取整）
   - 当前血量 = 总血量
   - 护盾值 = 叶障护盾值

**输出**：`List[ParsedUnit]`，包含名字、门派、屏幕坐标。坐标缓存到 `ocr_parser.unit_positions`。

### 2. 弹出数字识别（血量变化来源）

#### 2.1 搜索区域

对每个缓存角色，以其名字中心坐标为基准，扩展搜索框：

```python
# 角色名字中心 (cx, cy)
search_box = {
    "x": cx - 100,      # 向左扩展 100px
    "y": cy - 120,      # 向上扩展 120px（头顶区域）
    "width": 200,       # 总宽 200px
    "height": 160,      # 总高 160px
}
```

参数说明：
- 水平范围覆盖角色宽度及两侧可能出现的数字
- 垂直范围覆盖头顶上方（伤害数字常见位置）到名字下方
- 这些参数为初始值，后续可根据实际分辨率校准

#### 2.2 数字过滤

对搜索区域裁剪子图 OCR，结果过滤：

1. 文本只包含数字和可选的正负号（`^-?\d+$`）
2. 数字范围合理（1 - 99999）
3. 置信度 > 0.6

#### 2.3 伤害 vs 治疗判断

```python
def classify_number(value: int, color_hint: str) -> str:
    if value < 0 or color_hint == "red":
        return "damage"
    if value > 0 or color_hint == "green":
        return "heal"
    return "unknown"
```

**注意**：颜色判断为可选优化。PaddleOCR 不直接输出颜色，可通过图像预处理（提取红色/绿色通道）辅助判断。初始版本可只依赖正负号，后续迭代加颜色辅助。

#### 2.4 角色关联

数字出现在哪个角色的搜索区域内，就归属于该角色。如果同一数字同时落在多个角色的搜索区域（重叠时），归属到中心点最近的角色。

#### 2.5 去重策略

同一伤害/治疗事件可能持续多帧，OCR 每 1 秒截图一次，可能重复识别到同一数字。

**去重规则**：

```python
# 以 (unit_id, value, 时间窗口) 为键
# 同一角色在 3 秒内识别到相同数值的数字，视为重复，只计算一次
DEDUP_WINDOW_MS = 3000
```

实现方式：在 `ConnectionManager` 或 `BattleEngine` 层维护一个 `recent_numbers` 缓存，记录最近 3 秒内已处理过的 (unit_id, value, timestamp)。重复数字跳过。

#### 2.6 边界情况

| 情况 | 处理 |
|------|------|
| 一帧内同一角色多个不同数字 | 视为多段伤害，全部计入 |
| 数字识别为 0 | 忽略 |
| 搜索区域内无数字 | 跳过，不更新状态 |
| OCR 把名字的一部分误识别为数字 | 通过"纯数字"过滤 + 置信度阈值排除 |

### 3. 操作文字识别（特技 + 回合）

#### 3.1 搜索区域

画面下方固定区域：

```python
action_y_range = (0.75, 0.95)  # 画面底部 75% ~ 95%
```

#### 3.2 特技识别

遍历 OCR 结果，检查文本是否包含 `SKILL_ANGER_COST` 中的任一特技名：

```python
for skill_name in SKILL_ANGER_COST:
    if skill_name in text:
        # 匹配成功
        # 需要关联到角色：从文本中提取角色名，或按 x 坐标最近匹配
```

**角色关联**：操作文字通常以"XX 使用了 YY"的形式出现。如果 OCR 结果包含角色名，直接匹配；如果不包含，按文字 x 坐标与最近角色的 x 坐标关联。

#### 3.3 回合检测

正则匹配"第 X 回合"或"第X回合"：

```python
import re
round_match = re.search(r"第\s*(\d+)\s*回合", text)
if round_match:
    round_num = int(round_match.group(1))
    if round_num != battle_engine.current_round:
        battle_engine.next_round()  # 或 set_round(round_num)
```

#### 3.4 操作文字中的伤害描述

如"受到 1500 点伤害"、"气血回复了 800 点"等。

**处理策略**：提取其中的数字，但**不用于血量计算**（避免与弹出数字重复）。仅作为日志记录（`description` 字段），帮助用户回溯发生了什么。

### 4. 愤怒计算

#### 4.1 愤怒增加

来自弹出伤害数字：

```python
anger_gain = calculate_anger_from_damage(max_hp, actual_damage)
# actual_damage = min(damage, current_hp + shield)
```

#### 4.2 愤怒减少

来自操作文字中的特技使用：

```python
cost = SKILL_ANGER_COST.get(skill_name, 0)
# current_anger = max(0, current_anger - cost)
```

#### 4.3 愤怒上限

愤怒值上限 150。超过时截断。

### 5. 战斗生命周期

```
用户点击"战斗开始"
  │
  ├──→ ScreenMonitor 间隔设为 1.0s
  ├──→ 首场截图 OCR → parse_first_frame → init 5 个角色
  ├──→ BattleEngine.start_battle() (current_round = 1)
  └──→ 开始定时截图

战斗进行中
  │
  ├──→ 每 1s：截图 → OCR → 解析弹出数字 + 操作文字
  ├──→ 更新 BattleEngine 状态
  └──→ WebSocket 广播 state_update

用户点击"战斗结束"
  │
  ├──→ ScreenMonitor.stop()
  ├──→ 间隔恢复 5.0s
  ├──→ BattleEngine.end_battle()
  └──→ 保存战斗记录到数据库
```

### 6. 状态同步

WebSocket 消息类型：

| 类型 | 触发时机 | 数据 |
|------|----------|------|
| `state_update` | 每次 BattleEngine 状态变化后 | units, current_round, logs, is_active |
| `ocr_debug` | 每次 OCR 解析完成后 | 原始文字、识别到的 actions |
| `region_set` | 选区完成后 | region 坐标 |
| `battle_started` | 战斗开始时 | - |
| `battle_ended` | 战斗结束时 | - |

前端订阅 `state_update` 更新全局状态，`ocr_debug` 用于调试面板展示原始 OCR 结果。

### 7. OCR 调试面板（前端）

纯 OCR 方案必须能看到 OCR 在识别什么，否则无法迭代优化。

**功能**：
- 显示最近一帧的 OCR 原始文字列表
- 显示解析出的弹出数字（哪个角色、什么值、判断为伤害/治疗）
- 显示解析出的操作文字（特技、回合、日志描述）
- 显示哪些角色被成功匹配，哪些没匹配上

**位置**：可放在 `ActionPanel` 的日志区域下方，或作为一个可折叠的面板。

### 8. 错误处理策略

由于"完全信任 OCR、不纠错"的约束，错误处理只能是自动降级：

| 错误场景 | 处理 |
|----------|------|
| OCR 未识别到任何数字 | 跳过该帧，状态不变 |
| 角色匹配失败（名字 OCR 错误） | 该角色的数字无法关联，跳过 |
| 数字去重误判（不同事件数值相同） | 3 秒窗口内相同数值跳过，可能漏检不同来源的相同伤害 |
| 特技识别错误（文字不全） | 愤怒不扣，日志不记录 |
| 回合检测失败 | 需手动依赖弹出数字的时间序列推断，或延长检测窗口 |

## 待验证假设

1. 弹出数字在 1 秒间隔的截图中可被稳定捕获
2. 伤害数字和治疗数字在搜索区域内可被 OCR 准确识别为纯数字
3. 操作文字中的特技名可被准确匹配
4. "第 X 回合"文字在画面下方稳定出现

## 后续迭代方向

1. **颜色辅助判断**：通过图像预处理提取红色/绿色通道，辅助判断伤害/治疗
2. **自适应搜索区域**：根据首场识别的角色大小，动态调整搜索框尺寸
3. **模糊匹配**：角色名 OCR 错误时使用 edit distance 匹配
4. **操作文字扩展**：收集更多游戏内实际文本样本，扩展匹配模式
