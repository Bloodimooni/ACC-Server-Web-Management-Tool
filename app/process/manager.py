"""
Windows-native ACC server process manager.
Launches accServer.exe directly (no Wine needed).
"""
import asyncio
import subprocess
import sys
import time
from typing import Optional

import psutil

from app.config import settings

_process: Optional[asyncio.subprocess.Process] = None
_start_time: Optional[float] = None
_broadcaster = None  # set by main.py at startup


def set_broadcaster(bc) -> None:
    global _broadcaster
    _broadcaster = bc


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def _find_orphan() -> Optional[psutil.Process]:
    """Find an accServer.exe process started outside this dashboard."""
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"] == "accServer.exe":
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def get_status() -> dict:
    global _process, _start_time

    if _process is not None and _process.returncode is None:
        return {
            "running": True,
            "pid": _process.pid,
            "uptime": int(time.time() - (_start_time or time.time())),
            "adopted": False,
        }

    # Check for orphaned process (e.g. dashboard restarted while server ran)
    orphan = _find_orphan()
    if orphan:
        try:
            ct = orphan.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            ct = time.time()
        return {
            "running": True,
            "pid": orphan.pid,
            "uptime": int(time.time() - ct),
            "adopted": True,
        }

    return {"running": False, "pid": None, "uptime": 0, "adopted": False}


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

async def start() -> dict:
    global _process, _start_time

    if _process is not None and _process.returncode is None:
        return {"status": "already_running", "pid": _process.pid}

    orphan = _find_orphan()
    if orphan:
        return {"status": "already_running", "pid": orphan.pid, "adopted": True}

    exe = settings.SERVER_DIR / "accServer.exe"
    if not exe.exists():
        return {"status": "error", "message": f"Executable not found: {exe}"}

    # CREATE_NEW_PROCESS_GROUP allows sending CTRL_BREAK_EVENT for graceful stop
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    _process = await asyncio.create_subprocess_exec(
        str(exe),
        cwd=str(settings.SERVER_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        creationflags=creation_flags,
    )
    _start_time = time.time()
    asyncio.create_task(_drain_stdout(_process))

    return {"status": "started", "pid": _process.pid}


# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------

async def stop() -> dict:
    global _process

    if _process is None or _process.returncode is not None:
        # Try to terminate an adopted orphan
        orphan = _find_orphan()
        if orphan:
            try:
                orphan.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            return {"status": "stopped", "pid": orphan.pid}
        return {"status": "not_running"}

    pid = _process.pid

    # Graceful shutdown: send CTRL+BREAK (Windows) or SIGTERM (other)
    try:
        if sys.platform == "win32":
            import signal as _signal
            _process.send_signal(_signal.CTRL_BREAK_EVENT)
        else:
            _process.terminate()
        await asyncio.wait_for(_process.wait(), timeout=10.0)
    except (asyncio.TimeoutError, OSError):
        try:
            _process.kill()
            await _process.wait()
        except Exception:
            pass

    _process = None
    return {"status": "stopped", "pid": pid}


# ---------------------------------------------------------------------------
# Stdout pipe → broadcaster
# ---------------------------------------------------------------------------

async def _drain_stdout(proc: asyncio.subprocess.Process) -> None:
    if proc.stdout is None:
        return
    try:
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if _broadcaster and line:
                await _broadcaster.broadcast(line + "\n")
    except Exception:
        pass
    if _broadcaster:
        await _broadcaster.broadcast("[accServer.exe process exited]\n")
