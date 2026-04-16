import json
import bcrypt

from app.config import settings


def _load_users() -> dict:
    if not settings.USERS_FILE.exists():
        return {}
    return json.loads(settings.USERS_FILE.read_text(encoding="utf-8"))


def verify_user(username: str, password: str) -> bool:
    users = _load_users()
    stored = users.get(username)
    if not stored:
        # Constant-time dummy check to prevent username enumeration
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt()))
        return False
    return bcrypt.checkpw(password.encode(), stored.encode())


def add_user(username: str, password: str) -> None:
    users = _load_users()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = hashed
    settings.USERS_FILE.write_text(
        json.dumps(users, indent=2), encoding="utf-8"
    )
