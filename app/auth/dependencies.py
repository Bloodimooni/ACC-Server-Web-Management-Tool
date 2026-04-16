from fastapi import Request, HTTPException

from app.auth.session import read_session


def require_auth(request: Request) -> dict:
    return read_session(request)
