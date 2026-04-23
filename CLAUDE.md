# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MYPKHelper is a desktop/web hybrid assistant tool for 梦幻西游 (Fantasy Westward Journey) PK combat. It monitors the game screen via OCR to track opponent stats (HP, anger, shields) in real-time PvP battles.

**Stack**: Python 3.10+ (FastAPI, WebSocket, PaddleOCR, aiosqlite) + React 18 (Vite, TypeScript, TailwindCSS, Zustand) + Chrome Extension (MV3).

## Common Commands

### Development

```bash
# Start both backend and frontend dev servers, then open browser
python scripts/start.py

# Backend only (from backend/src/)
cd backend/src
python -m uvicorn main:app --host 0.0.0.0 --port 8765

# Frontend only (from frontend/)
cd frontend
npm run dev          # Vite dev server on :5173
npm run build        # tsc + vite build -> dist/
npm run preview      # Preview production build
```

### Testing

```bash
# Backend tests (from backend/)
cd backend
pytest
```

### Packaging

```bash
# Build standalone executable with PyInstaller (from backend/)
cd backend
pyinstaller mypkhelper.spec
```

The `.spec` bundles the backend with hidden imports for `uvicorn` and `paddleocr`. The frontend must be built (`npm run build`) before packaging so `main.py` can serve `frontend/dist/` as static files.

## High-Level Architecture

### Data Flow

1. User selects a screen region via the Chrome Extension (or manually)
2. Backend captures screenshots via `mss` at intervals (`screen_monitor.py`)
3. `PaddleOCR` recognizes Chinese text (`ocr_engine.py`)
4. `BattleOCRParser` extracts opponent names, factions, actions, and HP changes (`ocr_parser.py`)
5. `BattleEngine` updates unit stats and calculates anger (`battle_engine.py`)
6. WebSocket (`/ws`) broadcasts state updates to the React frontend (`websocket_handler.py`)
7. Frontend displays the combat table, logs, and history

### Backend Modules

| File | Responsibility |
|------|---------------|
| `main.py` | FastAPI entry, HTTP routes (`/api/region`, `/api/battles`), static file mount, lifespan (DB init) |
| `websocket_handler.py` | `ConnectionManager`: WebSocket lifecycle, message routing (`set_region`, `start_battle`, `end_battle`, `init_unit`, `manual_update`, `get_logs`), state broadcast |
| `battle_engine.py` | `BattleEngine`: in-memory combat state (units, HP, anger, shield, logs, rounds). Anger gain from `anger_calculator.py` |
| `ocr_engine.py` | Lazy-loaded PaddleOCR wrapper |
| `ocr_parser.py` | `BattleOCRParser`: extracts `CombatUnit` names/factions from first frame; extracts actions/HP changes from round frames |
| `screen_monitor.py` | Periodic screenshot + OCR polling with configurable interval (5.0s idle, 1.0s during battle) |
| `screenshot.py` | `mss`-based screen capture with region support |
| `database.py` | `aiosqlite` persistence: `combat_units`, `combat_logs`, `battle_records` |
| `models.py` | Pydantic models: `CombatUnit`, `CombatLog`, `BattleRecord`, `MonitorRegion` |
| `constants.py` | `FACTION_HP` (20 factions, 11k–16k base HP), `DAMAGE_ANGER_TABLE`, `SKILL_ANGER_COST` (15 skills) |

### Frontend Structure

- **`App.tsx`**: Root layout (`MonitorBar` + `CombatTable` + `ActionPanel`), view router (`combat` / `history`)
- **`hooks/useWebSocket.ts`**: Single WebSocket connection to `ws://localhost:8765/ws`, message dispatch to Zustand store, exposes `sendManualUpdate` / `startBattle` / `endBattle` / `setRegion` / `initUnit`
- **`stores/useCombatStore.ts`**: Zustand global state: `units`, `logs`, `current_round`, `is_active`, `selected_unit_id`, `monitor_region`, `currentView`
- **Vite proxy**: `/api` → `localhost:8765`, `/ws` → `ws://localhost:8765`

### Chrome Extension

- `extension/manifest.json`: MV3, permissions `activeTab`, `scripting`, `storage`, host `localhost:*`
- `content.js`: Overlay region selection UI (like WeChat screenshot tool)
- Selection is posted to the frontend window via `window.postMessage({ type: 'MYPK_REGION_SELECTED', region })`, picked up by `useWebSocket.ts`

### Key Domain Rules

- **20 Factions**: Each has a preset base HP in `constants.py`. Unknown faction defaults to 12000.
- **叶障护盾 (Ye Zhang Shield)**: When set, `max_hp = shield / 0.24`. Applied via `manual_update` with `update_type: "set_ye_zhang"`.
- **Anger System**: Damage as percentage of max HP maps to anger gain (1–55 points). 16 skills have defined anger costs in `constants.py`.
- **WebSocket Actions**: `set_region`, `start_battle`, `end_battle`, `init_unit`, `manual_update`, `get_logs`.
- **Manual Update Types**: `damage`, `heal`, `set_anger`, `set_ye_zhang`, `use_skill`, `record_cast`, `next_round`.

### Database Schema (SQLite)

- `combat_units`: persisted unit state
- `combat_logs`: round-by-round action logs
- `battle_records`: battle start/end timestamps, opponent name, result, unit IDs

DB path defaults to `mypkhelper.db` in CWD; override with `MYPKHELPER_DB` env var.

## Design System

The frontend follows an Airtable-inspired design system (see `design/DESIGN.md`). Key tokens:

- **Primary text**: `#181d26` (Deep Navy)
- **CTA/Links**: `#1b61c9` (Airtable Blue)
- **Background**: `#ffffff`
- **Borders**: `#e0e2e6`
- **Light surface**: `#f8fafc`
- **Success**: `#006400`
- **Shadow**: blue-tinted multi-layer (`rgba(45,127,249,0.28) 0px 1px 3px`)
- **Radius**: 12px buttons, 16px–24px cards
- **Font**: `Haas` / `-apple-system, system-ui, Segoe UI, Roboto`

Tailwind custom colors are defined in `frontend/tailwind.config.js` (`deep-navy`, `airtable-blue`, `border-gray`, `light-surface`).
