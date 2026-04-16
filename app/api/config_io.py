"""
ACC config files are UTF-16-LE encoded JSON with a BOM (0xFF 0xFE) and CRLF line endings.
All reads/writes here preserve that exact format.
"""
import json
from pathlib import Path

from app.config import settings

_CFG_DIR: Path = settings.SERVER_DIR / "cfg"


def read_cfg(name: str) -> dict:
    path = _CFG_DIR / f"{name}.json"
    raw = path.read_bytes()

    if raw[:2] == b"\xff\xfe":
        text = raw[2:].decode("utf-16-le")
    else:
        # Fallback for files without BOM
        text = raw.decode("utf-16-le")

    return json.loads(text)


def write_cfg(name: str, data: dict) -> None:
    text = json.dumps(data, indent=4, ensure_ascii=False)
    # Normalise to CRLF (ACC expects Windows line endings)
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")

    raw = b"\xff\xfe" + text.encode("utf-16-le")

    path = _CFG_DIR / f"{name}.json"
    # Atomic write: write to .tmp then rename so a crash mid-write can't corrupt the file
    tmp = path.with_name(f"{name}.json.tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)


def cfg_exists(name: str) -> bool:
    return (_CFG_DIR / f"{name}.json").exists()
