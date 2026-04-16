from fastapi import APIRouter, Depends

from app.auth.dependencies import require_auth
from app.process import manager

router = APIRouter(prefix="/api/server", dependencies=[Depends(require_auth)])


@router.get("/status")
async def status():
    return manager.get_status()


@router.post("/start")
async def start():
    return await manager.start()


@router.post("/stop")
async def stop():
    return await manager.stop()


@router.post("/restart")
async def restart():
    await manager.stop()
    return await manager.start()
