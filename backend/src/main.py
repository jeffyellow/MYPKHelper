"""FastAPI 应用入口：HTTP 端点、WebSocket 支持、CORS、静态文件服务。"""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import Database
from websocket_handler import manager
from models import MonitorRegion
from region_selector import select_region_sync
from screenshot import Region

DB_PATH = os.environ.get("MYPKHELPER_DB", "mypkhelper.db")
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(DB_PATH)
    await db.init()
    manager.set_database(db)
    yield
    await db.close()


app = FastAPI(title="MYPKHelper Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "MYPKHelper Backend is running"}


@app.post("/api/region")
async def set_region(region: MonitorRegion):
    manager.monitor_region = region.model_dump()
    return {"status": "ok", "region": manager.monitor_region}


@app.get("/api/region")
async def get_region():
    return {"region": manager.monitor_region}


@app.get("/api/battles")
async def list_battles():
    if manager.database is None:
        return {"battles": []}
    records = await manager.database.list_battle_records()
    return {"battles": records}


@app.post("/api/select-region")
async def select_region():
    """启动全屏区域选择器，阻塞直到用户完成选区。"""
    loop = asyncio.get_event_loop()
    region = await loop.run_in_executor(None, select_region_sync)

    if region is None:
        return {"status": "cancelled"}

    manager.monitor_region = {
        "x": region.x,
        "y": region.y,
        "width": region.width,
        "height": region.height,
    }
    manager.screenshot_engine.set_region(region)

    # 广播给所有前端客户端
    await manager.broadcast({
        "type": "region_set",
        "data": manager.monitor_region,
    })

    return {"status": "ok", "region": manager.monitor_region}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            await manager.handle_message(websocket, raw)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# 如果前端构建产物存在，挂载静态文件服务
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "MYPKHelper Backend is running"}
