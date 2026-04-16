from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from fastapi import Request, Response, HTTPException

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="acc-session")
SESSION_MAX_AGE = 8 * 3600  # 8 hours


def create_session(response: Response, username: str, provider: str = "local") -> None:
    token = _serializer.dumps({"sub": username, "provider": provider})
    response.set_cookie(
        "acc_session",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.HTTPS_ENABLED,
        max_age=SESSION_MAX_AGE,
    )


def read_session(request: Request) -> dict:
    token = request.cookies.get("acc_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")


def delete_session(response: Response) -> None:
    response.delete_cookie("acc_session")
